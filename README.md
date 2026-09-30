# Oscar Fabelo – personal page (ILL)

Static site, no build step: open `index.html` in a browser, or copy the whole
folder to the ILL web server.

```
index.html              the page
css/style.css           styles (ILL palette: navy + #0779AD)
js/main.js              menu, hero, release notes, publication search/filter
js/releases.js          software versions, download files and release notes
js/publications.js      publication list, generated from Zotero
img/                    screenshots and app icons
downloads/              PANDA and Edit_PyCR packages + user manuals
tools/publish.py        builds, packages and publishes PANDA / Edit_PyCR
tools/release_notes.py  turns git commits into release notes (used by publish.py)
tools/zotero_export.py  regenerates js/publications.js
```

## Updating

**Publications** – add the paper to Zotero, then:

```
python tools/zotero_export.py
```

It reads a copy of `~/Zotero/zotero.sqlite`, so Zotero may stay open.
Everything co-authored by Fabelo with a DOI or journal is kept; errata and
drafts are skipped. The hero's publication count updates by itself.

**A new PANDA / Edit_PyCR version** – bump the version in the program
(`src/app/metadata.py` for PANDA, `src/edit_pycr/core/app_version.py` for
Edit_PyCR), commit, and run from this folder:

```
python tools/publish.py panda            # or editpycr, or all
python tools/publish.py all --deploy     # ... and copy the site to the server
```

`publish.py` does every step:

1. writes the release notes from the commits since the previous release:
   housekeeping commits are dropped and Claude rewrites the rest as short
   New / Improved / Fixed notes for users (`release_notes.py`);
2. runs PyInstaller with the `.spec` at the root of `C:\ILL_Git\Panda`
   (`panda_onedir.spec`) or `C:\ILL_Git\Edit_PyCR`
   (`fullprof_editor_onedir.spec`); the log goes to `tools/logs/`;
3. zips `dist/PANDA` or `dist/FullProf_Editor` into
   `downloads/<Name>_v<version>_Windows_x64.zip` and copies the user manual;
4. updates `js/releases.js` and `index.html` (download buttons, "Latest"
   banner, "What's new", cache-busting stamp);
5. with `--deploy`, copies `index.html`, `css/`, `js/`, `img/` and
   `downloads/` to the server folder (only files that changed).

Options: `--pull` (git pull first), `--rebuild` (rebuild and replace the
package of the version already on the page, notes unchanged),
`--skip-build` (package the existing `dist/`), `--no-ai` (commit subjects
as notes, to edit by hand), `--keep 2` (delete older zips and manuals),
`--dry-run` (show what would happen, change nothing).

The server folder for `--deploy` comes from `tools/deploy.json`, e.g.
`{"deploy_dir": "//server/share/fabelo"}`, or the `WEB_DEPLOY_DIR`
variable, or is given directly: `--deploy <folder>`.

Release notes are written by Claude Code with the Claude subscription you
are logged in with (Pro is enough, no API key); the script finds the copy
installed with the VS Code extension. If `ANTHROPIC_API_KEY` is set it uses
the Claude API instead. Without either, use `--no-ai`.
The notes of a version always describe what is inside its zip (each release
records the commit it was built from). `python tools/release_notes.py panda`
previews the notes for the commits made since the last zip. The notes are plain JSON in `js/releases.js` and can
always be corrected by hand (double quotes, no trailing commas).

**Citation metrics** (hero card) are typed by hand from Google Scholar.
