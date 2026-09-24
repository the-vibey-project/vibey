## Title
refactor(db): the job-ready LISTEN rides the family's engine — the one written driver-level exemption

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `LISTEN` is the one thing the ORM cannot
express: a notification arrives asynchronously on one session, whenever the server sends
it, and SQLAlchemy has no API for receiving it. `PostgresJobReadyNotifier`
(`src/vibey/infrastructure/db/notifier.py:16-51`) therefore talks to asyncpg directly — and
today it also *opens* its connection directly (`asyncpg.connect(self._dsn)`, `:23`), outside
any seam, and it has no contract beside it (the port is `JobReadyNotifier`,
`src/vibey/application/interfaces/queue.py:82-86`; nothing declares `connect`/`close`).

The exemption this lane writes down is narrow: the connection is opened through the
family's engine factory (`vibey_bootstrap.db.async_engine`, lane `orm-bootstrap-async-engine`;
sub-doctrine 10.e), and only the subscription itself — `add_listener`/`remove_listener` on
the driver connection SQLAlchemy hands back from `AsyncConnection.get_raw_connection()` —
is driver-level. The notifier sends no SQL at all. The constructor keeps taking a DSN, so
`rmq-r02-wakeup-composition` (which builds `PostgresJobReadyNotifier(dsn)` at call time) and
the CLI tests that patch this class (`tests/cli/test_operational_commands.py:1255`) are
unaffected.

## Required behaviour
1. `PostgresJobReadyNotifier.__init__(self, dsn: str, *, engines: AsyncEngineFactoryInterface = ASYNC_ENGINES)`.
2. `connect()`:
   - `self._engine = self._engines.create(self._dsn, poolclass=NullPool)` (`sqlalchemy.pool.NullPool`:
     this listener's one connection lives for the notifier's lifetime and is never pooled);
   - `self._conn = await self._engine.connect()`;
   - `raw = await self._conn.get_raw_connection()`;
     `self._listener: asyncpg.Connection = raw.driver_connection`;
   - `await self._listener.add_listener(_CHANNEL, self._on_notify)`.
3. `close()`: when connected, `remove_listener`, then `await self._conn.close()`, then
   `await self._engine.dispose()`, and reset all three attributes to `None`. A `close()`
   without `connect()` is still a no-op (`test_notifier.py:48-49`).
4. `_on_notify` and `wait_for_job_ready` are unchanged (`:32-51`).
5. The module docstring gains a paragraph titled **The driver-level exemption** saying:
   LISTEN is the only persistence access in vibey that is not SQLAlchemy Core or ORM; why
   (asynchronous, session-bound delivery with no SQLAlchemy API); that the connection still
   comes from the family's engine factory; that no SQL is sent; and that `import asyncpg`
   here names the driver connection's type and is the one import the `orm-raw-sql-guard`
   contract allows.
6. New contract in `src/vibey/infrastructure/interfaces/class_contracts.py`, exported from
   `src/vibey/infrastructure/interfaces/__init__.py`:
   ```python
   @runtime_checkable
   class PostgresJobReadyNotifierInterface(JobReadyNotifier, Protocol):
       """The LISTEN/NOTIFY wakeup (the one driver-level exemption, ADR-orm)."""

       async def connect(self) -> None: ...

       async def close(self) -> None: ...
   ```
   (`JobReadyNotifier` from `vibey.application.interfaces`, with the others there.)

## Where to change
- `src/vibey/infrastructure/db/notifier.py`
- `src/vibey/infrastructure/interfaces/class_contracts.py`, `src/vibey/infrastructure/interfaces/__init__.py`
- `tests/infrastructure/db/test_notifier.py` (append only; the five existing tests pass unchanged)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface` — this module is the written exception, and only for the
subscription; no `text()`, `exec_driver_sql()` or SQL strings; substitute at the declared
seam, never by patching an import; never edit a protected test; the first line of every new
file is the provenance comment copied byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg.connect\|execute(\|fetch" src/vibey/infrastructure/db/notifier.py` prints nothing.
- [ ] The five existing tests in `test_notifier.py` pass unchanged.
- [ ] A notifier built with a recording factory (a subclass of `AsyncEngineFactoryInterface` that records `(dsn, options)` and returns `ASYNC_ENGINES.create(dsn, **options)`) was asked for exactly one engine, with `poolclass=NullPool`.
- [ ] After `close()`, the notifier's connection, listener and engine attributes are `None`, a second `close()` is a no-op, and a `NOTIFY` sent afterwards wakes nothing.
- [ ] `isinstance(notifier, PostgresJobReadyNotifierInterface)` and `JobReadyNotifier`.
- [ ] `tests/cli/test_operational_commands.py` (the notifier patch at `:1255`) and `tests/system/test_full_worker_faked.py` pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_notifier.py` (integration):
- `test_the_listen_connection_comes_from_the_family_factory`
- `test_close_releases_the_connection_and_the_engine`
- `test_the_notifier_is_its_declared_contract`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_notifier.py tests/cli/test_operational_commands.py tests/system/test_full_worker_faked.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Where the worker builds its notifier (`rmq-r02-wakeup-composition`); the RabbitMQ wakeup
  (`rmq-r14`). The channel name and the 5-second poll fallback. Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
