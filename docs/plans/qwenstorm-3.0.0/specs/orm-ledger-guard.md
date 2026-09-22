## Title
feat(db): the ORM seam refuses an UPDATE or DELETE of the ledger loudly

## Why
The ledger is append-only (CLAUDE.md non-negotiable). The database enforces it with two
rules that turn an UPDATE or DELETE of `event` into nothing
(`migrations/0013_ledger_partitioning.sql:65-66`, `CREATE RULE … DO INSTEAD NOTHING`), and
`tests/infrastructure/db/test_ledger_repository.py:125-154` pins that such a statement is a
*silent* no-op. Once persistence goes through the ORM (draft ADR `specs/ADR-orm.md`), a
mistaken `update(EventOrm)` or a dirty `EventOrm` in a session would reach that rule and
report success while writing nothing — and the ORM's own "rows matched" check would turn
it into a confusing `StaleDataError`, if anything. The seam should refuse the attempt in
Python, before it reaches the database, and name the rule it broke. The database rules stay
as the backstop for anything that bypasses the seam.

## Required behaviour
1. `class AppendOnlyViolation(VibeyError)` in `src/vibey/infrastructure/db/append_only_guard.py`,
   carrying `table: str`; message: `f"{table!r} is append-only: vibey never updates or deletes a ledger row (corrections are new events)"`.
2. `class AppendOnlyGuard` in the same module:
   - `__init__(self, tables: frozenset[str] = frozenset({"event"}))`.
   - `install(self, engine: AsyncEngine) -> None`: registers `self._refuse` for the
     `"before_execute"` event on `engine.sync_engine` with `sqlalchemy.event.listen`, unless
     `sqlalchemy.event.contains(engine.sync_engine, "before_execute", self._refuse)` is
     already true (installing twice registers once).
   - `_refuse(self, conn, clauseelement, multiparams, params, execution_options) -> None`:
     when `clauseelement` is a `sqlalchemy.sql.dml.Update` or `Delete` whose `.table.name`
     is in `tables`, raise `AppendOnlyViolation(name)`. Anything else passes untouched
     (`INSERT`, `SELECT`, `SELECT append_event(...)`, updates of other tables).
   - Module-level `APPEND_ONLY: Final[AppendOnlyGuardInterface] = AppendOnlyGuard()`.
3. `PostgresOrm.__init__(self, engine: AsyncEngine, *, guard: AppendOnlyGuardInterface = APPEND_ONLY)`
   calls `guard.install(engine)`. `from_dsn` passes nothing new (the default applies).
4. Interfaces `AppendOnlyGuardInterface` (method `install`) and `AppendOnlyViolationInterface`
   (property `table`) in `src/vibey/infrastructure/db/interfaces/append_only_guard_interface.py`,
   exported from `interfaces/__init__.py`.
5. The two existing silent-no-op tests keep passing unchanged: they send raw SQL through an
   asyncpg connection, which is exactly the path the database rule still covers.

## Where to change
- `src/vibey/infrastructure/db/append_only_guard.py` (new)
- `src/vibey/infrastructure/db/interfaces/append_only_guard_interface.py` (new)
- `src/vibey/infrastructure/db/interfaces/__init__.py`
- `src/vibey/infrastructure/db/orm.py` (`__init__` only)
- `tests/infrastructure/db/test_append_only_guard.py` (new, integration)
- `tests/infrastructure/orm/test_append_only_guard_unit.py` (new, no database)
Use `before_execute`, not `before_cursor_execute`: it receives the statement object, it
fires for Core statements and for the ORM's flush alike, and a raise there is not wrapped.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] Through `PostgresOrm`, `update(event).values(kind="x")` and `delete(event)` raise `AppendOnlyViolation` and the row is unchanged.
- [ ] An ORM session that changes a loaded `EventOrm` and commits raises `AppendOnlyViolation`.
- [ ] `update` of `project` through the same seam works.
- [ ] Appending through `SELECT append_event(...)` is untouched.
- [ ] `test_update_event_is_a_silent_no_op` and `test_delete_event_is_a_silent_no_op` pass unchanged.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_append_only_guard_unit.py` (no database; an engine built with
`create_async_engine("postgresql+asyncpg://u@h/db")` never connects):
- `test_installing_twice_registers_one_listener` (`event.contains` is true after one and after two installs; no error)
- `test_the_guard_and_its_error_are_declared`
- `test_the_violation_names_the_table_and_the_rule`

`tests/infrastructure/db/test_append_only_guard.py` (integration; seed one event through
the raw pool: `await migrated_pool.fetchval("SELECT append_event($1, 1, 'intake', 'TurnRequested', NULL, NULL, NULL, $1, 'agent', now(), '{}'::jsonb, 'd')", project_id)`;
the `migrated_pool` fixture is itself a `PostgresOrm` once `orm-test-harness` has landed):
- `test_a_core_update_of_the_ledger_is_refused`
- `test_a_core_delete_of_the_ledger_is_refused`
- `test_an_orm_session_cannot_rewrite_an_event` (`await session.get(EventOrm, (project_id, 1))`, change `kind`, commit → raises)
- `test_other_tables_update_normally`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_append_only_guard.py tests/infrastructure/db/test_ledger_repository.py tests/infrastructure/db/test_orm.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_append_only_guard_unit.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The ledger repository itself (`orm-ledger`). The migrations and their rules.
- Docs, CHANGELOG. Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
