## Title
feat(install): VS Code in the local stack — its open-source build for sovereignloop, Microsoft's opt-in for paid loops

## Why
Sub-doctrine 8.b (ratified in #392) repeals OpenCode and puts VS Code in both loops:
sovereignloop drives "VS Code when its provider is local", and paidloop's adapters include "VS
Code on a paid provider"; VS Code is also the default IDE for paid loops. The operator ruled on
2026-09-22 that **sovereignloop drives VS Code's open-source build, Code - OSS (as VSCodium ships
it)**, and that paidloop's VS Code is Microsoft's build. Microsoft's build carries a proprietary
licence and telemetry, so it never becomes a sovereign default (8.a, Article IV.2). So
`vibey install` offers two opt-in entries, never an OpenCode one:

- `vscode` — Code - OSS, the sovereign editor. Opt-in: an editor is a personal choice.
- `vscode-paid` — Microsoft's VS Code, for paid loops. Opt-in and declared, like every paid tool.

The packages, read 2026-09-22:
- Arch: `extra/code` — Code - OSS, MIT-licensed, built by Arch from source; binary `code`.
  Microsoft's build is the AUR's `visual-studio-code-bin`, binary `code`; the two packages
  conflict, so installing `vscode-paid` on Arch replaces Code - OSS (pacman asks).
- macOS: the `vscodium` cask (binary `codium`) for Code - OSS; the `visual-studio-code` cask
  (binary `code`) for Microsoft's build.

## Required behaviour
1. Append these entries at the end of `CATALOGUE_ENTRIES` in `src/vibey/domain/local_stack.py`:
   - key "vscode", title "VS Code (Code - OSS)", group "editor", default False, installer `PACKAGE`.
     - arch: `HostRecipe(PackageSpec(PACMAN, ("code",), ("code",)))`.
     - macos: `HostRecipe(PackageSpec(BREW_CASK, ("vscodium",), ("codium",)))`.
     - note: "opt-in. VS Code's open-source build, Code - OSS: the sovereign editor (8.b)."
   - key "vscode-paid", title "VS Code (Microsoft)", group "paid-editor", default False,
     installer `PACKAGE`.
     - arch: `HostRecipe(PackageSpec(AUR, ("visual-studio-code-bin",), ("code",)))`.
     - macos: `HostRecipe(PackageSpec(BREW_CASK, ("visual-studio-code",), ("code",)))`.
     - note: "opt-in and declared: Microsoft's build, the default IDE for paid loops (8.b). On
       Arch it replaces Code - OSS."
2. `resolve(host)` excludes both. `resolve(host, extra=("vscode",))` and
   `resolve(host, extra=("editor",))` include only `vscode`; `resolve(host, extra=("vscode-paid",))`
   and `resolve(host, extra=("paid-editor",))` include only `vscode-paid`.

## Where to change
- `src/vibey/domain/local_stack.py`: append the two entries. Use edit_file.
- `tests/domain/test_local_stack.py`: append tests.
- No other file.

## Acceptance criteria
- [ ] Neither entry is in the default set on either OS.
- [ ] `vscode` is Code - OSS on both OSes: pacman `code` (binary `code`) on Arch, the `vscodium`
      cask (binary `codium`) on macOS.
- [ ] `vscode-paid` is Microsoft's build: AUR `visual-studio-code-bin` on Arch, the
      `visual-studio-code` cask on macOS, both detecting `code`.
- [ ] The group names select exactly their own entry.
- [ ] The guard tests pass, with 100% domain coverage.

## Tests to write first (TDD)
Append to `tests/domain/test_local_stack.py`:
- `test_both_vscode_entries_are_opt_in`
- `test_the_sovereign_vscode_is_code_oss_on_both_oses`
- `test_the_paid_vscode_is_microsofts_build_on_both_oses`
- `test_editor_and_paid_editor_groups_select_their_own_entry`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- VS Code extensions or settings; the VS Code loop adapter itself (ADR-0046's lanes).
- Removing opencodeloop, which the canon repeal and its own lanes handle.
- An OpenCode install entry.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
