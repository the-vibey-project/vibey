## Title
feat(qwenloop): QWENLOOP_SHELL_TIMEOUT_SECONDS sets the shell tool's timeout

## Why
harness-T20a declared `shell_timeout_seconds` in `QwenConfig`. qwenloop layers its settings as
config file, then environment, then flags (`src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py:25-31`),
and every environment key is declared, not invented at the call site (12.c,
`src/vibey_tools/gh/docs/doctrines.md:455`). A storm lane's driver and an operator both set the
limit through the environment, without writing a config file. Draft ADR-0045 §11 names the
variable `QWENLOOP_SHELL_TIMEOUT_SECONDS`.

## Required behaviour
In `src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py`:
1. After `ENV_API_KEY` (`:20-22`), declare
   ```python
   #: How long the shell tool lets one command run (`shell_timeout_seconds`); 120 when unset.
   ENV_SHELL_TIMEOUT = "QWENLOOP_SHELL_TIMEOUT_SECONDS"
   ```
2. `SettingsLoader.ENVIRONMENT_KEYS` (`:33`) gains `ENV_SHELL_TIMEOUT: "shell_timeout_seconds"`.
   The loader passes the string on; `QwenConfigParser` converts it with `int` and refuses a value
   ≤ 0 (harness-T20a). A blank value does not override (`:57-60`).

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py` (with `edit_file`).
- `src/vibey_runners/qwen/tests/test_settings.py` (append one test).

## Acceptance criteria
- [ ] A config file's `shell_timeout_seconds = 300` gives 300; `QWENLOOP_SHELL_TIMEOUT_SECONDS=600` beats it; a flag override (`load({"shell_timeout_seconds": 900})`) beats both; a blank variable does not override.
- [ ] `QWENLOOP_SHELL_TIMEOUT_SECONDS=0` makes `load()` raise `ValueError`.
- [ ] The tenant suite passes at its 100% floor, and its static gates pass.

## Tests to write first (TDD)
Appended to `src/vibey_runners/qwen/tests/test_settings.py` (copy the shape of
`test_file_then_environment_then_flags`, `:25-49`; pass `environ` dicts, no `monkeypatch.setattr`):
- `test_shell_timeout_from_file_and_environment`

## Checks the lane must run (all must pass)
    (cd src/vibey_runners/qwen && uv run python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/qwen && uv run mypy --strict src/qwenloop && uv run lint-imports && uv run bandit -q -r src/qwenloop)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The sandbox (harness-T20c) and `_run_plan` (harness-T20). Any vibey code. The storm driver.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T20a-qwenloop-shell-timeout-config.
- **Files touched:** `src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py`, `src/vibey_runners/qwen/tests/test_settings.py`.
- **Shares a file with:** none in flight.
- **Must keep passing unchanged:** the whole qwenloop suite at its 100% floor, and the protected root tests.
- **Registry (amendment A4):** nothing; no seam is declared.
- **Standing constraints (every qwenloop harness lane):**
  - This lane changes a runner tenant and runs that tenant's own gates (ADR-0022); qwenloop does not import vibey.
  - The tenant's in-memory fakes live in `src/vibey_runners/qwen/tests/fakes.py` (it exists; append to it, never recreate it).
  - Substitute only at a declared seam. Never add `monkeypatch.setattr`, `mock.patch` or `MagicMock`; `setenv` and `delenv` are allowed.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - No test needs a model server or waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
