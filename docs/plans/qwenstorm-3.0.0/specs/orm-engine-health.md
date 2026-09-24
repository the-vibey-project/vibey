## Title
refactor(db): engine health upserts through the ORM seam, and the credits CHECK surfaces as IntegrityError

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `PostgresEngineHealthRepository`
(`src/vibey/infrastructure/db/engine_health_repository.py:60-144`) is three raw asyncpg
statements: `get` (`:67-74`), the upsert (`:88-136`), `list_for_project` (`:138-144`).
The upsert is where the non-negotiable "Credits ≠ rate limit" meets the database: the
third of its three independent layers is the CHECK constraint
`credits_never_have_a_deadline` (`migrations/0007_engine_health_rotation.sql:20-22`). Through
the ORM a violated CHECK arrives as `sqlalchemy.exc.IntegrityError` (the driver's
`CheckViolationError` is on `.orig`, SQLSTATE `23514`), not as the asyncpg exception the
current test pins (`tests/infrastructure/db/test_engine_health_repository.py:112-128`).
That test changes its expected exception type, and **nothing** else about the rule changes.

## Required behaviour
1. `EngineHealthRowMapper.to_record(self, row: Mapping[str, Any])`: the same mapping
   (`:35-53`); the interface (`interfaces/engine_health_repository_interface.py:23`) takes
   `Mapping[str, Any]` and drops its `asyncpg` import.
2. `PostgresEngineHealthRepository.__init__(self, orm: PostgresOrmInterface, *, rows=HEALTH_ROWS)`.
3. With `HEALTH = TABLES.table("engine_health")` (lane `orm-tables`):
   - `get`: in `self._orm.connect()`,
     `select(HEALTH).where(HEALTH.c["project_id"] == project_id, HEALTH.c["engine_id"] == engine_id)`.
   - `upsert`: the two refusals (`:77-87`) stay first and unchanged. Then, in
     `self._orm.transaction()`:
     ```python
     stmt = pg_insert(HEALTH).values(
         project_id=record.project_id, engine_id=engine_id.value, installed=record.installed,
         version=record.version, conformance_ok=record.conformance_ok,
         conformance_at=record.conformance_at, auth_ok_at=record.auth_ok_at,
         circuit=str(record.circuit), capacity_state=record.capacity_state,
         resets_at=record.resets_at, probe_next_at=record.probe_next_at,
         probe_attempt=record.probe_attempt, consecutive_fail=record.consecutive_fail,
         ewma_failure=record.ewma_failure, cost_usd_cycle=record.cost_usd_cycle,
         selected_count=record.selected_count,
     )
     stmt = stmt.on_conflict_do_update(
         index_elements=[HEALTH.c["project_id"], HEALTH.c["engine_id"]],
         set_={name: stmt.excluded[name] for name in _UPSERTED},
     ).returning(*HEALTH.c)
     ```
     where `_UPSERTED` is a class-level tuple of the fourteen column names today's
     `DO UPDATE SET` lists (`:101-114`), in that order. `pg_insert` is
     `sqlalchemy.dialects.postgresql.insert`. `None` from `.mappings().first()` raises today's
     `LookupError(f"upsert: no row returned for engine_health {record.engine_id}")`.
   - `list_for_project`: `select(HEALTH).where(HEALTH.c["project_id"] == project_id).order_by(HEALTH.c["engine_id"])`.
4. A CHECK violation propagates as `sqlalchemy.exc.IntegrityError`; the repository neither
   catches nor translates it.
5. `build_app` builds `engine_health_repo = PostgresEngineHealthRepository(orm)`
   (`src/vibey/bootstrap.py:721`).

## Where to change
- `src/vibey/infrastructure/db/engine_health_repository.py`
- `src/vibey/infrastructure/db/interfaces/engine_health_repository_interface.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_engine_health_repository.py`, two existing tests only:
  - `test_credits_exhausted_with_a_resets_at_violates_the_db_check_constraint` (`:112-128`):
    `pytest.raises(asyncpg.exceptions.CheckViolationError)` becomes
    `pytest.raises(sqlalchemy.exc.IntegrityError) as caught`, followed by
    `assert caught.value.orig.sqlstate == "23514"` and
    `assert "credits_never_have_a_deadline" in str(caught.value)`. Its docstring stays.
  - `test_upsert_raises_lookup_error_when_fetchrow_returns_none` (`:172-189`): delete its
    fake classes; `repo = PostgresEngineHealthRepository(FakeOrm(FakeResult()))` (from
    `tests/infrastructure/orm/fakes.py`); keep the `pytest.raises`.
  - append the new tests below.
- New `tests/infrastructure/orm/test_engine_health_row_mapper.py` (no database).
`tests/infrastructure/db/test_forward_compatibility_columns.py:136-186` constructs the
repository with `None` and must pass unchanged: both refusals happen before the seam is used.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg" src/vibey/infrastructure/db/engine_health_repository.py src/vibey/infrastructure/db/interfaces/engine_health_repository_interface.py` prints nothing.
- [ ] Writing `capacity_state="CreditsExhausted"` with a `resets_at` raises `IntegrityError` with SQLSTATE `23514` naming `credits_never_have_a_deadline`, and leaves no row.
- [ ] `WindowExhausted` with a `resets_at`, and `CreditsExhausted` without one, are stored (`:94-110`, `:131-141` unchanged).
- [ ] `tests/infrastructure/db/test_end_to_end_forced_rotation.py`, `tests/cli/test_operational_commands.py` and `tests/tui/test_dashboard.py` pass.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_engine_health_repository.py` (integration):
- `test_a_refused_credits_deadline_leaves_no_row` (after the `IntegrityError`, `get` returns `None`)
- `test_the_upsert_overwrites_every_listed_column` (write, then write again changing all
  fourteen columns; `get` returns the second record field for field)
`tests/infrastructure/orm/test_engine_health_row_mapper.py` (no database):
- `test_a_known_engine_id_maps_to_its_member`
- `test_an_unknown_engine_id_maps_to_unrecognized` (`"future-engine"` → `UnrecognizedEngineId`)
- `test_cost_is_a_float_even_from_a_decimal` (`Decimal("1.2500")` → `1.25`)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_engine_health_repository.py tests/infrastructure/db/test_forward_compatibility_columns.py tests/infrastructure/db/test_end_to_end_forced_rotation.py tests/cli/test_operational_commands.py tests/tui/test_dashboard.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_engine_health_row_mapper.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The migration and the CHECK itself; the domain type and the property test (the other
  two layers of the credits rule). `EngineHealthService`. Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
