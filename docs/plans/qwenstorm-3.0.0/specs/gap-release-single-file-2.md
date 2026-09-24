## Title
build(release): a PyInstaller recipe builds the single-file vibey from the release wheel

## Why
ADR-0019 step 2 (`docs/architecture/decisions/0019-installable-wherever-its-users-are.md:114-115`)
says: "A single-file executable as a release artifact. Unblocks most of what follows." The ADR
names "shiv, pex or PyInstaller" (`:103-104`) without choosing. That choice is
`gap-ops-canon-rulings` item 9. This spec is written for **PyInstaller**, the only one of the
three that needs no Python on the target. That is what sub-doctrine 2.b asks
(`src/vibey_tools/gh/docs/doctrines.md:30`: "the language it happens to be written in is an
implementation detail no reader is asked to care about"). **If ruling 9 names shiv or pex,
stop and report BLOCKED**, so the spec can be rewritten for that tool.

The build installs the same wheel PyPI receives into a throwaway environment, then freezes
it. The frozen program therefore holds exactly what `pip install vibey` would, the migrations
included (`gap-pkg-migrations-in-wheel`). One binary serves all twelve console scripts
through `vibey.cli.multicall` (`gap-release-single-file-1`). Nothing exists yet
(`issue-audit/gaps.md` G2, lines 395-400).

## Required behaviour
1. New `packaging/single-file/entry.py` (provenance line 1):
   ```python
   """PyInstaller's entry script for the single-file vibey (ADR-0019 step 2).

   Module-level code by necessity: PyInstaller runs this file as __main__. The dispatch
   itself is vibey.cli.multicall.MultiCallDispatcher, a class with an interface (9.b).
   """

   import sys

   from vibey.cli.multicall import MULTICALL

   raise SystemExit(MULTICALL.main(sys.argv))
   ```
2. New `packaging/single-file/vibey.spec` (provenance line 1), with a comment block (it is
   run through `build.sh`, which installs the release wheel first), then:
   ```python
   import os

   from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

   # Every package root the wheel ships (pyproject.toml [tool.hatch.build.targets.wheel.sources]);
   # tests/meta/test_single_file_build.py keeps this tuple equal to that table.
   PACKAGES = (
       "vibey",
       "claudeloop",
       "codexloop",
       "cursorloop",
       "agyloop",
       "qwenloop",
       "opencodeloop",
       "vibey_runners",
       "vibey_gh",
       "vibey_bootstrap",
       "vibey_skills",
   )

   hiddenimports = [name for package in PACKAGES for name in collect_submodules(package)]
   datas = [entry for package in PACKAGES for entry in collect_data_files(package)]
   datas += copy_metadata("vibey", recursive=True)

   a = Analysis(  # noqa: F821 -- PyInstaller injects Analysis, PYZ, EXE and SPECPATH
       [os.path.join(SPECPATH, "entry.py")],  # noqa: F821
       hiddenimports=hiddenimports,
       datas=datas,
       excludes=["tkinter"],
   )
   pyz = PYZ(a.pure)  # noqa: F821
   exe = EXE(  # noqa: F821
       pyz,
       a.scripts,
       a.binaries,
       a.datas,
       [],
       name="vibey",
       console=True,
       strip=False,
       upx=False,
   )
   ```
   If the frozen program fails on an import, add that module to `hiddenimports`, or
   `collect_submodules("<package>")`, with a comment naming the error it fixed. Never
   collect the whole dependency tree.
3. New `packaging/single-file/build.sh` (mode 755). Line 1 is `#!/usr/bin/env bash` and line 2
   is the provenance line, as a `#` comment:
   ```bash
   # Build the single-file vibey (ADR-0019 step 2; sub-doctrine 2.b) from the wheel PyPI gets.
   # Usage: packaging/single-file/build.sh OUTPUT_PATH
   set -euo pipefail
   out=${1:?usage: packaging/single-file/build.sh OUTPUT_PATH}
   case "$out" in /*) ;; *) out="$PWD/$out" ;; esac
   root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
   work=$(mktemp -d)
   trap 'rm -rf "$work"' EXIT
   cd "$root"
   uv build --wheel --out-dir "$work/wheel"
   uv venv --python 3.12 "$work/venv"
   python="$work/venv/bin/python"
   [ -x "$python" ] || python="$work/venv/Scripts/python.exe"
   uv pip install --python "$python" "$work"/wheel/*.whl "pyinstaller>=6.10,<7"
   "$python" -m PyInstaller --version
   "$python" -m PyInstaller --noconfirm --clean \
     --distpath "$work/dist" --workpath "$work/build" \
     packaging/single-file/vibey.spec
   built="$work/dist/vibey"
   [ -f "$built" ] || built="$work/dist/vibey.exe"
   mkdir -p "$(dirname "$out")"
   cp "$built" "$out"
   chmod +x "$out"
   echo "built $out"
   ```
4. Append to `packaging/channels.toml`, preceded by one blank line. The channel is declared
   but not enabled. `gap-release-single-file-3` enables it with the release job:
   ```toml
   [[channel]]
   name = "single-file"
   ecosystem = "single-file"
   publisher = "release-asset"
   branches = ["main"]
   definition = ["packaging/single-file/build.sh", "packaging/single-file/vibey.spec", "packaging/single-file/entry.py"]
   assets = ["vibey-{version}-linux-x86_64", "vibey-{version}-linux-aarch64", "vibey-{version}-macos-arm64", "vibey-{version}-macos-x86_64", "vibey-{version}-windows-x86_64.exe"]
   excludes = "PostgreSQL, Ollama and its model, and the vendor engine CLIs (Claude Code, Codex, Cursor, Antigravity); the executables are not code-signed; vibey doctor reports what is missing."
   grace_hours = 2
   probe = { url = "https://github.com/the-vibey-project/vibey/releases/download/vibey-v{version}/SHA256SUMS" }
   enabled = false
   ```
5. New meta-test `tests/meta/test_single_file_build.py` (provenance line 1):
   - `test_the_spec_freezes_every_package_the_wheel_ships`: `ast`-parse `vibey.spec`, find the
     `PACKAGES` tuple, and compare it as a set to the values of
     `[tool.hatch.build.targets.wheel.sources]` in `pyproject.toml`.
   - `test_the_spec_carries_the_distributions_metadata`: the text holds
     `copy_metadata("vibey", recursive=True)` and `collect_data_files(package)`.
   - `test_the_entry_script_dispatches_through_multicall`: `entry.py` holds
     `from vibey.cli.multicall import MULTICALL` and `MULTICALL.main(sys.argv)`.
   - `test_the_build_script_builds_from_the_wheel`: `build.sh` holds `uv build --wheel`,
     `"pyinstaller>=6.10,<7"` and `packaging/single-file/vibey.spec`. It is executable
     (`os.access(path, os.X_OK)`), and `bash -n` accepts it.
   - `test_the_single_file_channel_is_declared`: the registry (`vibey_gh.channels.CHANNEL_REGISTRY_LOADER`)
     has channel `single-file`, with publisher `release-asset`, the five assets above, and a
     `definition` naming the three files.

## Where to change
- New `packaging/single-file/entry.py`, `packaging/single-file/vibey.spec`, `packaging/single-file/build.sh` (then `chmod 755`).
- `packaging/channels.toml` (append).
- New `tests/meta/test_single_file_build.py`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider tests/meta` passes, `test_packaging_channels.py` included.
- [ ] A local build on the lane's host (macOS, the default paid OS, 8.h):
      `bash packaging/single-file/build.sh "$TMPDIR/onefile/vibey"` succeeds. Then:
      - `"$TMPDIR/onefile/vibey" --version` prints `vibey <the version in src/vibey/__init__.py>`;
      - `ln -sf vibey "$TMPDIR/onefile/claudeloop" && "$TMPDIR/onefile/claudeloop" --version` exits 0;
      - `"$TMPDIR/onefile/vibey" --as vibey-gh --help` and `"$TMPDIR/onefile/vibey" --as vibey-skills --help` exit 0.
      Paste the four outputs into the verdict. If the host cannot reach PyPI to install
      PyInstaller, say so, and report the local proof as not run (10.f). CI proves it in
      `gap-release-single-file-3`.
- [ ] Nothing is written inside the repository by the build (`git status --short` shows only this lane's files).

## Tests to write first (TDD)
`tests/meta/test_single_file_build.py`, with the five tests in item 5.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta
    bash -n packaging/single-file/build.sh

## Out of scope
- The release job, the Arch Linux proof, and publishing (`gap-release-single-file-3`).
- Code signing and notarization (an operator decision in `gap-ops-packaging-credentials`).
- The package-manager recipes (`gap-pkg-*`) and docs.

Commit as `build(release): a PyInstaller recipe for the single-file vibey`. Do not push.

## Lane card
- **Depends on:** `gap-ops-canon-rulings` (item 9, the tool), `gap-release-single-file-1`, `gap-pkg-migrations-in-wheel`, `gap-pkg-channels`.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
