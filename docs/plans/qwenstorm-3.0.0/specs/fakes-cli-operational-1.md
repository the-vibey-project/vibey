## Title
test(cli): the status, engines, cost, ledger and watch command tests run on the in-memory app

## Why
`tests/cli/test_operational_commands.py` is 2,313 lines and 124 tests, all `integration`
(`pytestmark`, `:22`). The autouse fixture `_use_test_database` (`:33-46`) connects to
PostgreSQL and drops `public` before **every** test, including those that only check
`--help` output.

By now:
- every collaborator the commands reach is a declared seam (`fakes-job-wakeup`, `fakes-cli-composition`);
- `tests/fakes/app.py` provides `InMemoryApp`, which runs the real `build_app` composition over
  fakes (`fakes-bootstrap-seam`).

This lane moves the **first 40 tests** (`:92` `test_status_command_text_and_json` through
`:602` `test_work_once_unknown_project`) into a new default-tier module. Lanes 2 and 3 move
the rest, and lane 3 deletes the old file.

## Required behaviour
1. **`tests/cli/ops_support.py`** (new; a support module, not a test module) holds:
   - a `memory_app` fixture: a fresh `InMemoryApp()` per test;
   - `invoke(app: InMemoryApp, *args, **kw) -> Result`, which calls
     `CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"}).invoke(vibey.cli.main.app, list(args), obj=app.composition(**kw))`.
     `kw` forwards extra `CliComposition` fields, such as `postgres_local=...`;
   - the seed helpers, rewritten over `async with app.open_app() as resources:`:
     `seed_status_project`, `seed_engines_project`, `seed_cost_project` and
     `seed_ledger_project` (from `:48`, `:114`, `:155`, `:257`), plus
     `seed_ledger_project_with_a_newer_kind` (`:436`). Where the old helper built
     `PostgresEngineHealthRepository(resources.ledger._pool)`, use `resources.engine_health_repo`.
     Where it inserted raw SQL, use the port method. The helper that writes an event of a kind
     this vibey does not know appends it through `InMemoryLedger` directly, because the port
     refuses unknown kinds, as the real writer does.
   Import it from test modules with `from tests.cli import ops_support as ops`.
2. **`tests/cli/test_ops_status_ledger.py`** (new) holds the first 40 tests. They are moved,
   not rewritten: the same names, the same asserted output and exit codes. Only the setup
   and the invocation change:
   - no `_use_test_database`;
   - no `pytestmark = integration`;
   - `ops.invoke(memory_app, ...)` in place of `runner.invoke(app, ...)`;
   - the fake collaborators from `tests/fakes/cli.py` in place of any composition built in the test.
   If a moved test's expected output depended on something only PostgreSQL produced, stop and
   report it. It stays in the old file, marked `integration`, with the reason. An example is
   an error message text from asyncpg.
3. **Delete the moved tests** from `test_operational_commands.py`, one checked block at a time
   (`EDITING-RULES.md` rule 2). Keep every helper that the remaining tests still use.
4. Lower the old file's baseline entry. The new module must count zero.

## Where to change
- New `tests/cli/ops_support.py`, `tests/cli/test_ops_status_ledger.py`.
- `tests/cli/test_operational_commands.py` (deletions), `tests/meta/patching_baseline.json`.

## Acceptance criteria
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_ops_status_ledger.py` passes with PostgreSQL stopped, and reports 40 tests, or 40 minus the reported exceptions.
- [ ] The total collected in `tests/cli` is unchanged (`--collect-only -q | tail -1`, before and after).
- [ ] 100% `cli/` coverage from the full run.

## Tests to write first (TDD)
- Move one test and make it pass, then the next. There are no new behaviours.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/cli/test_ops_status_ledger.py tests/meta
    uv run pytest -q -p no:cacheprovider tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- Tests 41–124 (lanes 2 and 3). Production code.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** `fakes-cli-composition`.
- **Files touched:** see *Where to change*.
- **Must keep passing unchanged:** every test left in `test_operational_commands.py`, and the protected tests.
- **Standing constraints (every fakes lane):**
  - Protected tests are never edited: `tests/domain/test_noloss*.py`,
    `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`,
    `tests/system/test_delivery_stage_set.py` and `tests/live/**`.
  - Line 1 of every new file is the provenance line, copied byte-for-byte from a sibling file.
  - A fake is a plain class with real in-memory behaviour for every method of its port.
    `unittest.mock` is never used under `tests/fakes/`. No method body is only `...`, only
    `pass`, only `return None`, or only `raise NotImplementedError`.
  - Substitute at a declared seam: a constructor or keyword argument, or
    `CliRunner.invoke(..., obj=...)`. Never use `monkeypatch.setattr`, `mock.patch` or
    `MagicMock` (sub-doctrine 9.b). `monkeypatch.setenv`, `delenv` and `chdir` stay allowed.
  - Once `fakes-registry` has landed, register every fake you add in `tests/fakes/registry.py`
    and delete its `PENDING` entry. Lower each converted file's numbers in
    `tests/meta/patching_baseline.json` to what the ratchet now counts, and never raise one.
  - A test that needs a real service is marked `integration`, and skips when its
    `VIBEY_TEST_*` variable is unset.
  - Change existing files with `edit_file` or a checked replacement, and never rewrite an
    existing test file (`EDITING-RULES.md`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
