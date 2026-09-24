## Title
feat(db): PostgresOrm is the one database seam — transactions, autocommit and sessions over the family's async engine

## Why
Every persistence access must go through the ORM behind a declared interface (ADR-0016;
sub-doctrine 9.b, `doctrines.md:349`; draft ADR `specs/ADR-orm.md`). The seam already
exists but only hands out ORM sessions and only its tests use it:
`src/vibey/infrastructure/db/orm.py:32-54` (`PostgresOrm`) and
`src/vibey/infrastructure/db/interfaces/orm_interface.py:13-28` (`PostgresOrmInterface`).
The repositories need three more ways in: one transaction (the queue's and the ledger's
atomic writes), a connection with no open transaction (the migrator, reads), and an
autocommit connection (session-level advisory locks, outbox relays). The seam also builds
its engine with its own URL helper (`orm.py:23-29`), a copy of what the family now ships
(`vibey_bootstrap.db.async_engine.AsyncEngineFactory`, lane `orm-bootstrap-async-engine`;
10.e says use the family's). And nothing refuses a non-PostgreSQL URL, although ADR-0002
forbids SQLite outright.

## Required behaviour
1. `PostgresOrm.__init__(self, engine: AsyncEngine) -> None` takes a built engine and keeps
   today's `async_sessionmaker(engine, expire_on_commit=False)`.
2. `@classmethod PostgresOrm.from_dsn(cls, dsn: str, *, echo: bool = False, pool_size: int = 10,
   max_overflow: int = 0, engines: AsyncEngineFactoryInterface = ASYNC_ENGINES) -> PostgresOrm`:
   - `url = engines.url(dsn)`; unless `url.startswith("postgresql+asyncpg://")`, raise
     `UnsupportedDatabaseUrl(dsn)`.
   - otherwise `return cls(engines.create(dsn, echo=echo, pool_size=pool_size, max_overflow=max_overflow))`.
   - `pool_size=10, max_overflow=0` are today's ceiling (`bootstrap.py:700`, `max_size=10`),
     kept as defaults, so nothing becomes less configurable (12.c).
3. `class UnsupportedDatabaseUrl(VibeyError)` (`vibey.domain.errors.VibeyError`), in `orm.py`.
   Its message names ADR-0002 and only the URL's scheme (`dsn.split("://", 1)[0]`) — never
   the rest, which can carry a password. It keeps the scheme on `self.scheme`.
4. Three new async context managers on `PostgresOrm`, each declared on the interface:
   - `connect()` yields `AsyncConnection` from `engine.connect()`: no transaction is open
     when it is yielded (`in_transaction()` is `False`). Whatever the caller did not commit
     is rolled back at exit.
   - `transaction()` yields the `AsyncConnection` of `engine.begin()`: commit on a clean
     exit, rollback when the body raises.
   - `autocommit()` yields `await conn.execution_options(isolation_level="AUTOCOMMIT")` for a
     connection from `engine.connect()`: every statement commits on its own, the way a bare
     asyncpg connection behaves today.
5. `engine`, `session()` and `dispose()` are unchanged.
6. The private `_asyncpg_url` function is deleted. The module docstring (`orm.py:2-8`) is
   rewritten: this seam is the one way vibey reaches PostgreSQL; the repositories move onto
   it lane by lane (the old text says the queue and ledger keep driver-level SQL).
7. `UnsupportedDatabaseUrlInterface` (a Protocol with a `scheme: str` property) is declared
   in `orm_interface.py`, and `PostgresOrmInterface` declares `connect`, `transaction`,
   `autocommit` with the same docstring style as `session`. Both are exported from
   `vibey/infrastructure/db/interfaces/__init__.py`.

## Where to change
- `src/vibey/infrastructure/db/orm.py`
- `src/vibey/infrastructure/db/interfaces/orm_interface.py` (runtime imports stay under
  `TYPE_CHECKING`: `AsyncConnection`, `AsyncEngine`, `AsyncSession`)
- `src/vibey/infrastructure/db/interfaces/__init__.py` (export the new Protocol)
- `tests/infrastructure/db/test_orm.py`: two edits only —
  - drop `_asyncpg_url` from the import on line 11 and change the parametrized
    `test_postgres_dsn_is_normalized_for_asyncpg` (`:38-47`) to assert
    `ASYNC_ENGINES.url(dsn) == expected` (`from vibey_bootstrap.db.async_engine import ASYNC_ENGINES`);
  - `PostgresOrm(database_url)` (`:65`) becomes `PostgresOrm.from_dsn(database_url)`.
- New `tests/infrastructure/orm/__init__.py` (empty but for the provenance line) and
  `tests/infrastructure/orm/test_orm_seam.py` (no database).
- New `tests/infrastructure/db/test_orm_seam_database.py` (integration).
Nothing else constructs `PostgresOrm` today (`grep -rn "PostgresOrm(" src tests`).

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `PostgresOrm.from_dsn("sqlite:///x")` and `PostgresOrm.from_dsn("mysql://u:secret@h/db")` raise `UnsupportedDatabaseUrl`; the second message does not contain `secret`, and both mention `ADR-0002`.
- [ ] `from_dsn` builds through the injected factory with `echo=False, pool_size=10, max_overflow=0` unless told otherwise.
- [ ] Against PostgreSQL: a row inserted in `transaction()` is visible afterwards; one inserted before an exception is not; one inserted in `autocommit()` before an exception is; `connect()` yields a connection with no transaction open.
- [ ] `test_orm.py` passes with its two edits; `mypy --strict src/vibey` is clean.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_orm_seam.py` (no database):
- `test_a_url_that_is_not_postgres_is_refused` (parametrize `sqlite:///x`, `mysql://u@h/db`)
- `test_the_refusal_never_repeats_the_password`
- `test_from_dsn_builds_through_the_injected_factory` — a recording subclass of
  `AsyncEngineFactoryInterface` whose `create` returns
  `create_async_engine("postgresql+asyncpg://u@h/db")` (builds, never connects); assert the
  recorded options and that `orm.engine` is what it returned.
- `test_the_seam_and_its_error_are_declared` (`isinstance` against both Protocols)

`tests/infrastructure/db/test_orm_seam_database.py` (integration; use the `migrated_pool`
fixture to get a migrated database and `database_url` to build `PostgresOrm.from_dsn`; write
with `insert(ProjectOrm).values(name=..., repo_path=..., config={})`; dispose in `finally`):
- `test_transaction_commits_on_a_clean_exit`
- `test_transaction_rolls_back_when_the_body_raises`
- `test_autocommit_commits_each_statement_on_its_own`
- `test_connect_yields_a_connection_with_no_transaction_open`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_orm.py tests/infrastructure/db/test_orm_seam_database.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_orm_seam.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Any repository, `bootstrap.py` (lane `orm-app-resources`), the test fixtures
  (`orm-test-harness`), typed table access and JSON decoding (`orm-tables`).
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
