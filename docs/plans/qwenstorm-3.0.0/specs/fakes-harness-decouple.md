## Title
test(harness): the default test run needs no PostgreSQL; only the integration tier builds a database

## Why
The operator's standard: "these fakes run in memory so that no outside thing is ever needed in
order to run tests". Draft ADR-0045 amendment (`specs/ADR-test-harness-fakes-amendment.md`,
section A1) makes it the rule that a plain `pytest` with nothing running passes.

Today no root test can start without PostgreSQL:
- `tests/conftest.py:146-156` (`pytest_configure`) runs `asyncio.run(_setup(...))`, which calls
  `asyncpg.connect` (`:86`, `:99`) for **every** session, even `pytest tests/domain`.
- The `integration` marker (`pyproject.toml:264`) exists but no command deselects it
  (`addopts`, `:262`, only excludes `paid`).
- `tests/infrastructure/db/conftest.py:17-19` and `tests/contracts/conftest.py:19-21` add the
  marker in `pytest_collection_modifyitems`. That hook is session-wide: a conftest's
  implementation receives **every** collected item, not only its own directory's. In a
  whole-suite run every test is marked `integration`, so `-m "not integration"` would
  deselect the whole suite.
- Some tests open the database and carry no marker:
  `tests/cli/test_forward_compatibility_columns.py` (`build_app()` at `:17` and `:34`),
  `tests/tui/test_dashboard.py::test_fetch_dashboard_state_from_db` (`:151`),
  `tests/system/test_full_worker_faked.py` (only `pytest.mark.system`, `:35`).

## Required behaviour
1. **`tests/conftest.py`** gains `class WorkerDatabase`. Move `_resolve_base_dsn`,
   `_replace_dbname`, `_worker_id`, `_worker_db_name`, `_setup` and `_teardown` into it as
   methods, with their SQL and comments unchanged. It has:
   - `setup(self) -> None`: does exactly what `pytest_configure` does today (sets
     `_VIBEY_TEST_BASE_DSN`, `VIBEY_TEST_DATABASE_URL` and `VIBEY_PG_URL`) and records that it
     ran;
   - `teardown(self) -> None`: runs `_teardown` only when `setup` ran, inside
     `contextlib.suppress(Exception)` as today.
   A module constant `WORKER_DATABASE = WorkerDatabase()` holds the one instance.
2. **`pytest_configure`** no longer connects to anything. The Hypothesis profile
   registration stays where it is.
3. **New hook `pytest_collection_finish(session)`** calls `WORKER_DATABASE.setup()` only when
   `any(item.get_closest_marker("integration") is not None for item in session.items)`.
   `pytest_unconfigure` calls `WORKER_DATABASE.teardown()`. Keep the three hooks as module
   functions, each with this comment: `# Module-level: pytest resolves conftest hooks by name
   at module scope (as src/vibey_tools/gh/test/conftest.py:32-33 says).`
4. **The two directory markers are scoped to their directory.** In
   `tests/infrastructure/db/conftest.py` and `tests/contracts/conftest.py`, add
   `_HERE = Path(__file__).resolve().parent` and only mark items with
   `item.path.resolve().is_relative_to(_HERE)`.
5. **Every test that opens the database carries `integration`:**
   - `tests/cli/test_forward_compatibility_columns.py`: `pytestmark = pytest.mark.integration`;
   - `tests/system/test_full_worker_faked.py`: `pytestmark = [pytest.mark.system, pytest.mark.integration]`;
   - `tests/tui/test_dashboard.py`: `@pytest.mark.integration` on `test_fetch_dashboard_state_from_db` only;
   - any other test that fails in acceptance item 1 with `DatabaseNotConfigured`,
     `ConnectionRefusedError`, `OSError` from asyncpg, or `KeyError: 'VIBEY_TEST_DATABASE_URL'`.
     Mark it (module `pytestmark` when every test in the module needs it, else per test), and
     list each one in the commit body.
6. **The marker's description** in `pyproject.toml` becomes:
   `"integration: needs a real outside service (PostgreSQL via VIBEY_TEST_DATABASE_URL, or a broker, model server, Docker, network); the opt-in tier"`.
7. **Nothing else changes.** `addopts` still runs integration by default, and CI and the
   pre-push hooks are untouched. `fakes-ci-no-services` flips the default later.

## Where to change
- `tests/conftest.py` (whole file, 162 lines; use `edit_file`, not `write_file`).
- `tests/infrastructure/db/conftest.py:17-19`, `tests/contracts/conftest.py:19-21`.
- The three modules in behaviour 5, plus any the acceptance run finds.
- `pyproject.toml:264` (one string).

## Acceptance criteria
- [ ] With nothing listening on port 1, this passes:
      `VIBEY_TEST_DATABASE_URL=postgresql://nobody@127.0.0.1:1/none env -u VIBEY_PG_URL uv run pytest -q -p no:cacheprovider -m "not integration and not paid"`.
- [ ] With PostgreSQL available, the whole suite passes as before, and
      `uv run pytest --collect-only -q -p no:cacheprovider | tail -1` reports the same count
      as before the change.
- [ ] `uv run pytest --collect-only -q -m "not integration" tests/domain tests/infrastructure/db`
      collects the domain tests and none of the db tests.
- [ ] The new meta tests pass.

## Tests to write first (TDD)
`tests/meta/test_integration_tier.py`:
- `test_directory_markers_stay_in_their_directory`: in a subprocess,
  `[sys.executable, "-m", "pytest", "--collect-only", "-q", "-p", "no:cacheprovider", "-n", "0", "-m", "not integration", "tests/domain", "tests/infrastructure/db"]`
  with `VIBEY_TEST_DATABASE_URL=postgresql://nobody@127.0.0.1:1/none`. It asserts that the
  exit code is 0, that the output names `tests/domain/`, and that it does not name
  `tests/infrastructure/db/`.
- `test_the_default_tier_starts_with_nothing_running`: in a subprocess,
  `-m "not integration and not paid" -n 0 tests/domain/test_domain_purity.py` with the same
  unreachable URL and `VIBEY_PG_URL` removed. Exit 0.
- `test_every_module_that_opens_the_database_is_marked`: an AST walk of `tests/**/*.py`,
  excluding `conftest.py`, `tests/live/**` and `tests/meta/**`. A module whose source contains
  `asyncpg.connect(`, `asyncpg.create_pool(`, `build_app(` or `VIBEY_TEST_DATABASE_URL` must
  meet one of these:
  - it has a module `pytestmark` that names `integration`;
  - it lies under `tests/infrastructure/db/` or `tests/contracts/`;
  - it is a key of `PER_TEST_MODULES`, a dict in the test file mapping the path to a one-line
    reason. Seed it with `tests/tui/test_dashboard.py`, `tests/cli/test_ledger_publication_cli.py`,
    `tests/infrastructure/test_sovereign_surfaces.py` (it replaces the pool) and
    `tests/test_bootstrap.py` (port 1, and a replaced pool).

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run pytest -q -p no:cacheprovider tests/meta/test_integration_tier.py
    VIBEY_TEST_DATABASE_URL=postgresql://nobody@127.0.0.1:1/none env -u VIBEY_PG_URL uv run pytest -q -p no:cacheprovider -m "not integration and not paid"
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    git diff --stat HEAD~1 -- tests/domain/test_noloss*.py tests/domain/test_briefing.py tests/infrastructure/db/test_chaos.py tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Changing `addopts`, CI or `.pre-commit-config.yaml` (`fakes-ci-no-services`).
- Writing fakes. Tests that need the database stay integration tests; later lanes move them.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Do not push. Commit locally with the Title as the subject.

## Lane card
- **Depends on:** none. Land it first.
- **Files touched:** `tests/conftest.py`, `tests/infrastructure/db/conftest.py`,
  `tests/contracts/conftest.py`, `tests/cli/test_forward_compatibility_columns.py`,
  `tests/system/test_full_worker_faked.py`, `tests/tui/test_dashboard.py`, `pyproject.toml`,
  `tests/meta/test_integration_tier.py` (new).
- **Shares a file with:** `pyproject.toml` (R03, T07, T28: this lane changes one marker string);
  `tests/conftest.py` (T09 reads it; see amendment A6).
- **Must keep passing unchanged:** the protected tests, the whole suite with PostgreSQL.
- **Standing constraints:** protected tests are never edited
  (`tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`,
  `tests/live/**`). Line 1 of every new file is the provenance line, copied byte-for-byte
  from a sibling.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
