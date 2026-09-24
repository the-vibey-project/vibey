## Title
ci: `vibey install --check` and `vibey doctor` are smoke-tested on Arch Linux and macOS

## Why
8.h (`src/vibey_tools/gh/docs/doctrines.md:326-333`) says the installer serves both default OSes.
The operator's standard is "the installer installs everything a developer needs on Arch and
macOS". The installer lanes test only against faked package managers (`issue-audit/gaps.md` F5).
Nothing proves that the real host detection, the catalogue resolution and the doctor lines run
on a real Arch or macOS host.

This lane smoke-tests the **report** paths (`--check`, `doctor`). They read the host and install
nothing. A real install in CI is out of scope: an Arch container has no systemd to start
services, and the model is 14 GB.

## Required behaviour
1. `ci.yml` gains a job `installer-smoke` with a two-row matrix:
   - `os: macos-latest` with no container;
   - `os: ubuntu-latest` with `container: archlinux:base-devel` and `label: Arch Linux`.

   Use `container: ${{ matrix.container }}` only if the lane first confirms, in the job's own
   run, that an empty value is accepted. Otherwise use two jobs, `installer-smoke-arch` and
   `installer-smoke-macos`, with identical steps. Prefer the two-job form: it is certain.
2. Steps:
   - on Arch, first `pacman -Syu --noconfirm --needed git uv`;
   - `actions/checkout@v4` (and `safe.directory` on Arch);
   - `uv python install 3.12 && uv sync --extra dev`;
   - then:
     ```bash
     set -uo pipefail
     out=$(uv run vibey install --check 2>&1); code=$?
     echo "$out"
     # 0 = everything ready, 1 = something missing; anything else is a crash.
     case "$code" in 0|1) ;; *) echo "::error::vibey install --check exited $code"; exit 1 ;; esac
     echo "$out" | grep -E '^host: (Arch Linux|macOS)' \
       || { echo "::error::no default-OS host line"; exit 1; }
     for key in postgres ollama model; do
       echo "$out" | grep -qi "$key" || { echo "::error::no line for $key"; exit 1; }
     done
     uv run vibey doctor || { echo "::error::vibey doctor failed"; exit 1; }
     ```
     The host line text follows `installer-cli`'s presenter, `f"host: {report.host_label}"`.
     Read that lane's final code and match its labels exactly.
3. Append to `tests/meta/test_ci_default_os.py`: `test_the_installer_is_smoked_on_both_default_oses`.
   It asserts that jobs (or matrix rows) cover `macos-latest` and the `archlinux:base-devel`
   container, and that their run blocks contain `vibey install --check` and `vibey doctor`.

## Where to change
- `.github/workflows/ci.yml` (edit_file; insert after `gates-macos`).
- `tests/meta/test_ci_default_os.py` (append).

## Acceptance criteria
- [ ] The YAML loads, and the meta-test passes.
- [ ] **Evidence, recorded by the reviewer:** both smoke jobs are green on the first run. Their logs show
      the host line and one line per default dependency, with exit 0 or 1.

## Tests to write first (TDD)
Append to `tests/meta/test_ci_default_os.py`:
- `test_the_installer_is_smoked_on_both_default_oses`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run pytest -q -p no:cacheprovider tests/meta

## Out of scope
- A real install in CI (a follow-up on a self-hosted Arch machine), and docs.

Commit as `ci: smoke the installer's report on Arch Linux and macOS`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
