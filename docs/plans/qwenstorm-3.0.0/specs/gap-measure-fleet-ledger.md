## Title
feat(db): the fleet ledger project holds measurements that belong to no one project

## Why
Sub-doctrine 7.c (`src/vibey_tools/gh/docs/doctrines.md:82-91`) puts every measurement in the
ledger, and 8.g (`:316-324`) measures queues, surfaces, models and test runs that serve every
project at once. The ledger is per project: `event.project_id` is `NOT NULL REFERENCES project(id)`
and `seq` is gapless per project (`migrations/0002_event.sql:3-19`,
`migrations/0013_ledger_partitioning.sql:18-35`). A measurement with no project therefore needs
a project row to be appended under. This lane gives it one: the **fleet ledger project**, whose
id the composition root passes in from `[measure] fleet_project_id` (lane `gap-measure-config`,
default `vibey.domain.measurement.FLEET_PROJECT_ID`), ensured idempotently through the ORM seam.

Two properties keep it out of the way. Its `created_at` is the Unix epoch, and `get_latest()`
skips it, so `vibey status`, `vibey worker` and every other "latest project" default
(`src/vibey/cli/main.py:616`, `:722`, `:804`, … and `cli/ledger_search.py:210`) never picks it,
even on a fresh database where it is the only row. Its phase is `done`, so no transition or job
ever applies to it. This is a design decision flagged for the operator (see the report).

## Required behaviour
1. New `src/vibey/infrastructure/db/fleet_ledger_project.py`:
   - `FLEET_REPO_PATH_PREFIX: Final = "vibey-fleet:"`,
     `FLEET_PROJECT_NAME: Final = "vibey fleet measurements"`,
     `FLEET_CREATED_AT: Final = datetime(1970, 1, 1, tzinfo=UTC)`,
     `PROJECT = TABLES.table("project")` (lane `orm-tables`).
   - `class FleetLedgerProject`, `__init__(self, orm: PostgresOrmInterface, *, project_id: UUID)`;
     property `project_id -> UUID`.
   - `async def ensure(self) -> UUID`: the first call runs, in `self._orm.transaction()`,
     ```python
     pg_insert(PROJECT).values(
         id=self._project_id, name=FLEET_PROJECT_NAME,
         repo_path=f"{FLEET_REPO_PATH_PREFIX}{self._project_id}", phase="done", cycle=1,
         max_cycles=10, config={"fleet": True, "holds": "measurements no one project owns (8.g)"},
         created_at=FLEET_CREATED_AT, updated_at=FLEET_CREATED_AT,
     ).on_conflict_do_nothing(index_elements=[PROJECT.c["id"]])
     ```
     (`from sqlalchemy.dialects.postgresql import insert as pg_insert`), then remembers success;
     later calls return the id without a statement. A failed insert is not remembered, so the
     next call tries again. Returns `self._project_id`.
2. New `src/vibey/infrastructure/db/interfaces/fleet_ledger_project_interface.py`:
   `@runtime_checkable class FleetLedgerProjectInterface(Protocol)` with property `project_id`
   and `async def ensure(self) -> UUID`.
3. `src/vibey/infrastructure/db/project_repository.py` `get_latest` (in the ORM form lane
   `orm-project` gives it: `select(PROJECT).order_by(PROJECT.c["created_at"].desc()).limit(1)`)
   gains `.where(PROJECT.c["repo_path"].not_like(f"{FLEET_REPO_PATH_PREFIX}%"))`, importing
   the prefix from `fleet_ledger_project.py`. Nothing else in the file changes.
4. `tests/fakes/measurement.py` (lane `gap-measure-port`) gains
   `class InMemoryFleetLedgerProject` (implements `FleetLedgerProjectInterface`):
   `__init__(self, project_id: UUID = FLEET_PROJECT_ID)`; `ensure` returns the id and counts
   `ensures`; `fail_next(exc)` makes the next `ensure` raise.
5. `tests/fakes/registry.py`: `DRIVER_SEAMS` gains `FleetLedgerProjectInterface`; `REGISTRY` gains
   `FakeRegistration(FleetLedgerProjectInterface, InMemoryFleetLedgerProject)`.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings in
`src/`; substitute at the declared seam, never by patching an import; never edit a protected
test; the first line of every new file is the provenance comment copied byte-for-byte from a
sibling.

## Where to change
- New `src/vibey/infrastructure/db/fleet_ledger_project.py` and its interface file.
- `src/vibey/infrastructure/db/project_repository.py` (one `.where(...)`, one import).
- `tests/fakes/measurement.py`, `tests/fakes/registry.py`.
- New `tests/infrastructure/orm/test_fleet_ledger_project.py` (no database, `FakeOrm` from
  `tests/infrastructure/orm/fakes.py`, lane `orm-test-harness`) and new
  `tests/infrastructure/db/test_fleet_ledger_project.py` (integration: every test under
  `tests/infrastructure/db/` is marked `integration` by its conftest, `:17-19`).

## Acceptance criteria
- [ ] The compiled insert (`stmt.compile(dialect=postgresql.dialect())`) contains
      `ON CONFLICT (id) DO NOTHING` and binds `repo_path = "vibey-fleet:<id>"`, `phase = "done"`
      and `created_at = 1970-01-01T00:00:00+00:00`.
- [ ] Against a migrated database, `ensure()` twice (on two instances) leaves exactly one fleet
      row, and `get_latest()` returns the `project_id` fixture's project, never the fleet.
- [ ] On a database whose only project is the fleet, `get_latest()` returns `None`.
- [ ] A `LedgerEventDraft` for the fleet id appends after `ensure()` (the foreign key holds).
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_fleet_ledger_project.py`:
- `test_ensure_inserts_once_and_remembers`
- `test_the_insert_does_nothing_on_conflict_and_dates_the_row_at_the_epoch`
- `test_a_failed_ensure_is_tried_again`
- `test_fleet_ledger_project_satisfies_its_interface`

`tests/infrastructure/db/test_fleet_ledger_project.py` (integration; fixtures `migrated_pool`,
`project_id` from the conftest):
- `test_ensure_is_idempotent_across_instances`
- `test_get_latest_never_returns_the_fleet`
- `test_get_latest_is_none_when_only_the_fleet_exists`
- `test_the_fleet_accepts_ledger_events`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_fleet_ledger_project.py tests/fakes
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_fleet_ledger_project.py tests/infrastructure/db/test_project_repository.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Writing measurements (`gap-measure-ledger-sink`); a migration (none is needed: the row is
  data, ensured at first use); listing or hiding the fleet in any other command.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees.

Commit as `feat(db): the fleet ledger project holds measurements that belong to no one project`. Do not push.

## Lane card
- **Depends on:** `gap-measure-port` (the fakes module), `orm-project`
  (the ORM `get_latest`), `orm-tables`, `orm-test-harness`, `fakes-registry`.
- **Must keep passing unchanged:** `tests/infrastructure/db/test_project_repository.py` and the
  protected tests.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
