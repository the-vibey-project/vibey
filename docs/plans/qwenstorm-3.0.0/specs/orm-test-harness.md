## Title
test(db): the migrated-database fixture is both an asyncpg pool and the ORM seam, and a FakeOrm substitutes at the seam

## Why
The ORM wave moves one repository at a time from an `asyncpg.Pool` to
`PostgresOrmInterface` (lane `orm-database-seam`; draft ADR `specs/ADR-orm.md`). Two things
in the test tree would otherwise block every one of those lanes:

1. **The protected chaos test.** `tests/infrastructure/db/test_chaos.py:53` builds
   `PostgresJobRepository(migrated_pool)` and uses `migrated_pool.acquire()` for raw checks
   (`:103`, `:153`). It is protected (`.vibey-gh.toml:71-78`) and is never edited. When the
   job repository takes the ORM seam, `migrated_pool` must still be something both calls
   accept. The same holds for the 25 other test files that construct repositories from
   `migrated_pool` or call `.acquire()`/`.fetch()` on it
   (`grep -rln "migrated_pool" tests | wc -l`).
2. **The null-pool unit tests.** Six tests reach a defensive branch by handing a repository
   a fake asyncpg pool (`test_job_repository.py:329-359`, `test_ledger_repository.py:174-207`,
   `test_project_repository.py:232-249`, `test_engine_health_repository.py:172-189`, and the
   `None` pools at `test_forward_compatibility_columns.py:110,141`). Once a repository takes
   the ORM seam, those need a double of the seam. Sub-doctrine 9.b (`doctrines.md:349`)
   says substitution happens at the declared seam, never by patching an import — so the
   double must satisfy `PostgresOrmInterface`, not patch `sqlalchemy`.

## Required behaviour
1. `tests/infrastructure/db/migrated_database.py` (new) defines
   `class MigratedDatabase(PostgresOrm)`:
   - `__init__(self, pool: asyncpg.Pool, engine: AsyncEngine)` → `super().__init__(engine)`,
     keeps `pool` as `self._asyncpg_pool`.
   - Pool passthroughs, each a one-line delegation: `acquire(*args, **kwargs)` (returns the
     pool's own acquire context, so both `async with db.acquire()` and `await db.acquire()`
     work), `async release(conn)`, `async fetch(*args)`, `async fetchrow(*args)`,
     `async fetchval(*args)`, `async execute(*args)`.
   - `async close()` closes the pool, then `await self.dispose()`.
   - Docstring: test-only; it lets repositories that already take the ORM seam and
     repositories and assertions that still use an asyncpg pool share one migrated database
     while the wave moves one repository at a time; production code never sees it.
2. `tests/infrastructure/db/conftest.py`: `migrated_pool` becomes a yield fixture that
   migrates exactly as today (`:62-67`), then builds
   `engine = ASYNC_ENGINES.create(database_url, pool_size=5, max_overflow=5)` (from
   `vibey_bootstrap.db.async_engine`), yields `MigratedDatabase(pg_pool, engine)`, and
   `await engine.dispose()` in `finally`. The fixture keeps its name. Its annotation becomes
   `AsyncIterator[MigratedDatabase]`. `pg_pool`, `pg_conn`, `project_id` are unchanged.
3. `tests/contracts/conftest.py`: `migrated_pool` (`:41-54`) yields
   `MigratedDatabase(pool, engine)` the same way (engine built after the migration, disposed
   in `finally` after `pool.close()`).
4. `tests/infrastructure/orm/fakes.py` (new) defines the seam double, for unit tests that
   need no database:
   - `class FakeResult`: `__init__(self, rows: Sequence[Mapping[str, object]] = (), *, rowcount: int | None = None, scalar: object = None)`;
     `mappings()` returns `self`; `first()` → first row or `None`; `one()` → the only row or
     `AssertionError`; `all()` → list of rows; `scalar()` → `scalar`; `rowcount` attribute
     (defaults to `len(rows)`).
   - `class FakeConnection`: `__init__(self, results: Iterable[FakeResult])`;
     `async execute(statement, parameters=None)` appends `statement` to `self.statements` and
     pops the next scripted result (a fresh empty `FakeResult` once the script runs out);
     `async scalar(statement, parameters=None)` is `(await self.execute(...)).scalar()`;
     `in_transaction()` → `False`; `async commit()` / `async rollback()` record themselves.
   - `class FakeOrm`: `__init__(self, *results: FakeResult)` builds one `FakeConnection`
     (`self.connection`); `connect()`, `transaction()`, `autocommit()` are
     `asynccontextmanager`s yielding it; `session()` raises `NotImplementedError` inside its
     context manager body (only when entered); `engine` returns a sentinel `object()`
     (never raises: `isinstance` against a runtime-checkable Protocol reads it);
     `async dispose()` sets `self.disposed = True`.
5. No existing test file other than the two conftests changes.

## Where to change
- `tests/infrastructure/db/migrated_database.py` (new)
- `tests/infrastructure/db/conftest.py`
- `tests/contracts/conftest.py`
- `tests/infrastructure/orm/fakes.py` (new; create `tests/infrastructure/orm/__init__.py`
  with only the provenance line if it does not exist yet)
- `tests/infrastructure/orm/test_fakes.py` (new) and
  `tests/infrastructure/db/test_migrated_database.py` (new)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `isinstance(migrated_pool, PostgresOrmInterface)` inside a db test, and `async with migrated_pool.acquire() as conn: await conn.fetchval("SELECT 1")` still works.
- [ ] `async with migrated_pool.transaction() as conn: (await conn.execute(select(1))).scalar() == 1`.
- [ ] `isinstance(FakeOrm(), PostgresOrmInterface)`; scripted results come back in order; statements are recorded.
- [ ] The whole `tests/infrastructure/db` and `tests/contracts` suites pass unchanged, including `test_chaos.py` (protected; `git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py` is empty).

## Tests to write first (TDD)
- `tests/infrastructure/db/test_migrated_database.py` (integration):
  - `test_the_fixture_is_the_orm_seam`
  - `test_the_fixture_is_still_an_asyncpg_pool`
  - `test_both_ways_in_see_the_same_database` (insert a project through `transaction()` with
    `insert(ProjectOrm)`; read it back through `acquire()`)
- `tests/infrastructure/orm/test_fakes.py` (no database):
  - `test_the_fake_is_the_orm_seam`
  - `test_scripted_results_come_back_in_order_then_empty`
  - `test_statements_are_recorded`
  - `test_a_session_is_refused_only_when_opened`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier): every db and contract test, chaos included
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db tests/contracts
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_fakes.py
    git diff --stat HEAD -- tests/infrastructure/db/test_chaos.py tests/domain tests/system/test_delivery_stage_set.py tests/live

## Out of scope
- Any file under `src/`. Any repository. The six null-pool tests (each repository lane
  rewrites its own with `FakeOrm`).
- Docs, CHANGELOG. Do not push. Commit locally with the Title (`test(db): …`).

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
