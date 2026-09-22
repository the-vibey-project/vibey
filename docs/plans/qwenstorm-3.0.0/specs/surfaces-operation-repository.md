## Title
feat(db): PostgresSurfaceOperationRepository records the intent and result of guarded surface operations through the ORM seam

## Why
Draft ADR-0047 §8 (`specs/ADR-surface-lanes.md`, "Guarded operations"): for `create_page`,
`send_email` and `send_sms` — whose backends cannot deduplicate — the lane writes an intent row
**before** the effect and a result row **after** it, keyed by `(surface, op_id)` with a
`request_digest`. What it does next depends on the row it finds (none, `done`, `started`,
`failed`, `parked`, or a different digest). This lane is the store for that protocol, on the
table migration 0015 created (`surfaces-migration`).

Every persistence access goes through `PostgresOrmInterface` with SQLAlchemy Core (draft
ADR-ORM `specs/ADR-orm.md` §1–§3; `specs/orm-database-seam.md`), over the typed table
(`TABLES.table(...)`, `specs/orm-tables.md`). No SQL strings, no asyncpg. Part of ADR-0047
lanes S10–S12.

## Required behaviour
In the new `src/vibey/infrastructure/db/surface_operation_repository.py`:

1. `class SurfaceOperationState(StrEnum)`: `STARTED="started"`, `DONE="done"`, `FAILED="failed"`, `PARKED="parked"`.
2. `@dataclass(frozen=True, slots=True) class SurfaceOperationRecord`: `surface: str`,
   `op_id: str`, `operation: str`, `request_digest: str`, `state: SurfaceOperationState`,
   `result: object`, `detail: str`, `request_id: str`, `instance: str`, `attempts: int`,
   `created_at: datetime`, `updated_at: datetime`.
3. `class SurfaceOperationRowMapper` with `to_record(self, row: Mapping[str, Any]) -> SurfaceOperationRecord`:
   `result` is `JSON_COLUMNS.optional_mapping(row["result"])["value"]` when the column is not
   null, else `None`. `OPERATION_ROWS: Final[SurfaceOperationRowMapperInterface] = SurfaceOperationRowMapper()`.
4. `class PostgresSurfaceOperationRepository`,
   `__init__(self, orm: PostgresOrmInterface, *, rows: SurfaceOperationRowMapperInterface = OPERATION_ROWS)`,
   with `OPS = TABLES.table("surface_operation")`:
   - `async get(self, surface: str, op_id: str) -> SurfaceOperationRecord | None`: in
     `orm.connect()`, `select(OPS).where(OPS.c["surface"] == surface, OPS.c["op_id"] == op_id)`.
   - `async start(self, *, surface: str, op_id: str, operation: str, request_digest: str, request_id: str, instance: str) -> bool`:
     in `orm.transaction()`,
     `postgresql.insert(OPS).values(surface=…, op_id=…, operation=…, request_digest=…, state="started", request_id=…, instance=…, attempts=1).on_conflict_do_nothing(index_elements=[OPS.c["surface"], OPS.c["op_id"]]).returning(OPS.c["op_id"])`;
     returns whether a row came back (False means another delivery won the race).
   - `async restart(self, *, surface, op_id, request_id, instance) -> bool`: in a transaction,
     `update(OPS).where(surface, op_id, OPS.c["state"].in_(["failed", "parked"])).values(state="started", attempts=OPS.c["attempts"] + 1, request_id=…, instance=…, detail="", updated_at=func.now()).returning(OPS.c["op_id"])`;
     True when a row changed.
   - `async finish(self, *, surface, op_id, state: SurfaceOperationState, result: object = None, detail: str = "") -> bool`:
     in a transaction, `update(OPS).where(surface, op_id).values(state=state.value, result={"value": result} if state is DONE else None, detail=detail[:2000], updated_at=func.now()).returning(OPS.c["op_id"])`.
     `STARTED` is refused with `ValueError` (use `start`/`restart`).
   Statements bind through the column types (draft ADR-ORM §3 rules); no `text()`.
5. **Interfaces** in the new `src/vibey/infrastructure/db/interfaces/surface_operation_repository_interface.py`:
   `SurfaceOperationRowMapperInterface` (`to_record`) and
   `SurfaceOperationRepositoryInterface` (`get`, `start`, `restart`, `finish`), both
   `@runtime_checkable`, exported from `src/vibey/infrastructure/db/interfaces/__init__.py`.
   The records and the enum are values and are imported by the interface file only under
   `TYPE_CHECKING`.

## Where to change
- New `src/vibey/infrastructure/db/surface_operation_repository.py`,
  `src/vibey/infrastructure/db/interfaces/surface_operation_repository_interface.py`;
  `src/vibey/infrastructure/db/interfaces/__init__.py` (exports).
- New `tests/infrastructure/orm/test_surface_operation_repository.py` (no database) and
  `tests/infrastructure/db/test_surface_operation_repository.py` (integration).

## Acceptance criteria
- [ ] Unit (`FakeOrm`, `specs/orm-test-harness.md`): `start` issues one insert that compiles (postgresql dialect) to `ON CONFLICT (surface, op_id) DO NOTHING RETURNING surface_operation.op_id`; `restart` filters on `state IN ('failed', 'parked')`; `finish(state=DONE, result="7")` binds `{"value": "7"}`; `finish(state=STARTED)` raises; the mapper reads decoded and text JSON alike.
- [ ] Integration: `start` twice returns True then False; `get` reads the row; `finish(DONE, result="page-9")` then `get` gives `result == "page-9"`; `restart` moves `parked` and `failed` back to `started` with `attempts == 2`, and refuses (`False`) a `done` or `started` row.
- [ ] `grep -n "asyncpg\|text(" src/vibey/infrastructure/db/surface_operation_repository.py` prints nothing.
- [ ] `isinstance(repo, SurfaceOperationRepositoryInterface)`; 100% `infrastructure/` branch coverage.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_surface_operation_repository.py` (no database):
- `test_start_inserts_once_on_conflict_do_nothing`
- `test_restart_only_moves_failed_or_parked`
- `test_finish_wraps_the_result_and_refuses_started`
- `test_the_mapper_reads_decoded_and_text_json`
- `test_repository_and_mapper_satisfy_their_interfaces`
`tests/infrastructure/db/test_surface_operation_repository.py` (integration; `migrated_pool` is the ORM seam):
- `test_start_is_won_once`
- `test_finish_then_get_round_trips_the_result`
- `test_restart_moves_parked_and_failed_only`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    uv run bandit -q -r src/vibey
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/infrastructure/orm/test_surface_operation_repository.py
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_surface_operation_repository.py tests/infrastructure/db/test_orm.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The guard protocol that uses it (`surfaces-guarded-execution`); its in-memory fake and
  contract (`surfaces-records-fakes`); wiring it into `build_app` (`surfaces-composition`).
  CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the skill trees
  (`surfaces-docs-wave`). Do not push, open PRs or change remotes. Commit locally with the
  Title as the subject.

## Lane card
- **Depends on:** `surfaces-migration`, `orm-database-seam`, `orm-tables`, `orm-test-harness`.
- **Shares a file with:** `src/vibey/infrastructure/db/interfaces/__init__.py` (exports only).
- **Must keep passing unchanged:** every test in `tests/infrastructure/db/` and `tests/infrastructure/orm/`, all protected tests.
- **Standing constraints (every surfaces lane):**
  - Read `/private/tmp/claude-501/storm/qwenstorm-3.0.0/EDITING-RULES.md` before changing a file.
  - Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`, `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
  - Line 1 of every new file is the provenance comment, copied byte-for-byte from line 1 of a sibling file.
  - Production code reaches PostgreSQL only through `PostgresOrmInterface`; no new `import asyncpg`, `text()`, `literal_column`, `exec_driver_sql()` or SQL string in `src/`.
  - Substitute only at the declared seam (`FakeOrm`); never `monkeypatch.setattr`, `mock.patch`, `MagicMock` or `AsyncMock`.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
