## Title
refactor(doctor): the cluster preflight's database checks become a DatabaseCheck class over the family's engine

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `vibey doctor --cluster`'s two database
checks are bare module functions over raw asyncpg (`src/vibey/infrastructure/cluster_preflight.py:244-286`:
`check_database` opens `asyncpg.connect(dsn)` and runs `SHOW server_version_num`;
`check_migrations` runs `SELECT version FROM schema_migration`). Their tests reach them by
patching the import (`tests/infrastructure/test_cluster_preflight.py:287`, `:309`, `:333`:
`monkeypatch.setattr("vibey.infrastructure.cluster_preflight.asyncpg.connect", …)`), which
9.b forbids: substitution happens at the declared seam. This lane gives the checks a class
and an interface, builds the connection through the family's engine factory
(`vibey_bootstrap.db.async_engine`; sub-doctrine 10.e), and lets the tests substitute the
factory instead of patching an import. The verdicts and their wording do not change.

## Required behaviour
1. New `class DatabaseCheck` in `cluster_preflight.py`:
   - `__init__(self, *, engines: AsyncEngineFactoryInterface = ASYNC_ENGINES)`.
   - `async def run(self, dsn: str, migrations_dir: Path) -> tuple[ClusterCheck, ...]`:
     ```python
     engine = self._engines.create(dsn, poolclass=NullPool)
     try:
         try:
             conn = await engine.connect()
         except Exception as exc:  # see the comment below
             return (ClusterCheck("database", False, f"cannot connect: {exc}"),)
         try:
             return await self._checks(conn, migrations_dir)
         finally:
             await conn.close()
     finally:
         await engine.dispose()
     ```
     The comment on the broad `except` says: a preflight reports every failure to connect —
     refused, unresolvable, bad password, unknown database — as a failed check; SQLAlchemy
     does not wrap the driver's connect errors, and the driver is not imported here.
   - `_checks(conn, migrations_dir)`:
     - `raw = await conn.scalar(select(func.current_setting("server_version_num")))`; a
       `SQLAlchemyError` returns only `(ClusterCheck("database", False, f"version check failed: {exc}"),)`
       — no migration verdict, as today (`:250-253`).
     - otherwise the `database` verdict exactly as `:254-268` (unreadable, below the floor,
       or `f"PostgreSQL {version}; connected"`), **followed by** the migrations verdict — today
       an unreadable or unsupported server still gets its migrations checked, and it still does.
   - `_migrations(conn, migrations_dir) -> ClusterCheck`: exactly `:271-286`, with the read as
     `(await conn.execute(select(MIGRATIONS.c["version"]))).scalars().all()`
     (`MIGRATIONS = TABLES.table("schema_migration")`, lane `orm-tables`) and
     `except SQLAlchemyError` in place of `asyncpg.PostgresError`.
   - `DATABASE_CHECK: Final[DatabaseCheckInterface] = DatabaseCheck()`.
2. `ClusterPreflight.__init__(self, *, engine_auth, database: DatabaseCheckInterface = DATABASE_CHECK)`;
   in `run`, lines `:315-321` become `checks.extend(await self._database.run(dsn, migrations_dir))`.
3. `check_database` and `check_migrations` are deleted, and so is `import asyncpg`.
4. `DatabaseCheckInterface` (method `run`) is declared in
   `src/vibey/infrastructure/interfaces/cluster_preflight_interface.py` and exported from
   `src/vibey/infrastructure/interfaces/__init__.py`.
5. `ClusterPreflight`'s output — names, order, wording — is unchanged
   (`test_full_preflight_against_a_live_database` and
   `test_preflight_skips_the_migration_check_when_the_database_is_unreachable` pass unchanged).

## Where to change
- `src/vibey/infrastructure/cluster_preflight.py`
- `src/vibey/infrastructure/interfaces/cluster_preflight_interface.py`, `src/vibey/infrastructure/interfaces/__init__.py`
- `tests/infrastructure/test_cluster_preflight.py`: remove `check_database` and
  `check_migrations` from the import block (`:17-28`), then delete the nine tests that call
  them with this checked script, and run `uv run ruff check --fix` on the file:
  ```python
  from pathlib import Path
  p = Path("tests/infrastructure/test_cluster_preflight.py")
  s = p.read_text()
  a = s.index("async def test_database_check_connects_and_hands_back_the_connection")
  b = s.index("async def test_full_preflight_against_a_live_database")
  p.write_text(s[:a] + s[b:])
  ```
- New `tests/infrastructure/test_database_check.py` (below), which replaces them.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface` or the family's engine factory; no `import asyncpg`, `text()`,
`exec_driver_sql()` or SQL strings in `src/`; substitute at the declared seam, never by
patching an import; never edit a protected test; the first line of every new file is the
provenance comment copied byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg" src/vibey/infrastructure/cluster_preflight.py` and `grep -rn "monkeypatch.setattr(\"vibey.infrastructure.cluster_preflight" tests` print nothing.
- [ ] Every verdict the nine removed tests pinned is pinned again in `test_database_check.py`: connected; unreachable host (`cannot connect`); unsupported server (`below`, migrations still checked); unreadable version (`unreadable`, migrations still checked); version query failure (`version check failed`, no migrations verdict, connection closed, engine disposed); migrations applied; a pending version named; no migration files; `schema_migration` unreadable.
- [ ] `vibey doctor --cluster`'s CLI tests pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/` and `src/vibey/cli/`.

## Tests to write first (TDD)
`tests/infrastructure/test_database_check.py`. The no-database tests substitute the engine
factory — a subclass of `vibey_bootstrap.db.interfaces.AsyncEngineFactoryInterface` whose
`create` records its options and returns a small fake engine (`async connect()` returning a
fake connection or raising; `async dispose()` recording itself); the fake connection has
`async scalar(stmt)`, `async execute(stmt)` returning an object with `.scalars().all()`,
and `async close()`. Raise `sqlalchemy.exc.ProgrammingError("stmt", {}, Exception("boom"))`
where a query must fail.
- `test_an_unreachable_host_cannot_connect` (real: `_DEAD_DSN = "postgresql://nobody@127.0.0.1:1/nothing"`)
- `test_an_unsupported_server_is_below_the_floor_and_still_checks_migrations` (fake: `"130023"`)
- `test_an_unreadable_version_is_reported_and_still_checks_migrations` (fake: `"unknown"`)
- `test_a_failed_version_query_reports_only_the_database_and_cleans_up` (fake; asserts `close` and `dispose` ran)
- `test_the_engine_is_unpooled` (the recorded options include `poolclass=NullPool`)
- `test_migrations_without_any_files_fail` (fake; `tmp_path` with no `.sql`)
- `test_an_unreadable_schema_migration_fails` (fake; `execute` raises)
- `test_applied_migrations_pass_after_bootstrap` (integration: `async with build_app(url=dsn): pass`, then `DatabaseCheck().run(dsn, migrations_dir())` → both ok)
- `test_a_version_the_database_has_not_seen_is_named` (integration; copy the migration files to `tmp_path` and add `9999_from_a_newer_image.sql`)
- `test_the_check_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/test_cluster_preflight.py tests/infrastructure/test_database_check.py tests/cli
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100
    uv run coverage report --include='src/vibey/cli/*' --fail-under=100

## Out of scope
- The other preflight checks (DSN host, non-root, workspace, engine auth) and the CLI
  wiring (`src/vibey/cli/main.py:1370` keeps constructing `ClusterPreflight(engine_auth=…)`).
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
