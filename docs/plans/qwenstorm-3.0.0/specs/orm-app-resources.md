## Title
feat(bootstrap): build_app hands out the ORM seam, and nothing reaches into a repository's pool

## Why
Every repository lane of the ORM wave (draft ADR `specs/ADR-orm.md`) switches one
repository's construction in `build_app` from the asyncpg pool to the ORM seam
(`PostgresOrmInterface`, lane `orm-database-seam`). For that, `build_app`
(`src/vibey/bootstrap.py:694-954`) must build the seam once, beside today's pool, and hand
it out. And today five places reach past a repository into its private pool, which would
break the moment that repository stops holding one:
- `src/vibey/cli/main.py:634`, `:728`, `:810`, `:884` —
  `PostgresEngineHealthRepository(resources.ledger._pool)`, although `AppResources` already
  carries that very repository as `engine_health_repo` (`bootstrap.py:148`, built `:721`);
- `src/vibey/cli/ledger_search.py:200` — `PostgresLedgerSearchRepository(resources.ledger._pool)`;
- and, in tests, `resources.ledger._pool` (`tests/tui/test_dashboard.py:184`,
  `tests/cli/test_operational_commands.py:56`, `:122`, `:166`, `:438`,
  `tests/cli/test_ledger_search_cli.py:216`) and `resources.projects._pool`
  (`tests/cli/test_forward_compatibility_columns.py:21`, `:38`).
Sub-doctrine 9.b (`doctrines.md:349`): reach a capability through its declared seam, never
around it.

## Required behaviour
1. In `build_app`, resolve the DSN once: `dsn = url or database_url()` before the pool is
   created, and use `dsn` for `asyncpg.create_pool(...)` (`:700`).
2. Directly after the `if pool is None` check, build `orm = PostgresOrm.from_dsn(dsn)` (before
   the `try:`). In the `finally` (`:953-954`), `await orm.dispose()` after `await pool.close()`.
3. `AppResources` (`:134-171`) gains two required fields, placed before
   `integration_lock` (which has a default): `orm: PostgresOrm` and
   `ledger_search: PostgresLedgerSearchRepository`. The yield (`:916`) passes `orm=orm` and
   `ledger_search=PostgresLedgerSearchRepository(pool)` (the search repository still takes the
   pool; lane `orm-ledger-search` switches it).
4. `AppResourcesInterface` (`src/vibey/bootstrap_interface.py:23`) gains
   `@property def orm(self) -> object: ...` and
   `@property def ledger_search(self) -> LedgerSearch: ...` (import `LedgerSearch` from
   `vibey.application.interfaces`, as the file already imports that package).
5. The four `PostgresEngineHealthRepository(resources.ledger._pool)` lines in `cli/main.py`
   become `resources.engine_health_repo`; each now-unused local
   `from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository`
   (`:603`, `:715`, `:798`, `:839`) is removed (ruff F401 will say which).
6. `cli/ledger_search.py:198-200` uses `searcher: LedgerSearch = resources.ledger_search`; the
   comment above it is updated to say the search repository is the one `build_app` built,
   and the import at `:47` is removed if unused.
7. The test reach-ins change as follows, and nothing else in those tests changes:
   - `PostgresEngineHealthRepository(resources.ledger._pool)` → `resources.engine_health_repo`
     (`test_dashboard.py:184`, `test_operational_commands.py:56`, `:122`, `:166`); drop an
     import that becomes unused.
   - `async with build_app() as resources, resources.ledger._pool.acquire() as conn:` (and the
     same with `resources.projects._pool`) → a raw asyncpg connection to the same database,
     the pattern these files already use at `test_operational_commands.py:41`:
     `conn = await asyncpg.connect(database_url())` … `finally: await conn.close()`. Where the
     `build_app()` block existed only to reach the pool, drop it; where it also creates data
     (`test_forward_compatibility_columns.py:16-26`, `:32-45`), keep it and open the raw
     connection inside it. Tests may use asyncpg directly; production code may not.
8. Behaviour is otherwise unchanged: same migrations, same version floor, same repositories.

## Where to change
- `src/vibey/bootstrap.py` (`AppResources`, `build_app`); import `PostgresOrm` from
  `vibey.infrastructure.db.orm` and `PostgresLedgerSearchRepository` from
  `vibey.infrastructure.db.ledger_search_repository`.
- `src/vibey/bootstrap_interface.py`
- `src/vibey/cli/main.py` (the four lines and their imports only)
- `src/vibey/cli/ledger_search.py` (`:47`, `:198-200`)
- `tests/tui/test_dashboard.py`, `tests/cli/test_operational_commands.py`,
  `tests/cli/test_ledger_search_cli.py`, `tests/cli/test_forward_compatibility_columns.py`
  (the reach-ins only)
- `tests/test_bootstrap.py` (new tests appended)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -rn "\._pool" src/vibey tests | grep -v "self\._pool"` prints nothing.
- [ ] Inside `build_app()`, `isinstance(resources.orm, PostgresOrmInterface)` and `isinstance(resources.ledger_search, LedgerSearch)`, and `select(1)` runs through `resources.orm.connect()`.
- [ ] `tests/test_bootstrap.py::test_build_app_rejects_a_postgres_server_below_the_support_floor` and the two `build_app` tests in `tests/infrastructure/test_sovereign_surfaces.py` pass unchanged (building the engine never connects).
- [ ] `vibey status`, `vibey ledger search` and the dashboard tests pass.
- [ ] 100% branch coverage of `src/vibey/cli/` and `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/test_bootstrap.py`:
- `test_build_app_hands_out_the_orm_seam` (integration: `async with build_app() as resources:`
  `isinstance(resources.orm, PostgresOrmInterface)`; `select(1)` through `resources.orm.connect()`)
- `test_build_app_hands_out_the_ledger_search_it_built` (`isinstance(resources.ledger_search, LedgerSearch)`)
- `test_app_resources_still_satisfy_their_interface` (`isinstance(resources, AppResourcesInterface)`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (these build the app against the per-worker database):
    uv run pytest -q -p no:cacheprovider tests/test_bootstrap.py tests/cli/test_operational_commands.py tests/cli/test_ledger_search_cli.py tests/cli/test_forward_compatibility_columns.py tests/tui/test_dashboard.py tests/infrastructure/test_sovereign_surfaces.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Switching any repository to the seam (each repository lane), removing the pool
  (`orm-bootstrap-engine`), the `recover` command (`orm-cli-recover`).
- `rmq-r02-wakeup-composition` and `rmq-r17-queue-backend-selection` also edit
  `AppResources`; if either has landed, keep its fields and add these two beside them.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
