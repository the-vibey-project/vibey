## Title
refactor(db): the migrator runs on an AsyncConnection — Core for its bookkeeping, the driver only for the checksummed files

## Why
Migrations stay what they are: forward-only, checksummed, hand-written `.sql` files applied
under an advisory lock (`src/vibey/infrastructure/db/migrator.py:1-18`; draft ADR
`specs/ADR-orm.md` — no `create_all`, no Alembic autogenerate). What moves is the code
around them. Every caller already goes through `apply_url` (lane `orm-migrator-callers`),
which today hands `apply` the raw asyncpg connection. This lane makes `apply` take the
`AsyncConnection` itself and writes every statement the migrator composes as SQLAlchemy
Core: the lock bound (`:228-231`), the lock (`:232`), the unlock (`:220`), the lock-holder
lookup (`:115-124`, `:234`), the applied-set read (`:252`) and the bookkeeping insert
(`:267-271`).

One thing cannot be Core, and this lane writes the reason down: a migration file is a
multi-statement script (`CREATE TYPE …; CREATE TABLE …; DO $$ … $$;`). SQLAlchemy's asyncpg
dialect prepares every statement it executes (`sqlalchemy/dialects/postgresql/asyncpg.py`,
`_prepare_and_execute`), and PostgreSQL refuses to prepare more than one command. A script
needs the simple-query protocol, which only the driver connection offers. So the migrator
runs the checksummed file text — and the `CREATE TABLE IF NOT EXISTS schema_migration`
bootstrap DDL (`:103-109`) — through
`(await conn.get_raw_connection()).driver_connection.execute(sql)`, inside the
`AsyncConnection`'s own transaction. That is the second and last written exemption (the
first is LISTEN, lane `orm-notifier`), and `orm-raw-sql-guard` pins it.

## Required behaviour
1. `import asyncpg` and the `OwnedConnection` alias are removed from `migrator.py` and from
   `interfaces/migrator_interface.py`; `apply(self, conn: AsyncConnection, migrations, *, check_only=False)`.
2. `apply`: `if conn.in_transaction(): raise MigrationInsideTransaction()`; `await self._acquire(conn)`;
   `try: return await self._apply_locked(...)`; `finally:` release inside its own
   `async with conn.begin(): await conn.execute(select(func.pg_advisory_unlock(literal(self.LOCK_KEY, BigInteger()))))`.
   Every advisory key is bound as `BigInteger`: a bare Python `int` binds as `$n::INTEGER`,
   and `LOCK_KEY` is a 64-bit value.
3. `_acquire`:
   ```python
   try:
       async with conn.begin():
           await conn.execute(select(func.set_config("lock_timeout", f"{self._lock_timeout_ms}ms", True)))
           await conn.execute(select(func.pg_advisory_lock(literal(self.LOCK_KEY, BigInteger()))))
   except DBAPIError as exc:
       if getattr(exc.orig, "sqlstate", None) != "55P03":  # lock_not_available
           raise
       async with conn.begin():
           holders = (await conn.execute(self._holders())).scalars().all()
       raise MigrationLockTimeout(self.LOCK_KEY, self._lock_timeout_seconds, tuple(holders)) from exc
   ```
   (`DBAPIError` from `sqlalchemy.exc`; SQLAlchemy's asyncpg dialect puts the SQLSTATE on
   `exc.orig.sqlstate`.)
4. `_holders(self)` builds today's `_LOCK_HOLDERS` query in Core over lightweight
   `sqlalchemy.table`/`column` constructs for `pg_locks` (`pid`, `locktype`, `database`,
   `objsubid`, `granted`, `classid`, `objid`) and `pg_database` (`oid`, `datname`):
   `locktype == "advisory"`, `database == select(pg_database.c.oid).where(pg_database.c.datname == func.current_database()).scalar_subquery()`,
   `objsubid == 1`, `granted.is_(True)`, and
   `cast(classid, BigInteger).op("<<")(32).op("|")(cast(objid, BigInteger)) == literal(self.LOCK_KEY, BigInteger())`,
   ordered by `pid`. `_LOCK_HOLDERS` (the string) is deleted; keep its comment on the method.
5. `_apply_locked`:
   - `await self._run_script(conn, _ENSURE_SCHEMA_MIGRATION_TABLE)` (outside any
     `begin()`: the statement is idempotent and runs under the lock);
   - the applied set in `async with conn.begin():` through
     `select(MIGRATIONS.c["version"], MIGRATIONS.c["checksum"])`, with
     `MIGRATIONS = TABLES.table("schema_migration")` (lane `orm-tables`);
   - each pending migration in **one** `async with conn.begin():` that first executes
     `insert(MIGRATIONS).values(version=…, checksum=…)` (this starts the transaction on the
     driver connection) and then `await self._run_script(conn, migration.sql)` — so the file
     and its bookkeeping row commit together or not at all.
6. `_run_script(self, conn: AsyncConnection, sql: str) -> None` (docstring: the exemption
   above, in three sentences): `raw = await conn.get_raw_connection()`;
   `driver = cast(Any, raw.driver_connection)`; `await driver.execute(sql)`.
7. `apply_url` hands `conn` itself to `apply` (drop the `get_raw_connection` line and its
   transitional comment).
8. Errors, the lock key, the timeout arithmetic and every message are unchanged. A failing
   migration file still raises the driver's own error (e.g.
   `asyncpg.exceptions.UndefinedTableError`), because the script runs on the driver.

## Where to change
- `src/vibey/infrastructure/db/migrator.py`
- `src/vibey/infrastructure/db/interfaces/migrator_interface.py`
- `tests/infrastructure/db/test_migrator.py`, only:
  - add a fixture beside `other_conn`:
    ```python
    @pytest_asyncio.fixture
    async def other_sa_conn(pg_conn: asyncpg.Connection, database_url: str) -> AsyncIterator[AsyncConnection]:
        """A second session, as the migrator now takes it: another pod."""
        engine = ASYNC_ENGINES.create(database_url, poolclass=NullPool)
        try:
            async with engine.connect() as conn:
                yield conn
        finally:
            await engine.dispose()
    ```
  - in `test_a_second_start_waits_for_the_first_then_finds_the_schema_settled` and
    `test_a_wedged_holder_fails_the_waiter_loudly_and_names_it`, use `other_sa_conn` in place
    of `other_conn`: read the pid with
    `waiter_pid = await other_sa_conn.scalar(select(func.pg_backend_pid()))` followed by
    `await other_sa_conn.rollback()` (so no transaction is open when the migrator starts);
    call `PostgresMigrator(...).apply(other_sa_conn, migrations)`; in the wedged test assert
    `other_sa_conn.in_transaction() is False` and
    `await other_sa_conn.scalar(select(func.current_setting("lock_timeout"))) == "0"`.
  - `test_migrations_do_not_run_under_the_lock_wait_bound`:
    `.apply(pg_conn, discover_migrations(tmp_path))` → `.apply_url(_test_dsn(), discover_migrations(tmp_path))`.
  - `test_a_connection_inside_a_transaction_is_refused`: open the transaction on
    `other_sa_conn` (`async with other_sa_conn.begin():`) and call
    `PostgresMigrator().apply(other_sa_conn, …)` inside it; the rest is unchanged.
  No other existing test changes.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface` or the family's engine factory; no `import asyncpg`, `text()` or
`exec_driver_sql()` in `src/`; the only SQL strings allowed are the checksummed migration
files and the one bootstrap DDL constant, and only through `_run_script`; substitute at the
declared seam, never by patching an import; never edit a protected test; the first line of
every new file is the provenance comment copied byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg\|fetchval\|\.fetch(\|conn.transaction()" src/vibey/infrastructure/db/migrator.py` prints nothing.
- [ ] `grep -n "driver_connection" src/vibey/infrastructure/db/migrator.py` shows only `_run_script`.
- [ ] Every test in `test_migrator.py` passes: fresh apply, twice is a no-op, seeded data survives, the checksum guard (also in check-only mode), the race applies each migration once, the waiter queues before touching anything, the wedged holder is named, the lock is released after success and after failure, migrations do not inherit the lock bound, a connection inside a transaction is refused, and the partition migration keeps the ledger append-only.
- [ ] A migration file that fails leaves neither its effects nor its `schema_migration` row.
- [ ] The whole `tests/infrastructure/db` and `tests/contracts` suites pass; `build_app` migrates.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_migrator.py` (integration):
- `test_a_failed_file_leaves_no_bookkeeping_row` (`0001_ok.sql` then `0002_half.sql` =
  `CREATE TABLE half (id int); SELECT * FROM no_such_table;` → the second raises; `half`
  does not exist and `schema_migration` holds only `0001_ok`)
- `test_the_holder_lookup_names_the_backend_holding_the_lock` (take the key on `pg_conn`
  with `SELECT pg_advisory_lock($1)`; execute `PostgresMigrator()._holders()` on
  `other_sa_conn`; the result is exactly `[pg_conn's backend pid]`; unlock in `finally`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier; a fresh template proves the harness migrates through the new path):
    VIBEY_TEST_TEMPLATE_DB=vibey_test_template_orm2 uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/contracts tests/test_bootstrap.py tests/infrastructure/test_cluster_preflight.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The migration files (never edit an applied one: the checksum guard exists for that).
- `vibey doctor --cluster` (`orm-cluster-preflight`). Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
