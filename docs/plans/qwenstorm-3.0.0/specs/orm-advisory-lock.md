## Title
refactor(db): the integration advisory lock holds an ORM-seam connection and gets its declared contract

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `PostgresAdvisoryLock`
(`src/vibey/infrastructure/db/advisory_lock.py:28-54`) implements `IntegrationLock`
(`src/vibey/application/interfaces/build.py:84-95`; ADR-0029) with two raw asyncpg calls
(`pg_try_advisory_lock` `:40-42`, `pg_advisory_unlock` `:53`), pins a pooled connection by
hand (`:39`, `:44`, `:54`), and has no contract in
`src/vibey/infrastructure/interfaces/class_contracts.py`. The semantics that must not move
are in its docstring (`:2-12`): the lock is session-level, so the connection that took it is
held out of the pool until release; `try_acquire` never blocks; a second acquire through the
same instance is contention, not re-entry.

## Required behaviour
1. `PostgresAdvisoryLock.__init__(self, orm: PostgresOrmInterface)`; `self._held: dict[tuple[UUID, int], tuple[AsyncExitStack, AsyncConnection]]`.
2. `try_acquire(project_id, cycle)`:
   - key already held → `False` (unchanged).
   - `stack = AsyncExitStack()`; `conn = await stack.enter_async_context(self._orm.autocommit())`.
     An autocommit connection holds the session lock without an open transaction, so it is
     never "idle in transaction" while a worker integrates.
   - `acquired = await conn.scalar(select(func.pg_try_advisory_lock(literal(lock_key(project_id, cycle), BigInteger()))))`.
     The key must be bound as `BigInteger`: SQLAlchemy's asyncpg dialect binds a bare Python
     `int` as `$n::INTEGER`, and a 64-bit key does not fit in `int4`.
   - not acquired → `await stack.aclose()`; `False`. Acquired → keep `(stack, conn)`; `True`.
3. `release(project_id, cycle)`: pop; nothing held → return (unchanged). Otherwise
   `await conn.scalar(select(func.pg_advisory_unlock(literal(lock_key(project_id, cycle), BigInteger()))))`, then
   `await stack.aclose()` in a `finally`, so the connection goes back even if the unlock raises.
4. `lock_key` (`:21-25`) is unchanged (ADR-0029 pins its derivation).
5. The module docstring's second paragraph says the held connection is an ORM-seam
   autocommit connection kept open by an `AsyncExitStack`.
6. New contract in `class_contracts.py`, exported from `src/vibey/infrastructure/interfaces/__init__.py`:
   ```python
   @runtime_checkable
   class PostgresAdvisoryLockInterface(IntegrationLock, Protocol):
       """The Postgres session-advisory-lock implementation of the integration lock (ADR-0029)."""
   ```
   (`IntegrationLock` is imported from `vibey.application.interfaces` with the others there.)
7. `build_app` passes `integration_lock=PostgresAdvisoryLock(orm)` (`src/vibey/bootstrap.py:951`).

## Where to change
- `src/vibey/infrastructure/db/advisory_lock.py`
- `src/vibey/infrastructure/interfaces/class_contracts.py`, `src/vibey/infrastructure/interfaces/__init__.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_advisory_lock.py` (append only; the four existing tests pass unchanged)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg\|fetchval\|release(conn" src/vibey/infrastructure/db/advisory_lock.py` prints nothing.
- [ ] While held, `pg_locks` shows one granted advisory lock with the key; after `release`, none.
- [ ] After `release`, the engine has no checked-out connection (`migrated_pool.engine.pool.checkedout() == 0`).
- [ ] A lost race (`try_acquire` returns `False`) also returns its connection.
- [ ] `isinstance(PostgresAdvisoryLock(migrated_pool), PostgresAdvisoryLockInterface)` and `IntegrationLock`.
- [ ] `tests/infrastructure/db/test_build_implement_end_to_end.py` and every `build.integrate` test pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_advisory_lock.py` (integration; query `pg_locks`
through `await migrated_pool.fetchval(...)`, which the fixture still passes to asyncpg):
- `test_a_held_lock_is_visible_in_pg_locks_until_release`
- `test_release_hands_the_connection_back`
- `test_a_lost_race_hands_the_connection_back`
- `test_the_lock_is_its_declared_contract`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_advisory_lock.py tests/infrastructure/db/test_build_implement_end_to_end.py
    # No-services tests that must stay green:
    uv run pytest -q -p no:cacheprovider tests/application
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `lock_key`'s derivation, the migration lock (`orm-migrator`), the integrate handler.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
