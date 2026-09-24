## Title
refactor(db): migrations are applied by URL through the family's engine, so no caller hands the migrator an asyncpg connection

## Why
The migrator (`src/vibey/infrastructure/db/migrator.py`) is the last persistence code the
ORM wave converts (draft ADR `specs/ADR-orm.md`), and five callers hand it a raw asyncpg
connection they opened themselves: `build_app` (`src/vibey/bootstrap.py:704-709`), the
façade `apply_migrations` (`migrator.py:277-290`) and, through it, the test harness's
template database (`tests/conftest.py:98-106`), the db fixtures
(`tests/infrastructure/db/conftest.py`, `migrated_pool`) and the contract fixtures
(`tests/contracts/conftest.py:41-48`), plus most of `tests/infrastructure/db/test_migrator.py`.
This lane moves every caller onto one entry point that takes a **URL** and opens its own
connection through the family's engine factory (`vibey_bootstrap.db.async_engine`, lane
`orm-bootstrap-async-engine`; sub-doctrine 10.e). The migrator's own statements stay as they
are in this lane; `orm-migrator` converts them next, behind the same entry point, without
touching the callers again. Splitting it this way keeps both lanes small and green.

## Required behaviour
1. `PostgresMigrator.__init__(self, *, lock_timeout_seconds: float = DEFAULT_LOCK_TIMEOUT_SECONDS, engines: AsyncEngineFactoryInterface = ASYNC_ENGINES)`;
   `from_environ` is unchanged (it builds with the default factory).
2. New `async def apply_url(self, dsn: str, migrations: tuple[Migration, ...], *, check_only: bool = False) -> tuple[str, ...]`:
   ```python
   engine = self._engines.create(dsn, poolclass=NullPool)
   try:
       async with engine.connect() as conn:
           raw = await conn.get_raw_connection()
           return await self.apply(raw.driver_connection, migrations, check_only=check_only)
   finally:
       await engine.dispose()
   ```
   (`NullPool` from `sqlalchemy.pool`: one migration run, one connection, never pooled.)
   The comment above it says the driver connection is handed to `apply` only until
   `orm-migrator` converts `apply` to an `AsyncConnection`.
3. The façade becomes `async def apply_migrations(dsn: str, migrations, *, check_only=False)`
   returning `await PostgresMigrator().apply_url(dsn, migrations, check_only=check_only)`.
   Its docstring says the test harness migrates by URL.
4. `MigratorInterface` (`src/vibey/infrastructure/db/interfaces/migrator_interface.py`)
   declares `apply_url` beside `apply`.
5. `build_app`: `dsn = url or database_url()` is computed once (lane `orm-app-resources`
   already did this; reuse it). The version check still runs on the pool connection, but
   `await migrator.apply(conn, ...)` (`:709`) is removed from that block, and **after** the
   `async with pool.acquire()` block: `await migrator.apply_url(dsn, discover_migrations(migrations_dir()))`.
6. Callers in tests:
   - `tests/conftest.py:98-106`: delete `tmpl_conn` and its `try/finally`; call
     `await apply_migrations(_replace_dbname(base_dsn, _TEMPLATE_DB), migrations)`.
   - `tests/infrastructure/db/conftest.py` (`migrated_pool`): replace the
     `async with pg_pool.acquire() as conn: … apply_migrations(conn, migrations)` block with
     `await apply_migrations(database_url, discover_migrations(MIGRATIONS_DIR))`.
   - `tests/contracts/conftest.py` (`migrated_pool`): keep the schema reset inside
     `async with pool.acquire() as conn:`, move the migration after that block as
     `await apply_migrations(database_url, discover_migrations(MIGRATIONS_DIR))`.
   - `tests/infrastructure/test_sovereign_surfaces.py:633` and `:682`:
     `migrator.apply = AsyncMock()` → `migrator.apply_url = AsyncMock()`.
   - `tests/infrastructure/db/test_migrator.py`: add, after the imports,
     ```python
     def _test_dsn() -> str:
         """The URL the `database_url` fixture returns, for calls outside a fixture."""
         return os.environ.get(
             "VIBEY_TEST_DATABASE_URL",
             f"postgresql://{getpass.getuser()}@localhost:5432/vibey_test",
         )
     ```
     (import `os` and `getpass`), then apply exactly these replacements with a checked script:
     `apply_migrations(pg_conn,` → `apply_migrations(_test_dsn(),` and
     `apply_migrations(other_conn,` → `apply_migrations(_test_dsn(),`.
     The tests that call `PostgresMigrator(...).apply(other_conn, …)` or `.apply(pg_conn, …)`
     are **not** touched: `apply` still takes an asyncpg connection in this lane.
7. Nothing about migrating changes: same lock, same checksums, same order, same errors.

## Where to change
- `src/vibey/infrastructure/db/migrator.py` (`__init__`, `apply_url`, the façade)
- `src/vibey/infrastructure/db/interfaces/migrator_interface.py`
- `src/vibey/bootstrap.py` (`build_app`'s migration call)
- `tests/conftest.py`, `tests/infrastructure/db/conftest.py`, `tests/contracts/conftest.py`,
  `tests/infrastructure/test_sovereign_surfaces.py`, `tests/infrastructure/db/test_migrator.py`
  (only as listed above), `tests/test_bootstrap.py` (new tests appended)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface` or the family's engine factory; no new `import asyncpg`, `text()`,
`exec_driver_sql()` or SQL strings in `src/`; substitute at the declared seam, never by
patching an import; never edit a protected test; the first line of every new file is the
provenance comment copied byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -rn "apply_migrations(" tests src | grep -v "_test_dsn()\|database_url\|_replace_dbname\|def apply_migrations"` prints nothing.
- [ ] Every test in `test_migrator.py` passes (the lock, race, wedge and checksum tests included).
- [ ] `build_app` still migrates a fresh database, and still fails the start on a bad `VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS` before touching the database (`tests/test_bootstrap.py:66-76` unchanged).
- [ ] A migrator built with a recording factory asks it for exactly one engine per `apply_url`, with `poolclass=NullPool`, and disposes it (also when a migration fails).
- [ ] The whole `tests/infrastructure/db` and `tests/contracts` suites pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_migrator.py` (integration):
- `test_apply_url_opens_one_unpooled_connection_through_the_factory`
- `test_apply_url_disposes_its_engine_when_a_migration_fails` (a factory subclass whose
  engine records `dispose`; a `0001_broken.sql` of `SELECT * FROM no_such_table;`)
Append to `tests/test_bootstrap.py`:
- `test_build_app_migrates_by_url` (integration: after `build_app()`, `schema_migration`
  holds every file in `migrations_dir()`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier; the root conftest re-creates the template through the new path):
    VIBEY_TEST_TEMPLATE_DB=vibey_test_template_orm uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/contracts tests/test_bootstrap.py tests/infrastructure/test_sovereign_surfaces.py tests/infrastructure/test_cluster_preflight.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
The `VIBEY_TEST_TEMPLATE_DB` override makes the root conftest build a fresh template
through the new code path instead of reusing an existing one (`tests/conftest.py:44-47`).

## Out of scope
- Converting `apply`, `_acquire` and `_apply_locked` to SQLAlchemy (`orm-migrator`).
- `vibey doctor --cluster`'s migration check (`orm-cluster-preflight`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
