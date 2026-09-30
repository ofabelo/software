"""Turn the git history of PANDA / Edit_PyCR into the page's release notes.

Commit messages are written for developers ("update", "fix spec", half in
Spanish...). This script collects the commits since the last release from
the local clone of each program (pulled from code.ill.fr or GitHub), asks
Claude to rewrite them as short notes for users, and stores them in
js/releases.js, which feeds the "What's new" panel.

Usage (from the web/ folder):

    # preview the notes for everything since the zip on the page was built
    python tools/release_notes.py panda

    # publish a new version: reads the version number from the repository,
    # turns the pending commits into that release's notes, and points the
    # download button at the new zip (copy it into downloads/ first)
    python tools/release_notes.py panda --release

    # only list the commits, without calling Claude or changing anything
    python tools/release_notes.py editpycr --no-ai

Options:
    --pull           git pull the repository first
    --since REF      start from this commit/tag instead of the last release
    --date YYYY-MM-DD   release date (default: today)
    --file PATH      zip for the release (default: downloads/<Name>_v<ver>_Windows_x64.zip)
    --manual PATH    manual for the release (default: keep the previous one)
    --dry-run        show the result without writing files

The rewriting uses Claude Code with your Claude subscription (Pro/Max),
found on the PATH or inside the VS Code extension. If ANTHROPIC_API_KEY is
set it uses the Claude API instead (needs `pip install anthropic`).
"""

import argparse
import datetime as dt
import html
import json
import re
import subprocess
import sys
from pathlib import Path

WEB = Path(__file__).resolve().parent.parent
RELEASES = WEB / "js" / "releases.js"
INDEX = WEB / "index.html"
MARKER = "window.SOFTWARE = "
RECENT = 4  # keep in sync with js/main.js

# Commits that never matter to users, whatever the model thinks.
NOISE_SUBJECT = re.compile(
    r"^(update[sd]?|nothing|test|merge\b|remov(e|ing)\b.*(pyc|pycache|files?)|"
    r"borrando|ignore\b|upload removing|add a non committed|bump\b|release v)", re.I)
NOISE_PATHS = re.compile(
    r"(^|/)(tests?/|\.gitignore|CLAUDE\.md|AGENTS\.md|\.claude/|__pycache__/|"
    r"docs/Future_actions\.md|docs/ROADMAP\.md)|\.pyc$")


# ---------------------------------------------------------------- data file

def load_releases():
    text = RELEASES.read_text(encoding="utf-8")
    start = text.index(MARKER)
    header = text[:start]
    body = text[start + len(MARKER):].rstrip().rstrip(";")
    return header, json.loads(body)


def dump_releases(header, data):
    body = json.dumps(data, ensure_ascii=False, indent=2)
    # one line per note keeps the file easy to read and edit by hand
    body = re.sub(
        r'\{\n\s+"type": ("(?:[^"\\]|\\.)*"),\n\s+"text": ("(?:[^"\\]|\\.)*")\n\s+\}',
        r'{"type": \1, "text": \2}', body)
    return header + MARKER + body + ";\n"


# ---------------------------------------------------------------- git

def git(repo, *args):
    out = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                         text=True, encoding="utf-8", errors="replace")
    if out.returncode:
        sys.exit(f"git {' '.join(args)} failed:\n{out.stderr}")
    return out.stdout


def version_at_head(repo, version_file):
    text = git(repo, "show", f"HEAD:{version_file}")
    m = re.search(r'^(?:VERSION|__version__)\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not m:
        sys.exit(f"No version string found in {version_file}")
    return m.group(1)


def bump_commit(repo, version_file, version):
    """Commit that introduced `version` in the version file."""
    pattern = r"(VERSION|__version__)\s*=\s*[\"']" + re.escape(version) + r"[\"']"
    hits = git(repo, "log", "--format=%h", "-G", pattern, "--", version_file).split()
    return hits[-1] if hits else None


def commits_since(repo, start):
    rng = f"{start}..HEAD" if start else "HEAD"
    raw = git(repo, "log", "--no-merges", "--reverse", "--date=short",
              "--format=%h%x1f%ad%x1f%s%x1f%b%x1e", rng)
    commits = []
    for rec in raw.split("\x1e"):
        if not rec.strip():
            continue
        h, date, subject, body = (rec.strip("\n").split("\x1f") + [""])[:4]
        body = "\n".join(l for l in body.splitlines()
                         if l.strip() and not l.lower().startswith("co-authored-by"))
        files = git(repo, "show", "--name-only", "--format=", h).split()
        noise = bool(NOISE_SUBJECT.match(subject)) or (files and all(NOISE_PATHS.search(f) for f in files))
        commits.append({"hash": h, "date": date, "subject": subject, "body": body,
                        "files": files, "noise": noise})
    return commits


# ---------------------------------------------------------------- Claude

SYSTEM = """You write the release notes shown on the download page of a scientific \
desktop program used by neutron-diffraction scientists at the Institut Laue-Langevin.

You receive the git commits made since the last release. Turn them into notes for \
USERS of the program:
- English, plain and concrete: what they can now do, what works better, what was fixed.
- One sentence each (two at most). Name the feature, dialog or file format involved.
- Merge commits that belong to the same change into one note.
- Leave out anything users never see: refactoring, tests, build scripts, packaging, \
repository housekeeping, developer documentation, code style, icons redrawn with no \
functional change. If nothing is user-visible, return an empty list.
- Only state what the commits support; do not invent features, numbers or benefits.
- Classify each note as "new" (a capability that did not exist), "improved" \
(existing behaviour made better) or "fixed" (a bug fixed).
- Order notes by importance to users, most important first.
- File names, extensions and keywords may be wrapped in <code></code>; no other markup.
- Commit messages may be in English or Spanish, terse or informal."""

SCHEMA = {
    "type": "object",
    "properties": {
        "notes": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {"type": "string", "enum": ["new", "improved", "fixed"]},
                    "text": {"type": "string"},
                },
                "required": ["type", "text"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["notes"],
    "additionalProperties": False,
}


def build_prompt(product, commits):
    examples = [n for r in product["releases"][:3] for n in r["notes"]][:8]
    log = "\n\n".join(
        f"[{c['hash']} {c['date']}] {c['subject']}"
        + (f"\n{c['body']}" if c["body"] else "")
        + f"\nfiles: {', '.join(c['files'][:15])}"
        + (" ..." if len(c["files"]) > 15 else "")
        for c in commits if not c["noise"])
    return (
        f"Program: {product['name']}\n\n"
        f"Examples of the style used in earlier notes:\n"
        f"{json.dumps(examples, ensure_ascii=False, indent=1)}\n\n"
        f"Commits since the last release, oldest first:\n\n{log}")


def find_claude_cli():
    """Claude Code: on the PATH, or the copy bundled with the VS Code extension."""
    import os
    import shutil
    exe = os.environ.get("CLAUDE_CLI") or shutil.which("claude")
    if exe:
        return exe
    bundled = sorted(Path.home().glob(
        ".vscode/extensions/anthropic.claude-code-*/resources/native-binary/claude*"))
    return str(bundled[-1]) if bundled else None


def rewrite_notes(product, commits):
    """Rewrite commits as user notes.

    Uses the Claude API when an API key is set; otherwise Claude Code, which
    runs on the Claude subscription (Pro/Max) you are logged in with.
    """
    import os
    if os.environ.get("ANTHROPIC_API_KEY"):
        return rewrite_with_claude(product, commits)
    cli = find_claude_cli()
    if cli:
        return rewrite_with_claude_code(cli, product, commits)
    sys.exit("Claude is not available: install Claude Code (or set ANTHROPIC_API_KEY), "
             "or use --no-ai.")


def rewrite_with_claude_code(cli, product, commits):
    import tempfile
    prompt = (SYSTEM + "\n\nAnswer with the JSON object only, no other text, in the form "
              '{"notes": [{"type": "new|improved|fixed", "text": "..."}]}.\n\n'
              + build_prompt(product, commits))
    print(f"   asking Claude Code ({Path(cli).name}) ...")
    # run outside any project so no CLAUDE.md or project context gets mixed in
    with tempfile.TemporaryDirectory() as tmp:
        out = subprocess.run([cli, "-p", "--output-format", "json"], input=prompt,
                             capture_output=True, text=True, encoding="utf-8",
                             errors="replace", cwd=tmp, timeout=600)
    if out.returncode:
        sys.exit(f"Claude Code failed ({out.returncode}):\n{out.stderr or out.stdout}\n"
                 "Is it logged in? Open Claude Code once, or use --no-ai.")
    try:
        reply = json.loads(out.stdout)
        if reply.get("is_error"):
            sys.exit(f"Claude Code: {reply.get('result')}")
        text = reply["result"]
        notes = json.loads(text[text.index("{"):text.rindex("}") + 1])["notes"]
    except (ValueError, KeyError) as e:
        sys.exit(f"Could not read Claude Code's answer ({e}):\n{out.stdout[:2000]}")
    return [n for n in notes if n.get("type") in ("new", "improved", "fixed") and n.get("text")]


def rewrite_with_claude(product, commits):
    try:
        import anthropic
    except ImportError:
        sys.exit("The 'anthropic' package is missing: pip install anthropic  (or use --no-ai)")

    prompt = build_prompt(product, commits)
    client = anthropic.Anthropic()
    try:
        response = client.beta.messages.create(
            model="claude-opus-5",
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},  # rerun on another model if one declines
            thinking={"type": "adaptive"},
            output_config={"effort": "medium",
                           "format": {"type": "json_schema", "schema": SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
    except anthropic.AuthenticationError:
        sys.exit("No valid API key: set ANTHROPIC_API_KEY or run `ant auth login`.")
    except anthropic.RateLimitError:
        sys.exit("Rate limited by the API; try again in a minute.")
    except anthropic.APIStatusError as e:
        sys.exit(f"API error {e.status_code}: {e.message}")
    except anthropic.APIConnectionError:
        sys.exit("Could not reach the Anthropic API (network or proxy).")

    if response.stop_reason == "refusal":
        sys.exit("The model declined to write these notes.")
    if response.stop_reason == "max_tokens":
        sys.exit("The answer was cut off; try with --since to cover fewer commits.")
    text = next(b.text for b in response.content if b.type == "text")
    return json.loads(text)["notes"]


# ---------------------------------------------------------------- page

def fmt_date(d):
    parts = [int(x) for x in str(d).split("-") if x]
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    if len(parts) == 1:
        return str(parts[0])
    return (f"{parts[2]} " if len(parts) > 2 else "") + f"{months[parts[1] - 1]} {parts[0]}"


def note_html(n):
    label = None if isinstance(n, str) else {"new": "New", "improved": "Improved", "fixed": "Fixed"}.get(n["type"])
    text = n if isinstance(n, str) else n["text"]
    if not label:
        return f'<li class="plain">{text}</li>'
    return f'<li><span class="kind kind--{n["type"]}">{label}</span><span>{text}</span></li>'


def static_news(sw):
    """Same markup js/main.js renders, for browsers where the script can't run."""
    out = []
    for r in sw["releases"][:RECENT]:
        latest = r["version"] == sw["latest"]["version"]
        out.append(
            f'<article class="release{" release--latest" if latest else ""}"><header>'
            f'<span class="release__v">{html.escape(sw["name"])} {r["version"]}</span>'
            f'<time class="release__date">{fmt_date(r["date"])}</time>'
            + (f'<a class="release__tag" href="{sw["latest"]["file"]}" download>Latest · download</a>'
               if latest else "")
            + "</header><ul>" + "".join(map(note_html, r["notes"])) + "</ul></article>")
    return "\n            ".join(out)


def update_index(data):
    s = INDEX.read_text(encoding="utf-8")
    first = next(iter(data.values()))
    s = re.sub(r"(<!-- news:start -->).*?(<!-- news:end -->)",
               lambda m: m.group(1) + "\n            " + static_news(first) + "\n            " + m.group(2),
               s, flags=re.S)
    # new cache-busting stamp so browsers fetch the updated scripts
    stamp = dt.datetime.now().strftime("%Y%m%d%H%M")
    s = re.sub(r'((?:css|js)/[\w.-]+\.(?:css|js))\?v=\w+', rf"\1?v={stamp}", s)
    return s


def file_size(path):
    return f"{path.stat().st_size / 2**20:.0f} MB" if path.exists() else "?"


def add_release(sw, repo, version, notes, file, manual, date=None):
    """Put `version` at the top of the release list and make it the download."""
    date = date or dt.date.today().isoformat()
    head = git(repo, "rev-parse", "--short", "HEAD").strip()
    sw["releases"] = [r for r in sw["releases"] if r["version"] != version]
    sw["releases"].insert(0, {"version": version, "date": date, "commit": head, "notes": notes})
    sw["latest"] = {"version": version, "date": date, "file": file,
                    "size": file_size(WEB / file), "manual": manual}


def save(header, data):
    RELEASES.write_text(dump_releases(header, data), encoding="utf-8")
    INDEX.write_text(update_index(data), encoding="utf-8")


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("product", help="key in js/releases.js: panda or editpycr")
    ap.add_argument("--release", action="store_true")
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--since")
    ap.add_argument("--date")
    ap.add_argument("--file")
    ap.add_argument("--manual")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    header, data = load_releases()
    if a.product not in data:
        sys.exit(f"Unknown product '{a.product}'. Choose from: {', '.join(data)}")
    sw = data[a.product]
    repo = (WEB / sw["repo"]).resolve()
    if a.pull:
        print(git(repo, "pull", "--ff-only").strip())

    last = sw["releases"][0]
    start = a.since or last.get("commit") or bump_commit(repo, sw["version_file"], last["version"])
    commits = commits_since(repo, start)
    print(f"{sw['name']}: {len(commits)} commits since {last['version']} ({start}), "
          f"{sum(not c['noise'] for c in commits)} kept")

    if a.no_ai:
        for c in commits:
            print(f"{'  (skip) ' if c['noise'] else '  '}{c['hash']} {c['date']} {c['subject']}")
        return
    if not any(not c["noise"] for c in commits):
        print("Nothing new to describe.")
        return

    notes = rewrite_notes(sw, commits)
    print(json.dumps(notes, ensure_ascii=False, indent=1))

    if a.release:
        version = version_at_head(repo, sw["version_file"])
        if version == last["version"]:
            sys.exit(f"The repository is still at {version}: bump the version before --release.")
        file = a.file or f"downloads/{sw['name']}_v{version}_Windows_x64.zip"
        if not (WEB / file).exists():
            print(f"Warning: {file} does not exist yet - copy the zip there before uploading.")
        add_release(sw, repo, version, notes, file, a.manual or sw["latest"]["manual"], a.date)
        print(f"-> release {sw['name']} {version}")
    else:
        print("(preview only - use tools/publish.py to publish, or --release)")
        return

    if a.dry_run:
        print("(dry run: nothing written)")
        return
    save(header, data)
    print(f"Updated {RELEASES.relative_to(WEB)} and {INDEX.relative_to(WEB)}")


if __name__ == "__main__":
    main()
