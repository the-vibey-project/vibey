## Title
feat(db): PostgresLedgerSegmentStore keeps sealed ledger segments in ledger_segment through the ORM seam

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, "Current state": "**There is no PostgreSQL
tier store**", and "Proposed child issues" 2: "Persistence goes through `PostgresOrmInterface`
(SQLAlchemy), never new raw SQL … It is not wired yet"). The table exists after
`roadmap-114-postgres-tier-store-p1` (`migrations/0016_ledger_segment.sql`, `LedgerSegmentOrm`
in the `orm_models.ORM_TABLE_MODELS` registry that `orm-tables`' `TABLES` reads); the value is
`LedgerSegment` (`-p2`); the port, its fake and its contract suite are `LedgerSegmentStore`,
`InMemoryLedgerSegmentStore` and `tests/contracts/test_ledger_segment_store_contract.py` (`-p3`).
This lane is the PostgreSQL implementation, written as SQLAlchemy Core over the seam (draft ADR
`specs/ADR-orm.md` §1, §3: "Bind through the column's type"; "Values, not fragments"), with a
class contract beside it (sub-doctrine 9.b, `src/vibey_tools/gh/docs/doctrines.md:349`;
ADR-0016), unit tests on `FakeOrm` in the default tier and the contract's `postgres` backend in
the integration tier (fakes amendment A5, `specs/ADR-test-harness-fakes-amendment.md`).
Every job is idempotent under replay (CLAUDE.md), so a replayed seal must be a no-op, including
when two writers race on the same `first_seq`.

## Required behaviour
1. `src/vibey/infrastructure/db/ledger_segment_store.py` (new):
   - Module docstring: the PostgreSQL home of sealed ledger segments (vibey#114); one row per
     segment in `ledger_segment` (`migrations/0016_ledger_segment.sql`), append-only by rule and
     by `AppendOnlyGuard`; not wired into `build_app` until the rotation lane.
   - `SEGMENTS = TABLES.table("ledger_segment")` (module constant; `from vibey.infrastructure.db.tables import TABLES`).
   - `class PostgresLedgerSegmentStore:` with `__init__(self, orm: PostgresOrmInterface) -> None`.
   - `async def put_segment(self, segment: LedgerSegmentInterface) -> None`:
     1. `if not segment.intact:` raise
        `ValueError(f"ledger segment {segment.project_id}:{segment.first_seq}-{segment.last_seq} does not hash to its digest; refusing to store it")`
        before any statement (the same message as the fake).
     2. `async with self._orm.transaction() as conn:`
        - `overlapping = (await conn.execute(select(SEGMENTS).where(SEGMENTS.c["project_id"] == segment.project_id, SEGMENTS.c["first_seq"] <= segment.last_seq, SEGMENTS.c["last_seq"] >= segment.first_seq).order_by(SEGMENTS.c["first_seq"]))).mappings().all()`
        - `for row in overlapping:` return if `self._segment(row).same_seal(segment)`; otherwise
          raise `LedgerSegmentConflict(segment.project_id, segment.first_seq, segment.last_seq)`.
        - `await conn.execute(pg_insert(SEGMENTS).values(project_id=segment.project_id, first_seq=segment.first_seq, last_seq=segment.last_seq, codec=segment.codec, digest=segment.digest, data=segment.data).on_conflict_do_nothing(index_elements=[SEGMENTS.c["project_id"], SEGMENTS.c["first_seq"]]))`
          (`from sqlalchemy.dialects.postgresql import insert as pg_insert`).
        - `stored = (await conn.execute(select(SEGMENTS).where(SEGMENTS.c["project_id"] == segment.project_id, SEGMENTS.c["first_seq"] == segment.first_seq))).mappings().one()`;
          if `not self._segment(stored).same_seal(segment)`, raise `LedgerSegmentConflict(...)`
          (a concurrent writer stored a different seal at the same `first_seq` between the
          read and the insert; the transaction rolls back).
       Comment above the method: overlapping *different* ranges written concurrently are not
       serialized here; the rotation job runs once per project (`roadmap-114-design-rotation`),
       and two verified copies of the same append-only rows read back identically.
   - `async def segments(self, project_id: UUID, *, from_seq: int, to_seq: int) -> tuple[LedgerSegment, ...]`:
     through `self._orm.connect()`, `select(SEGMENTS).where(SEGMENTS.c["project_id"] == project_id, SEGMENTS.c["first_seq"] <= to_seq, SEGMENTS.c["last_seq"] >= from_seq).order_by(SEGMENTS.c["first_seq"])`,
     rows from `.mappings().all()`, each through `self._segment`.
   - `async def segments_for_project(self, project_id: UUID) -> tuple[LedgerSegment, ...]`:
     the same without the two seq conditions.
   - `@staticmethod def _segment(row: Mapping[str, Any]) -> LedgerSegment` (a method, so the
     mapping lives on the class that owns the table):
     `LedgerSegment(project_id=row["project_id"], first_seq=row["first_seq"], last_seq=row["last_seq"], codec=row["codec"], digest=row["digest"], data=bytes(row["data"]))`.
   - No `text()`, no SQL strings, no `import asyncpg`, no update or delete statement.
2. `src/vibey/infrastructure/db/interfaces/ledger_segment_store_interface.py` (new):
   `@runtime_checkable class PostgresLedgerSegmentStoreInterface(LedgerSegmentStore, Protocol)`
   with the docstring "The PostgreSQL implementation of the sealed-segment port (vibey#114)."
   (the pattern of `PostgresJobRepositoryInterface`,
   `src/vibey/infrastructure/interfaces/class_contracts.py:68`). Export it from
   `src/vibey/infrastructure/db/interfaces/__init__.py` (`__all__` alphabetical).
3. The contract suite (`tests/contracts/test_ledger_segment_store_contract.py`, from `-p3`):
   - add an async fixture, used only by the `postgres` branch:
     ```python
     @pytest_asyncio.fixture
     async def other_project_id(migrated_pool: MigratedDatabase) -> UUID:
         pid = await migrated_pool.fetchval(
             "INSERT INTO project (name, repo_path, config) VALUES ($1, $2, '{}'::jsonb) RETURNING id",
             "segment-contract-other",
             "/tmp/segment-contract-other",
         )
         return UUID(str(pid))
     ```
   - the `case` fixture stays a **sync** fixture (so `request.getfixturevalue` can resolve the
     async database fixtures lazily, and the `memory` backend never touches the database); its
     `params` becomes `backends()` (from `tests/contracts/conftest.py`, lane
     `fakes-contracts-repositories`), its `-p3` comment is removed, and a `"postgres"` branch
     returns `SegmentStoreCase(PostgresLedgerSegmentStore(request.getfixturevalue("migrated_pool")), request.getfixturevalue("project_id"), request.getfixturevalue("other_project_id"))`.
   - No contract test body changes.
4. `tests/contracts/test_every_repository_port_has_a_contract.py` (lane
   `fakes-contracts-repositories`): add one entry for `LedgerSegmentStore` naming
   `test_ledger_segment_store_contract.py`, in the form the existing entries use.

## Where to change
- `src/vibey/infrastructure/db/ledger_segment_store.py` (new; line 1 is the provenance comment
  copied byte-for-byte from line 1 of `src/vibey/infrastructure/db/ledger_repository.py`).
- `src/vibey/infrastructure/db/interfaces/ledger_segment_store_interface.py` (new; same line 1).
- `src/vibey/infrastructure/db/interfaces/__init__.py` (`edit_file`).
- `tests/contracts/test_ledger_segment_store_contract.py` (`edit_file`: the fixture only).
- `tests/contracts/test_every_repository_port_has_a_contract.py` (`edit_file`: one entry).
- `tests/infrastructure/orm/test_ledger_segment_store_unit.py` (new; same line 1).
Not `bootstrap.py`: the store is not wired.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings in
`src/`; substitute at the declared seam, never by patching an import; never edit a protected
test.

## Acceptance criteria
- [ ] `isinstance(PostgresLedgerSegmentStore(FakeOrm()), PostgresLedgerSegmentStoreInterface)` and `isinstance(..., LedgerSegmentStore)`.
- [ ] Every contract test passes on both backends: `-m "not integration"` (memory) and `-m integration` (postgres).
- [ ] `grep -n "text(\|asyncpg\|exec_driver_sql\|\"SELECT\|\"INSERT" src/vibey/infrastructure/db/ledger_segment_store.py` prints nothing.
- [ ] `grep -rn "PostgresLedgerSegmentStore" src/vibey/bootstrap.py` prints nothing.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_ledger_segment_store_unit.py` (no database; `FakeOrm`, `FakeResult`
from `tests/infrastructure/orm/fakes.py`, lane `orm-test-harness`). Helpers:
`SEGMENT = LedgerSegment.seal(project_id=PROJECT, first_seq=1, last_seq=3, codec="jsonl+zlib", data=b"sealed")`
and `_row(segment) -> dict[str, object]` with the six columns plus `"sealed_at": datetime(2026, 9, 22, tzinfo=UTC)`:
- `test_the_store_is_its_declared_seam`
- `test_a_new_seal_reads_overlaps_then_inserts_then_rereads` — `orm = FakeOrm(FakeResult(), FakeResult(), FakeResult([_row(SEGMENT)]))`; `put_segment(SEGMENT)`; `len(orm.connection.statements) == 3`; the second statement compiled with `postgresql.dialect()` contains `ON CONFLICT (project_id, first_seq) DO NOTHING`.
- `test_a_replay_found_by_the_overlap_read_writes_nothing` — `FakeOrm(FakeResult([_row(SEGMENT)]))`; one statement only.
- `test_an_overlapping_different_seal_is_a_conflict` — `FakeOrm(FakeResult([_row(LedgerSegment.seal(project_id=PROJECT, first_seq=2, last_seq=5, codec="jsonl+zlib", data=b"x"))]))`; `LedgerSegmentConflict`; one statement.
- `test_a_different_seal_stored_concurrently_is_a_conflict` — `FakeOrm(FakeResult(), FakeResult(), FakeResult([_row(dataclasses.replace(SEGMENT, digest=hashlib.sha256(b"other").hexdigest(), data=b"other"))]))`; `LedgerSegmentConflict`.
- `test_a_segment_that_does_not_hash_is_refused_before_any_statement` — `dataclasses.replace(SEGMENT, data=b"rotted")`; `ValueError` matching `does not hash to its digest`; `orm.connection.statements == []`.
- `test_rows_map_back_to_segments_in_order` — `segments(PROJECT, from_seq=1, to_seq=9)` over `FakeOrm(FakeResult([_row(a), _row(b)]))` returns `(a, b)`; `segments_for_project` the same over a second `FakeOrm`; a `memoryview` in `data` maps to `bytes`.

The contract's `postgres` backend (item 3) is the integration test.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    export VIBEY_TEST_TEMPLATE_DB=vibey_test_template_seg114
    # No-services unit tests and the memory contract:
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_ledger_segment_store_unit.py
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_ledger_segment_store_contract.py tests/fakes
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider -m integration tests/contracts
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_ledger_segment_table.py tests/infrastructure/db/test_orm.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Wiring the store into `build_app` or any worker (the rotation lane, after
  `roadmap-114-design-rotation`); reading segments back into ledger reads
  (`roadmap-114-tier-aware-reads-p3`).
- Archive segments on the blob surface or an archival node (#114 open question 4, unanswered).
- The migration and the ORM model (`-p1`); the value (`-p2`); the port and fake (`-p3`).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
