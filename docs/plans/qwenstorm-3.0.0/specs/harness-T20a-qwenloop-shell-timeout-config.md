## Title
feat(qwenloop): shell_timeout_seconds is a qwenloop configuration key

## Why
qwenloop's `SandboxTools.execute` kills every shell command after a hard-coded 120 s
(`src/vibey_runners/qwen/src/qwenloop/infrastructure/tools.py:59-64`, `timeout=120` at `:60`).
Sub-doctrine 12.c (`src/vibey_tools/gh/docs/doctrines.md:455`): "a hard-coded value that could have
been a key is a decision taken away from the next human adopter". It also collides with 8.e
(`doctrines.md:271-292`): a storm lane's full-suite run was measured at 259 s
(`.pre-commit-config.yaml:18`), so it can never finish inside the tool, and waiting in the test
harness's queue makes that worse. Draft ADR-0045 §11 needs the limit configurable.

This lane is the first of four (T20a config → T20b environment → T20c sandbox → T20 the run):
it declares the key in qwenloop's pure configuration. The default stays 120, so nothing changes
until someone sets it.

## Required behaviour
In `src/vibey_runners/qwen/src/qwenloop/domain/config.py`:
1. `QwenConfig` (`:19-44`) gains, after `endpoint_timeout_seconds` (`:34`), a comment
   `# How long the shell tool lets one command run before killing it (ADR-0045 §11).` and the field
   `shell_timeout_seconds: int = 120`. `_KEYS` (`:47`) derives from the fields, so the key is
   accepted with no further change.
2. `QwenConfigParser.parse` (`:59-93`) reads it like `endpoint_timeout_seconds` (`:78-80`):
   `shell_timeout_seconds=int(data.get("shell_timeout_seconds", defaults.shell_timeout_seconds))`.
3. The positivity check (`:84-90`) gains `or config.shell_timeout_seconds <= 0`; its message
   (`"timeouts, context_window, and max_turns must be positive"`) already covers it.

## Where to change
- `src/vibey_runners/qwen/src/qwenloop/domain/config.py` (with `edit_file`).
- `src/vibey_runners/qwen/tests/test_domain.py` (append one test).

## Acceptance criteria
- [ ] `QwenConfigParser().parse({}).shell_timeout_seconds == 120`.
- [ ] `parse({"shell_timeout_seconds": 600})` gives 600; `0` and `-1` raise `ValueError` matching `positive`.
- [ ] The tenant suite passes at its 100% floor (`src/vibey_runners/qwen/pyproject.toml:68`), and its static gates pass.

## Tests to write first (TDD)
Appended to `src/vibey_runners/qwen/tests/test_domain.py` (it already has `parser = QwenConfigParser()` at module level):
- `test_shell_timeout_default_and_validation`

## Checks the lane must run (all must pass)
    (cd src/vibey_runners/qwen && uv run python -m pytest -q -p no:cacheprovider)
    (cd src/vibey_runners/qwen && uv run mypy --strict src/qwenloop && uv run lint-imports && uv run bandit -q -r src/qwenloop)
    uv run ruff check . && uv run ruff format --check .

## Out of scope
- The environment variable (harness-T20b), the sandbox (harness-T20c), `_run_plan` (harness-T20).
- Any vibey code. The storm driver (`qwenlane.py`, outside the repository).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** none.
- **Files touched:** `src/vibey_runners/qwen/src/qwenloop/domain/config.py`, `src/vibey_runners/qwen/tests/test_domain.py`.
- **Shares a file with:** `domain/config.py` (the qwenloop lanes; fakes-tenant-qwen-1 lands after the whole T20 chain).
- **Must keep passing unchanged:** the whole qwenloop suite, `(cd src/vibey_runners/qwen && uv run python -m pytest -q)`, at its 100% floor; and the protected root tests.
- **Registry (amendment A4):** nothing; `QwenConfig` is a value and the parser a pure policy.
- **Standing constraints (every qwenloop harness lane):**
  - This lane changes a runner tenant and runs that tenant's own gates (ADR-0022); qwenloop does not import vibey.
  - The tenant's in-memory fakes live in `src/vibey_runners/qwen/tests/fakes.py` (it exists; append to it, never recreate it). Tests import them with `from fakes import …`, as `tests/conftest.py:5` does.
  - Substitute only at a declared seam: a constructor or keyword argument, or a parameter with a production default. Never add `monkeypatch.setattr`, `mock.patch` or `MagicMock` (lane fakes-tenant-qwen-1 freezes the tenant's counts and only lowers them); `setenv` and `delenv` are allowed.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - No test needs a model server or waits longer than 5 s.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
