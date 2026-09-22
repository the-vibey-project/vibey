## Title
refactor(db): the handoff repository goes through the ORM seam and gets its declared contract

## Why
Every persistence access goes through the ORM behind a declared interface (ADR-0016,
sub-doctrine 9.b; draft ADR `specs/ADR-orm.md`). `PostgresHandoffRepository`
(`src/vibey/infrastructure/db/handoff_repository.py:34-93`) is three raw asyncpg statements
— `record` (`:38-69`), `get` (`:71-76`), `list_for_pair` (`:78-93`) — and two 9.b gaps:
- no contract: the application port `HandoffStore`
  (`src/vibey/application/interfaces/ledger.py:173-177`) declares only `record`, and
  `src/vibey/infrastructure/interfaces/class_contracts.py` has no
  `PostgresHandoffRepositoryInterface` for the adapter's `get` and `list_for_pair`;
- its row mapper is a bare module function, `_row_to_dict` (`:96-113`).
The no-loss gate's attempt history lives in this table (data-model §3.7), so the stored
`envelope` and `gate_violations` JSON must read back exactly as today.

## Required behaviour
1. New `class HandoffRowMapper` in `handoff_repository.py` with
   `to_dict(self, row: Mapping[str, Any]) -> dict[str, object]`: the fifteen keys of
   `_row_to_dict`, in the same order, except `envelope=JSON_COLUMNS.mapping(row["envelope"])`
   and `gate_violations=JSON_COLUMNS.sequence(row["gate_violations"])` (lane `orm-tables`).
   `HANDOFF_ROWS: Final[HandoffRowMapperInterface] = HandoffRowMapper()`. `_row_to_dict` is
   deleted.
2. `PostgresHandoffRepository.__init__(self, orm: PostgresOrmInterface, *, rows: HandoffRowMapperInterface = HANDOFF_ROWS)`.
3. With `HANDOFFS = TABLES.table("handoff")`:
   - `record`: in `self._orm.transaction()`,
     `insert(HANDOFFS).values(handoff_id=…, project_id=…, cycle=…, phase=envelope.phase.value, job_id=None, from_engine=…, to_engine=…, reason=…, from_seq=…, to_seq=…, range_digest=…, envelope=json.loads(envelope_to_json(envelope)), gate_mode=…, gate_attempts=…, gate_violations=json.loads(violations_to_json(envelope.gate)), accepted=envelope.gate.ok).returning(HANDOFFS.c["handoff_id"])`,
     values exactly as today (`:52-67`). `json.loads(envelope_to_json(...))` keeps today's
     serialization rules (UUIDs, datetimes and enums through `_json_default`) and hands the
     JSONB column a plain JSON value. Return
     `UUID(str((await conn.execute(stmt)).scalar_one()))`, as `:69` does today.
   - `get`: `select(HANDOFFS).where(HANDOFFS.c["handoff_id"] == handoff_id)` in `connect()`;
     `None` or `self._rows.to_dict(row)`.
   - `list_for_pair`: `select(HANDOFFS).where(HANDOFFS.c["project_id"] == project_id, HANDOFFS.c["to_engine"] == to_engine, HANDOFFS.c["from_engine"].is_not_distinct_from(from_engine)).order_by(HANDOFFS.c["created_at"])`.
4. Interfaces in the new `src/vibey/infrastructure/db/interfaces/handoff_repository_interface.py`:
   `HandoffRowMapperInterface` (`to_dict`), exported from `interfaces/__init__.py`.
5. A new contract in `src/vibey/infrastructure/interfaces/class_contracts.py`, next to
   `PostgresEngineHealthRepositoryInterface` (`:63`):
   ```python
   @runtime_checkable
   class PostgresHandoffRepositoryInterface(HandoffStore, Protocol):
       """The Postgres implementation of the handoff store, with its two readers."""

       async def get(self, handoff_id: UUID) -> Mapping[str, object] | None: ...

       async def list_for_pair(
           self, project_id: UUID, *, from_engine: str | None, to_engine: str
       ) -> tuple[Mapping[str, object], ...]: ...
   ```
   (import `HandoffStore` with the other application interfaces there), exported from
   `src/vibey/infrastructure/interfaces/__init__.py` in the same way as the others.
6. `build_app` passes `handoffs=PostgresHandoffRepository(orm)` (`src/vibey/bootstrap.py:934`).
7. `envelope_to_json`, `violations_to_json` and `_json_default` are unchanged.

## Where to change
- `src/vibey/infrastructure/db/handoff_repository.py`
- `src/vibey/infrastructure/db/interfaces/handoff_repository_interface.py` (new)
- `src/vibey/infrastructure/db/interfaces/__init__.py`
- `src/vibey/infrastructure/interfaces/class_contracts.py`, `src/vibey/infrastructure/interfaces/__init__.py`
- `src/vibey/bootstrap.py` (one line)
- `tests/infrastructure/db/test_handoff_repository.py` (append only)
- New `tests/infrastructure/orm/test_handoff_row_mapper.py` (no database)

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings
in `src/`; substitute at the declared seam, never by patching an import; never edit a
protected test; the first line of every new file is the provenance comment copied
byte-for-byte from a sibling.

## Acceptance criteria
- [ ] `grep -n "asyncpg" src/vibey/infrastructure/db/handoff_repository.py` prints nothing.
- [ ] `isinstance(PostgresHandoffRepository(migrated_pool), PostgresHandoffRepositoryInterface)` and `isinstance(..., HandoffStore)`.
- [ ] Every existing test in `test_handoff_repository.py` passes unchanged (round trip, every attempt's violations, ordering, the synthesized `from_engine=None` pair).
- [ ] The stored `envelope` reads back equal to `json.loads(envelope_to_json(envelope))`.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
Append to `tests/infrastructure/db/test_handoff_repository.py` (integration):
- `test_the_repository_is_its_declared_contract`
- `test_the_envelope_reads_back_as_its_serialized_json`
`tests/infrastructure/orm/test_handoff_row_mapper.py` (no database):
- `test_decoded_and_text_json_columns_map_the_same` (one row with `envelope`/`gate_violations`
  as dict/list, one with the same as JSON text)
- `test_the_mapper_is_its_declared_seam`

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_handoff_repository.py tests/infrastructure/db/test_end_to_end_forced_rotation.py
    # No-services unit tests (need no database once the in-memory-fakes work lands; today the root conftest still opens one at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_handoff_row_mapper.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- The three JSON helper functions (converging them into a class is a separate change).
- The `HandoffStore` application port. Docs, CHANGELOG.
Do not push. Commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
