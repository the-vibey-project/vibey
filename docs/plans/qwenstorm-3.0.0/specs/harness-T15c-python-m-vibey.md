## Title
feat(cli): python -m vibey runs the CLI, and vibey test is registered

## Why
Draft ADR-0045 §13 spawns the `local` backend's detached supervisor as
`sys.executable -m vibey test-harness execute …` (harness-T14, T15a), so that the supervisor runs
in the requester's own interpreter and **no console script is added**: ADR-0037 ships one
distribution, and the image contract "every console script is on PATH"
(`.github/workflows/ci.yml:817-822`) lists exactly the twelve in `pyproject.toml:69-81`. That
needs a `vibey/__main__.py`, whose module-level call is the one place a module function is
required by the language (9.b: "permitted only where a language or library contract requires
one, and its reason is written at the definition").

This lane also registers harness-T15b's `test` group with the `vibey` app.

## Required behaviour
1. **New `src/vibey/__main__.py`**: line 1 the provenance line; then the docstring
   `"""The entry `python -m vibey`. It needs a module-level call; the test harness's supervisor is spawned this way so that no console script is added (ADR-0037, ADR-0045 §13)."""`;
   then exactly
   ```python
   from vibey.cli.main import app

   if __name__ == "__main__":
       app(prog_name="vibey")
   ```
2. **`src/vibey/cli/main.py`**: add `from vibey.cli.test_harness import test_app` to the
   `vibey.cli.*` imports (`:36-38`), and `app.add_typer(test_app, name="test")` after the ledger
   registrations (`:86-90`). Change nothing else. `SIGTERM_LATCH.arm()` stays the statement at
   `:9`, before these imports (its E402 placement is deliberate).

## Where to change
- New `src/vibey/__main__.py`.
- `src/vibey/cli/main.py` (two added lines, with `edit_file`; the file is over 1500 lines).
- New `tests/cli/test_python_m_vibey.py`.

## Acceptance criteria
- [ ] `python -m vibey --version` prints `vibey <version>` and exits 0.
- [ ] `python -m vibey test --help` exits 0 and lists `run`.
- [ ] `uv run python -c "import tomllib; print(len(tomllib.load(open('pyproject.toml', 'rb'))['project']['scripts']))"` still prints `12`: no console script is added.
- [ ] 100% coverage of `src/vibey/cli/` (`__main__.py` is outside the per-layer globs, and its call only runs as `__main__`).

## Tests to write first (TDD)
`tests/cli/test_python_m_vibey.py`, module-level test functions (the reason
`tests/meta/test_githooks_reach_the_framework.py:30-33` gives: pytest collects `test_*` functions,
and the class rule is about production code). Each runs a subprocess of `sys.executable` with an
environment copied from `os.environ` minus `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE`:
- `test_python_m_vibey_prints_the_version`
- `test_python_m_vibey_lists_the_test_group` (`["-m", "vibey", "test", "--help"]`; stdout contains `run`)
- `test_the_test_group_is_registered_on_the_app` (in process: `CliRunner().invoke(main.app, ["test", "--help"])` exits 0)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The `test-harness` group (harness-T15). Any console script.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push, open a pull request or change remotes. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** harness-T15b-test-run-command.
- **Files touched:** `src/vibey/__main__.py` (new), `src/vibey/cli/main.py` (two lines), `tests/cli/test_python_m_vibey.py` (new).
- **Shares a file with:** `src/vibey/cli/main.py` (rmq-r02, rmq-r17, rmq-r27, rmq-r28, rmq-r33 and fakes-cli-composition edit other parts; harness-T15 adds one more registration).
- **Must keep passing unchanged:** `tests/cli/*`, the image contract "every console script is on PATH", and the protected tests.
- **Registry (amendment A4):** nothing; no seam is declared.
- **Standing constraints (every harness lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte for byte from line 1 of a sibling file:
    `# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).`
  - Never `monkeypatch.setattr`, `mock.patch` or `MagicMock`.
  - Default-tier tests need nothing outside the process (ADR-0045 amendment A1; lane fakes-isolation-guard's audit hook fails a default-tier test that reaches out); children of `sys.executable` are inside.
  - Every child environment drops `VIBEY_HARNESS_RUN` and `VIBEY_HARNESS_ROUTE`.
  - Edit existing files with `edit_file`, never rewrite a test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
