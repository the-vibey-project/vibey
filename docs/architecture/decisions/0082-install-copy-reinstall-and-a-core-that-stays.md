# 0082 — Install, copy and reinstall in one command; the krypton interfaces uninstall cleanly; the core stays

**Status:** accepted · **Date:** 2026-10-03 · **Cites:** sub-doctrines 10.h, 10.l, 10.m, 12.c, 12.e and 12.h · **Related:** ADR-0019, ADR-0021, ADR-0037, ADR-0069, ADR-0080 · **Evidence:** `develop` at `3245dc5d8`; the files of `krypton-desktop-0.1.0-linux-x86_64.tar.gz` in the 3.4.0 release · **Canon:** drafts sub-doctrine 10.m, ratified by the operator's merge under Article II.3

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`; `properdocs.yml` nav entries for this record and for
`docs/guides/install.md`; `docs/llms.txt` regenerated from that nav. All are in the change
that carries this record.

## Context

The operator asked for the codebase to be "as easy to copy and reinstall as insanely
possible", for an uninstall script for every krypton interface and the TUI, and ruled that
"vibey-engine's core lives forever, no uninstall script for that". Installing already took
one documented command (`uv tool install vibey-engine`), but nothing removed the clients:
krypton desktop alone installs three different ways (a Flatpak, four files under `/usr` from
the Ubuntu tarball, a macOS app), and its pairing with a hub leaves a device key on disk.

## Decision

1. **`scripts/install.sh`** installs uv if missing, then `uv tool install --reinstall
   vibey-engine`, and ends with `vibey doctor`. Because it reinstalls, running it again is a
   repair. `--with-krypton` adds `krypton-app`; `--from-source DIR` clones the full history
   into `DIR`, builds it with `uv sync --extra dev` and installs the commands from that copy,
   updating the same copy when run again.
2. **`scripts/uninstall-krypton.sh`** removes the krypton interfaces: `krypton-app` by the
   tool that installed it, the editor extension from every VS Code-family editor, and krypton
   desktop in each of its three forms. It is a dry run unless given `--yes`; it removes the
   macOS app only when its `Info.plist` names krypton's identifier; it never escalates —
   a root-owned file is printed as a `sudo` command; and it keeps settings and the pairing
   unless given `--purge`, printing the `vibey hub revoke` command first.
3. **The core is never uninstalled** (sub-doctrine 10.m). Neither script, nor anything else
   the project ships, removes vibey-engine. "The TUI" in the request is read accordingly: the
   `vibey` TUI is part of the core and stays; the terminal interface that belongs to krypton is
   the `krypton` command, which goes.
4. **Both are POSIX `sh`**, so they run before Python or uv exist, and both run from
   `curl … | sh` without a clone. Their identifiers default to the shipped ones and can be
   overridden by environment variables (12.h).

## Consequences

- `tests/scripts/test_install_scripts.py` runs both scripts for real against recording stubs
  of every tool they call, so each behaviour above is shown, and the invariant that nothing
  removes vibey-engine is asserted on every run. `tests/meta/test_install_scripts.py` checks
  each hard-coded identifier against the source it comes from — the Flatpak manifest, the
  desktop data files, the extension's manifest, the package names, and the binary the release
  checks — so a rename fails CI rather than leaving an uninstaller that misses its target.
- The Ubuntu tarball's file list is declared in the uninstaller. If a release starts
  installing more files, the meta test does not see them; shipping an install manifest inside
  the tarball would close that gap and is left for the release lane.
- The phone apps cannot be removed from a computer; the uninstaller says so rather than
  pretending.
