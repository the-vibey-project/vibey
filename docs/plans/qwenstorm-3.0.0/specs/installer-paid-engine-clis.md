## Title
feat(install): the paid engines' vendor CLIs are opt-in, one per engine, from Homebrew casks and the AUR

## Why
The paid loop engines are `claudeloop`, `codexloop`, `cursorloop` and `agyloop`. They ship
inside vibey (ADR-0037), but each drives a vendor CLI that vibey does not ship:
- `claude` (`src/vibey_runners/claude`);
- `codex` (`src/vibey_runners/codex/src/codexloop/infrastructure/agent/argv.py:71`);
- Cursor's agent (`src/vibey_runners/cursor/src/cursorloop/infrastructure/agent/cli_fallback.py:34`);
- `agy` (`src/vibey_runners/agy`).

Sub-doctrine 8.b (doctrines.md:118-119) makes the paid engines declared-only. So each CLI is
opt-in, per engine: `vibey install --with claude`, and so on, or `--with paid-engine` for all
four. Installing a CLI does not enable its engine; that stays a declaration in `vibey.toml`
`[engines]`.

The vendors' own installers are `curl … | sh`, which is forbidden. Every one of these CLIs has
a Homebrew cask and an AUR package (read 2026-09-22 from formulae.brew.sh and
aur.archlinux.org). None is in Arch's official repositories, so Arch uses an AUR helper, which
lane installer-host-runner requires to be paru or yay, run as the user:

| key | macOS cask (binary) | Arch AUR package (binary) |
|---|---|---|
| claude | `claude-code` (`claude`) | `claude-code` (`claude`) |
| codex | `codex` (`codex`) | `openai-codex-bin` (`codex`) |
| cursor | `cursor-cli` (`cursor-agent`) | `cursor-cli` (`cursor-agent`) |
| agy | `antigravity-cli` (`agy`) | `antigravity-cli` (`agy`) |

**Known gap:** cursorloop's CLI fallback runs `agent`, while both packages install only
`cursor-agent`. The AUR PKGBUILD links `/usr/bin/cursor-agent`, and the cask's only binary is
`cursor-agent`. The catalogue therefore detects either name. Teaching cursorloop to accept `cursor-agent` is a follow-up in the cursor tenant,
not this lane.

## Required behaviour
1. Append four entries at the end of `CATALOGUE_ENTRIES` in `src/vibey/domain/local_stack.py`,
   in the table's order. Each has group "paid-engine", default False and installer `PACKAGE`,
   and each has these recipes:
   - arch: `HostRecipe(PackageSpec(AUR, (<aur>,), <binaries>))`;
   - macos: `HostRecipe(PackageSpec(BREW_CASK, (<cask>,), <binaries>))`.

   Titles: "Claude Code CLI", "Codex CLI", "Cursor agent CLI", "Antigravity CLI".
   `binaries` are `("claude",)`, `("codex",)`, `("cursor-agent", "agent")` and `("agy",)`.
   Each note is: "opt-in: paid engines are declared-only (8.b); installing the CLI does not
   enable the engine". The cursor note adds: "cursorloop's fallback runs `agent`; the
   packages install `cursor-agent` (follow-up)".
2. `resolve(host)` includes none of them. `extra=("claude",)` adds exactly claude, and
   `extra=("paid-engine",)` adds all four in order.

## Where to change
- `src/vibey/domain/local_stack.py`: append the entries. Use edit_file.
- `tests/domain/test_local_stack.py`: append tests.
- No other file.

## Acceptance criteria
- [ ] No paid CLI appears in either OS's default resolution.
- [ ] Each key can be selected alone, and the group selects all four.
- [ ] Arch recipes use `PackageSource.AUR`, and macOS recipes use `BREW_CASK`, with the exact
      names in the table.
- [ ] The guard tests pass, with 100% domain coverage.

## Tests to write first (TDD)
Append to `tests/domain/test_local_stack.py`:
- `test_paid_engine_clis_are_never_default` (the 8.b guard)
- `test_each_paid_cli_is_selectable_alone_and_as_a_group`
- `test_paid_cli_package_names_per_os`, parametrized over the table.
- `test_cursor_detects_either_agent_binary`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/domain
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- Signing in to any vendor.
- Enabling engines in `vibey.toml`.
- The cursorloop binary-name fix.
- The OpenCode CLI, which is being repealed from the canon.
- Docs.

Commit as `feat(install): ...`. Do not push.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
