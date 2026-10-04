"""Build, package and publish PANDA / Edit_PyCR on the web page in one go.

For each program:
  1. (optional) git pull
  2. reads the version from the repository
  3. builds it with PyInstaller (its own onedir .spec)
  4. zips dist/<program>/ into downloads/<Name>_v<version>_Windows_x64.zip,
     adding THIRD_PARTY_LICENSES/ (license texts of everything bundled)
  5. copies the user manual into downloads/
  6. writes the release notes from the commits since the last release
     (Claude, see release_notes.py) and updates js/releases.js + index.html
  7. (optional) uploads the zip to the GitLab package registry of
     code.ill.fr/fabelo/software and links the page to it (--upload)
  8. (optional) commits and pushes the site to GitHub, which redeploys
     GitHub Pages (--push)
  9. (optional) copies the web folder to a server folder (--deploy)

USUAL COMMAND - update everything to the latest code
-----------------------------------------------------
Bump the version in the program(s) you want to release and push, then:

    cd C:\\ILL_Git\\software
    python tools/publish.py all --pull --upload --push --dry-run   # 1. check
    python tools/publish.py all --pull --upload --push             # 2. do it

It pulls both repositories, builds with PyInstaller every program whose
version changed (from the .spec at the root of C:\\ILL_Git\\Panda and
C:\\ILL_Git\\Edit_PyCR), zips it into downloads/, copies the manual, writes
the release notes and updates the web page. The zip and manual of the
previous version are deleted from downloads/ to save space. The notes always describe what
is inside the zip: every commit since the previous zip goes into the new
version. A program whose version did not change is not built (the script
says whether it has changes pending; use --rebuild to put them into the
current version).
--upload puts the zip in the package registry (the zips are too big for git
and for Pages) and --push commits and pushes the page, so the public site
is updated a minute later.

Other uses (from this folder):

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
    --upload         upload the zip to the GitLab package registry and make the
                     download button point there. On a program whose version did
                     not change, uploads the zip already on the page if it is
                     still a local file.
    --push           git commit + push the site to GitHub (Pages redeploys it)
    --deploy [DIR]   copy the site to DIR (default: "deploy_dir" in
                     tools/deploy.json, or the WEB_DEPLOY_DIR variable)
    --dry-run        show what would happen, change nothing

The version is bumped in the program itself (metadata.py / app_version.py)
and committed before running this; the release notes cover the commits
since the previous release up to HEAD.

--upload needs a GitLab personal access token with the "api" scope in the
GITLAB_TOKEN environment variable (setx GITLAB_TOKEN "glpat-...").
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
import urllib.error
import urllib.request
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
        # resources/tools/edit_pycr_conv.dll links CrysFML and FullProf's
        # FullPLib statically (fortran_codes/build.bat); the .pcr templates
        # are FullProf's examples
        "components": [
            ("CrysFML", "LGPL-3.0-or-later (no military use)",
             "edit_pycr_conv.dll (statically linked)", ["CrysFML-LICENSE.txt"]),
            ("FullProf library (FullPLib) and example .pcr files",
             "Copyright J. Rodriguez-Carvajal, ILL - all rights reserved",
             "edit_pycr_conv.dll, templates/", ["FullProf-LICENSE.txt"]),
            ("Intel Fortran runtime", "Intel redistributable",
             "edit_pycr_conv.dll (statically linked)", []),
        ],
    },
}

# License texts the wheels don't carry (PySide6 ships only its commercial one).
LICENSES = WEB / "tools" / "licenses"
LICENSE_FILE = re.compile(r"LICEN[CS]E|COPYING|NOTICE|AUTHORS", re.I)

# GitLab project that hosts the site and, in its package registry, the zips.
GITLAB = "https://code.ill.fr"
PAGES_REMOTE = "github"  # the site is pushed here only (not to code.ill.fr)
PROJECT_ID = 1699  # fabelo/software

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


def dist_license(dist):
    meta = dist.metadata
    text = meta.get("License-Expression") or meta.get("License") or ""
    if text and "\n" not in text.strip() and len(text) < 80:
        return text.strip()
    classifiers = [c.split("::")[-1].strip() for c in meta.get_all("Classifier") or []
                   if c.startswith("License ::")]
    return "; ".join(classifiers) or "see license files"


def third_party_licenses(src, name, cfg):
    """{path in the zip: bytes} for THIRD_PARTY_LICENSES/: the license files of
    every Python distribution bundled in dist/<program>/_internal, of Python
    itself and of the PyInstaller bootloader, plus a README listing them.

    The metadata comes from this interpreter, which is the one that runs
    PyInstaller in build(), so the versions are the ones in the zip."""
    import importlib.metadata as md
    top = md.packages_distributions()
    internal = src / "_internal"
    names = set()
    for p in internal.iterdir() if internal.is_dir() else []:
        stem = p.name.split("-")[0] if p.name.endswith(".dist-info") else p.name
        stem = stem.removesuffix(".libs").split(".")[0]
        names.update(top.get(stem, []))
    names.add("pyinstaller")

    out, rows, seen = {}, [], set()
    root = "THIRD_PARTY_LICENSES"
    for dname in sorted(names, key=str.lower):
        try:
            dist = md.distribution(dname)
        except md.PackageNotFoundError:
            continue
        key = dist.metadata["Name"].lower().replace("_", "-")
        if key in seen:
            continue
        seen.add(key)
        folder = f"{root}/{dist.metadata['Name']}-{dist.version}"
        found = 0
        for f in dist.files or []:
            parts = Path(str(f)).parts
            if not parts[0].endswith(".dist-info") or not LICENSE_FILE.search(f.name) \
                    or "Qt-Commercial" in f.name:
                continue
            out[f"{folder}/{'/'.join(parts[1:])}"] = Path(f.locate()).read_bytes()
            found += 1
        if key in ("pyside6", "shiboken6"):
            for t in ("LGPL-3.0.txt", "GPL-3.0.txt"):
                out[f"{folder}/{t}"] = (LICENSES / t).read_bytes()
            found += 2
        elif key in ("pyside6-essentials", "pyside6-addons"):
            found = 1  # the Qt libraries of PySide6: its license texts cover them
        if not found:
            print(f"   WARNING: no license file in the {dist.metadata['Name']} wheel")
        where = "PyInstaller bootloader (the .exe)" if key == "pyinstaller" else "_internal/"
        rows.append((dist.metadata["Name"], dist.version, dist_license(dist), where))

    python_license = Path(sys.base_prefix) / "LICENSE.txt"
    if python_license.exists():
        out[f"{root}/Python-{sys.version.split()[0]}/LICENSE.txt"] = python_license.read_bytes()
    rows.append(("Python", sys.version.split()[0], "PSF-2.0 (+ OpenSSL, libffi, zlib...)",
                 "_internal/python3*.dll"))
    rows.append(("Microsoft Visual C++ runtime", "", "Microsoft redistributable",
                 "_internal/VCRUNTIME140*.dll, MSVCP140*.dll, ucrtbase.dll"))
    for comp, lic, where, files in cfg.get("components", []):
        folder = f"{root}/{comp.split(' (')[0].split(' and ')[0].replace(' ', '_')}"
        for t in files:
            out[f"{folder}/{t}"] = (LICENSES / t).read_bytes()
        rows.append((comp, "", lic, where))

    # name + version, license; where it is on a second line, unless in _internal/
    w = max(len(f"{r[0]} {r[1]}") for r in rows if r[1]) + 2

    def line(r):
        head = f"{r[0]} {r[1]}".strip()
        head = f"{head:<{w}}" if len(head) < w else f"{head}\n{'':<{w}}"
        return head + r[2] + ("" if r[3] == "_internal/" else f"\n{'':<{w}}in {r[3]}")
    table = "\n".join(line(r) for r in rows)
    out[f"{root}/README.txt"] = f"""\
Third-party software in {name}
{'=' * (23 + len(name))}

{name} is distributed as a program built with PyInstaller. It contains the
components below; each folder here holds their license texts.

{table}

Qt for Python (PySide6, shiboken6) and Qt are used under the GNU LGPL v3.
Their libraries are the separate files in _internal/PySide6/ and
_internal/shiboken6/ and can be replaced with other builds of the same
version. Their source code is at https://code.qt.io and
https://download.qt.io/official_releases/QtForPython/.
""".replace("\n", "\r\n").encode("utf-8")
    print(f"   THIRD_PARTY_LICENSES: {len(rows)} components, {len(out)} files")
    return out


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
        if (src / "_internal").is_dir():
            third_party_licenses(src, name, cfg)
        return rel
    licenses = third_party_licenses(src, name, cfg)
    DOWNLOADS.mkdir(exist_ok=True)
    tmp = dest.with_suffix(".zip.part")
    with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for p in sorted(src.rglob("*")):
            if p.is_file():
                z.write(p, Path(src.name) / p.relative_to(src))
        for arc, data in licenses.items():
            z.writestr(f"{src.name}/{arc}", data)
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


def gitlab_token():
    """GITLAB_TOKEN from the environment, or from the user variables in the
    registry when it was set with setx after this terminal was opened."""
    token = os.environ.get("GITLAB_TOKEN")
    if not token and sys.platform == "win32":
        import winreg
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as k:
                token = winreg.QueryValueEx(k, "GITLAB_TOKEN")[0]
        except OSError:
            pass
    if not token:
        sys.exit('--upload needs a GitLab token with the "api" scope: setx GITLAB_TOKEN "glpat-..."')
    return token


def registry_url(key, version, filename):
    """Public download address of a file in the project's generic package registry."""
    return f"{GITLAB}/api/v4/projects/{PROJECT_ID}/packages/generic/{key}/{version}/{filename}"


def upload(key, version, rel, dry):
    """Upload downloads/<zip> to the package registry; returns its public URL."""
    src = WEB / rel
    url = registry_url(key, version, src.name)
    print(f"   {rel} -> {url}")
    if dry:
        return url
    if not src.exists():
        sys.exit(f"{src} not found - nothing to upload.")
    size = src.stat().st_size
    t0 = time.time()
    with src.open("rb") as f:
        req = urllib.request.Request(url, data=f, method="PUT", headers={
            "PRIVATE-TOKEN": gitlab_token(), "Content-Length": str(size),
            "Content-Type": "application/octet-stream"})
        try:
            with urllib.request.urlopen(req, timeout=1800) as r:
                r.read()
        except urllib.error.HTTPError as e:
            sys.exit(f"Upload failed: HTTP {e.code} {e.read().decode(errors='replace')[:300]}")
    print(f"   uploaded {size / 2**20:.0f} MB in {time.time() - t0:.0f} s")
    # the page must not point at a file that is not really there
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60):
            pass
    except urllib.error.HTTPError as e:
        sys.exit(f"The upload finished but {url} answers HTTP {e.code}.")
    return url


def push(published, dry):
    """Commit the site and push it to GitHub; GitHub Pages redeploys it."""
    step("Committing and pushing the site")
    if not (WEB / ".git").exists():
        sys.exit(f"{WEB} is not a git repository.")
    changed = rn.git(WEB, "status", "--porcelain").strip()
    if changed:
        print("   " + "\n   ".join(changed.splitlines()))
        msg = "Publish " + ", ".join(published) if published else "Update the site"
        print(f"   commit: {msg}")
    else:
        print("   nothing to commit")
    remotes = [PAGES_REMOTE]
    print(f"   push to: {', '.join(remotes)}")
    if dry:
        return
    if changed:
        rn.git(WEB, "add", "-A")
        rn.git(WEB, "commit", "-m", msg)
    # Push even with nothing new to commit, so a remote left behind catches up.
    for remote in remotes:
        rn.git(WEB, "push", remote, "HEAD")
    print("   pushed - the site is redeployed in about a minute")


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
        if a.upload and not sw["latest"]["file"].startswith("http"):
            step(f"{name}: upload of the zip on the page")
            sw["latest"]["file"] = upload(key, last, sw["latest"]["file"], a.dry_run)
            return f"{name} {last} (zip moved to the package registry)"
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
    size = rn.file_size(WEB / file)
    if a.upload:
        step(f"{name}: upload to the package registry")
        file = upload(key, version, file, a.dry_run)

    if a.rebuild:
        # same version, newer zip: its notes grow with what the new build adds
        rn.add_release(sw, repo, version, notes + current["notes"], file, manual)
    else:
        rn.add_release(sw, repo, version, notes, file, manual)
    sw["latest"]["size"] = size  # add_release can't measure a URL
    return f"{name} {version}"


def main():
    ap = argparse.ArgumentParser(description="Build, package and publish PANDA / Edit_PyCR.")
    ap.add_argument("product", help="panda, editpycr or all")
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--skip-build", action="store_true")
    ap.add_argument("--rebuild", action="store_true")
    ap.add_argument("--no-ai", action="store_true")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--push", action="store_true")
    ap.add_argument("--deploy", nargs="?", const=True)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    header, data = rn.load_releases()
    keys = list(BUILD) if a.product == "all" else [a.product]
    for k in keys:
        if k not in BUILD or k not in data:
            sys.exit(f"Unknown product '{k}'. Choose from: {', '.join(BUILD)} or all")

    if a.upload and not a.dry_run:
        gitlab_token()  # fail now rather than after a long build
    published = [p for p in (publish(k, data, a) for k in keys) if p]

    step("Web page")
    if not published:
        print("   nothing published - page unchanged")
    elif a.dry_run:
        print("   (dry run: js/releases.js and index.html not written)")
    else:
        rn.save(header, data)
        print("   js/releases.js and index.html updated")

    if a.push:
        push(published, a.dry_run)
    if a.deploy:
        deploy(deploy_target(a.deploy), a.dry_run)
    if not (a.push or a.deploy):
        print("\nDone. Open index.html to check, then publish with --push "
              "(git push to GitHub) or --deploy DIR.")


if __name__ == "__main__":
    main()
