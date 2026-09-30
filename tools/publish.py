"""Build, package and publish PANDA / Edit_PyCR on the web page in one go.

For each program:
  1. (optional) git pull
  2. reads the version from the repository
  3. builds it with PyInstaller (its own onedir .spec)
  4. zips dist/<program>/ into downloads/<Name>_v<version>_Windows_x64.zip
  5. copies the user manual into downloads/
  6. writes the release notes from the commits since the last release
     (Claude, see release_notes.py) and updates js/releases.js + index.html
  7. (optional) copies the web folder to the server

USUAL COMMAND - update everything to the latest code
-----------------------------------------------------
Bump the version in the program(s) you want to release and push, then:

    cd C:\\ILL_Git\\web
    python tools/publish.py all --pull --dry-run     # 1. check what will happen
    python tools/publish.py all --pull               # 2. do it

It pulls both repositories, builds with PyInstaller every program whose
version changed (from the .spec at the root of C:\\ILL_Git\\Panda and
C:\\ILL_Git\\Edit_PyCR), zips it into downloads/, copies the manual, writes
the release notes and updates the web page. The zip and manual of the
previous version are deleted from downloads/ to save space. The notes always describe what
is inside the zip: every commit since the previous zip goes into the new
version. A program whose version did not change is not built (the script
says whether it has changes pending; use --rebuild to put them into the
current version).
Add --deploy to also copy the site to the server.

Other uses (from the web/ folder):

    python tools/publish.py panda              # only PANDA
    python tools/publish.py editpycr           # only Edit_PyCR

    python tools/publish.py editpycr --rebuild # same version again: rebuild
                                               # and replace the zip

Options:
    --pull           git pull before building
    --skip-build     package the existing dist/ folder instead of building
    --rebuild        rebuild the current version and replace its zip; notes for
                     any new commits are added to that version
    --no-ai          don't call Claude; the release gets the commit subjects
                     as notes, to be edited by hand in js/releases.js
    --deploy [DIR]   copy the site to DIR (default: "deploy_dir" in
                     tools/deploy.json, or the WEB_DEPLOY_DIR variable)
    --dry-run        show what would happen, change nothing

The version is bumped in the program itself (metadata.py / app_version.py)
and committed before running this; the release notes cover the commits
since the previous release up to HEAD.
"""

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import release_notes as rn  # noqa: E402

WEB = rn.WEB
DOWNLOADS = WEB / "downloads"
LOGS = WEB / "tools" / "logs"

# How each program is built. Paths are relative to its repository.
BUILD = {
    "panda": {
        "spec": "panda_onedir.spec",
        "dist": "dist/PANDA",
        "exe": "PANDA.exe",
        # the spec regenerates this manual during the build
        "manuals": ["docs/PANDA_User_Manual_v{version}.pdf"],
    },
    "editpycr": {
        "spec": "fullprof_editor_onedir.spec",
        "dist": "dist/FullProf_Editor",
        "exe": "FullProf_Editor.exe",
        # the manual bundled with the app; the LaTeX output as a fallback
        "manuals": ["src/edit_pycr/resources/manual/FullProf_Editor_Manual.pdf",
                    "docs/manual/main.pdf"],
    },
}

# Files of the site that go to the server (tools/, logs and README stay here).
SITE = ["index.html", "css", "js", "img", "downloads"]


def step(msg):
    print(f"\n== {msg}")


def version_in_worktree(repo, version_file):
    """The version the build will carry (working tree, not HEAD)."""
    text = (repo / version_file).read_text(encoding="utf-8")
    m = re.search(r'^(?:VERSION|__version__)\s*=\s*["\']([^"\']+)["\']', text, re.M)
    if not m:
        sys.exit(f"No version string found in {version_file}")
    return m.group(1)


def build(key, repo, cfg, version, dry):
    LOGS.mkdir(parents=True, exist_ok=True)
    log = LOGS / f"{key}-{version}.log"
    cmd = [sys.executable, "-m", "PyInstaller", cfg["spec"], "--clean", "--noconfirm"]
    print(f"   {' '.join(cmd)}   (in {repo}, log: {log.relative_to(WEB)})")
    if dry:
        return
    t0 = time.time()
    with log.open("w", encoding="utf-8", errors="replace") as f:
        proc = subprocess.run(cmd, cwd=repo, stdout=f, stderr=subprocess.STDOUT)
    if proc.returncode:
        tail = log.read_text(encoding="utf-8", errors="replace").splitlines()[-25:]
        sys.exit("PyInstaller failed:\n   " + "\n   ".join(tail) + f"\nFull log: {log}")
    exe = repo / cfg["dist"] / cfg["exe"]
    if not exe.exists() or exe.stat().st_mtime < t0:
        sys.exit(f"The build finished but {exe} was not (re)created.")
    print(f"   built in {time.time() - t0:.0f} s")


def package(repo, cfg, name, version, dry, will_build=False):
    """Zip dist/<program>/ (with its top folder) into downloads/."""
    src = repo / cfg["dist"]
    if not (src / cfg["exe"]).exists() and not (dry and will_build):
        sys.exit(f"{src / cfg['exe']} not found - build first (or drop --skip-build).")
    newest_commit = int(rn.git(repo, "log", "-1", "--format=%ct").strip())
    if not will_build and (src / cfg["exe"]).stat().st_mtime < newest_commit:
        print(f"   WARNING: {cfg['exe']} is older than the last commit - it may not "
              f"contain the latest changes.")
    rel = f"downloads/{name}_v{version}_Windows_x64.zip"
    dest = WEB / rel
    print(f"   {src} -> {rel}")
    if dry:
        return rel
    DOWNLOADS.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                z.write(p, Path(src.name) / p.relative_to(src))
    tmp.replace(dest)
    print(f"   {rn.file_size(dest)}")
    return rel


def copy_manual(repo, cfg, name, version, dry):
    for pattern in cfg["manuals"]:
        src = repo / pattern.format(version=version)
        if src.exists():
            rel = f"downloads/{name}_User_Manual_v{version}.pdf"
            print(f"   {src.relative_to(repo)} -> {rel}")
            if not dry:
                shutil.copy2(src, WEB / rel)
            return rel
    print("   WARNING: no manual found; the page keeps the previous one.")
    return None


def prune(name, current, dry):
    """Delete the older zips and manuals of one program: only the files the
    page links to (`current`, paths relative to web/) are kept."""
    keep = {(WEB / c).resolve() for c in current if c}
    for kind in ("_v*_Windows_x64.zip", "_User_Manual_v*.pdf"):
        for old in DOWNLOADS.glob(name + kind):
            if old.resolve() not in keep:
                print(f"   remove old {old.name}")
                if not dry:
                    old.unlink()


def deploy(target, dry):
    target = Path(target)
    step(f"Copying the site to {target}")
    if not dry and not target.exists():
        sys.exit(f"{target} does not exist or is not reachable.")
    copied = 0
    for item in SITE:
        src = WEB / item
        files = [src] if src.is_file() else [p for p in src.rglob("*") if p.is_file()]
        for f in files:
            if f.name.endswith(".part"):
                continue
            dest = target / f.relative_to(WEB)
            if dest.exists() and dest.stat().st_size == f.stat().st_size \
                    and dest.stat().st_mtime >= f.stat().st_mtime:
                continue  # unchanged
            copied += 1
            print(f"   {f.relative_to(WEB)}")
            if not dry:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
    print(f"   {copied} file(s) copied" + (" (dry run)" if dry else ""))

    # old zips/manuals removed here are removed on the server too
    remote = target / "downloads"
    if remote.exists():
        for f in remote.iterdir():
            if f.is_file() and not (DOWNLOADS / f.name).exists():
                print(f"   remove old {f.relative_to(target)} from the server")
                if not dry:
                    f.unlink()


def deploy_target(arg):
    if arg and arg is not True:
        return arg
    cfg = WEB / "tools" / "deploy.json"
    if cfg.exists():
        return json.loads(cfg.read_text(encoding="utf-8"))["deploy_dir"]
    if os.environ.get("WEB_DEPLOY_DIR"):
        return os.environ["WEB_DEPLOY_DIR"]
    sys.exit("No deploy target: pass --deploy DIR, create tools/deploy.json "
             '({"deploy_dir": "..."}) or set WEB_DEPLOY_DIR.')


def publish(key, data, a):
    sw, cfg = data[key], BUILD[key]
    repo = (WEB / sw["repo"]).resolve()
    name = sw["name"]
    step(f"{name}  ({repo})")

    if a.pull:
        print("   " + rn.git(repo, "pull", "--ff-only").strip())
    dirty = [l for l in rn.git(repo, "status", "--porcelain").splitlines() if not l.startswith("??")]
    if dirty:
        print(f"   WARNING: {len(dirty)} uncommitted change(s); they go into the build "
              f"but not into the release notes.")

    version = version_in_worktree(repo, sw["version_file"])
    current = sw["releases"][0]
    last = current["version"]
    # Commits not yet in the zip on the page (the page records the commit each
    # zip was built from). Whatever gets built now contains them, so their
    # notes go to the version being published.
    start = current.get("commit") or rn.bump_commit(repo, sw["version_file"], last)
    commits = [c for c in rn.commits_since(repo, start) if not c["noise"]]

    if version != last and a.rebuild:
        sys.exit(f"--rebuild republishes the current version, but the repository is at "
                 f"{version} and the page at {last}. Drop --rebuild for a new release.")
    if version == last and not a.rebuild:
        if not commits:
            print(f"   {version}: the zip on the page is up to date - nothing to do.")
        else:
            print(f"   {len(commits)} change(s) since the zip on the page, but the version is "
                  f"still {version}: not built.\n   Bump the version in {sw['version_file']} "
                  f"for a new release, or use --rebuild to put them into {version}.")
        return False
    print(f"   version {version}" + (f"  (rebuild, {len(commits)} new change(s))" if a.rebuild
                                     else f"  (previous {last})"))

    # Write the notes first: if Claude or the network fails, nothing was built for nothing.
    notes = []
    if commits or not a.rebuild:
        step(f"{name}: release notes")
        print(f"   {len(commits)} relevant commits since the last build ({start})")
        if not commits:
            notes = [{"type": "improved", "text": "Maintenance release."}]
        elif a.no_ai:
            notes = [{"type": "improved", "text": c["subject"]} for c in commits]
            print("   --no-ai: commit subjects used as notes - edit them in js/releases.js")
        else:
            notes = rn.rewrite_notes(sw, commits)
        for n in notes:
            print(f"   [{n['type']}] {n['text']}")

    if a.skip_build:
        step(f"{name}: build skipped")
    else:
        step(f"{name}: PyInstaller build")
        build(key, repo, cfg, version, a.dry_run)

    step(f"{name}: package")
    file = package(repo, cfg, name, version, a.dry_run, will_build=not a.skip_build)
    manual = copy_manual(repo, cfg, name, version, a.dry_run) or sw["latest"]["manual"]
    prune(name, [file, manual], a.dry_run)

    if a.rebuild:
        # same version, newer zip: its notes grow with what the new build adds
        rn.add_release(sw, repo, version, notes + current["notes"], file, manual)
    else:
        rn.add_release(sw, repo, version, notes, file, manual)
    return True


def main():
    ap = argparse.ArgumentParser(description="Build, package and publish PANDA / Edit_PyCR.")
    ap.add_argument("product", help="panda, editpycr or all")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--deploy", nargs="?", const=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    header, data = rn.load_releases()
    keys = list(BUILD) if a.product == "all" else [a.product]
    for k in keys:
        if k not in BUILD or k not in data:
            sys.exit(f"Unknown product '{k}'. Choose from: {', '.join(BUILD)} or all")

    published = [k for k in keys if publish(k, data, a)]

    step("Web page")
    if not published:
        print("   nothing published - page unchanged")
    elif a.dry_run:
        print("   (dry run: js/releases.js and index.html not written)")
    else:
        rn.save(header, data)
        print("   js/releases.js and index.html updated")

    if a.deploy:
        deploy(deploy_target(a.deploy), a.dry_run)
    else:
        print("\nDone. Open index.html to check, then publish with --deploy "
              "(or copy index.html, css/, js/, img/ and downloads/ to the server).")


if __name__ == "__main__":
    main()
