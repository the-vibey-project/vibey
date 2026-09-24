## Title
feat(db): PostgresLedgerRepository.range() and all_for_project() read raw rows and sealed segments as one ordered ledger

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, Scope 5 "Reads are tier-aware.
`PostgresLedgerRepository.range()` / `all_for_project()` … return one coherent, ordered answer
across tiers", Acceptance "the same ordered events as an untiered ledger. The no-loss gate's R6
digest over a tiered range equals the untiered digest", and "Proposed child issues" 3). Every
application reader of the ledger goes through `all_for_project` (e.g.
`src/vibey/application/budget_source.py:96`, `src/vibey/application/ledger_publication.py:209`,
`src/vibey/application/design_acceptance.py:67`) or `range`, and the full-ledger handoff writer
digests what they return (`src/vibey/infrastructure/ledger/full_ledger_writer.py:2-7`: "the digest
in the returned LedgerRef is exactly `domain.ledger.digest_range(events)`, so R6 … can verify").
Today both methods read `event` only (at this cutoff `src/vibey/infrastructure/db/ledger_repository.py:164-185`).

**This lane builds on `orm-ledger`'s post-lane shape of `ledger_repository.py`, not on the file
at this cutoff:** after `orm-ledger`, `PostgresLedgerRepository.__init__(self, orm: PostgresOrmInterface, *, appender: EventAppenderInterface = DEFAULT_EVENT_APPENDER)`,
and `range` / `all_for_project` read through `self._orm.connect()` with
`select(EVENT).where(...).order_by(EVENT.c["seq"])`, mapping `.mappings().all()` with
`EVENT_ROWS.to_event` (`specs/orm-ledger.md`, Required behaviour 4). The segment store is
`LedgerSegmentStore` (`roadmap-114-postgres-tier-store-p3`; PostgreSQL implementation `-p4`); the
merge rule is `TieredEventMerger` (`roadmap-114-tier-aware-reads-p2`). The repository gains the
store as an optional constructor keyword (sub-doctrine 9.b, `src/vibey_tools/gh/docs/doctrines.md:349`:
substitution at the declared seam), defaulting to none, so `build_app` and every existing caller
read exactly as today until the rotation lane wires a store.

## Required behaviour
1. `src/vibey/infrastructure/db/ledger_repository.py`:
   - Imports: `from vibey.application.interfaces.ledger_segments import LedgerSegmentStore`,
     `from vibey.infrastructure.db.interfaces import TieredEventMergerInterface` (add to the
     existing `from vibey.infrastructure.db.interfaces import …` line), and
     `from vibey.infrastructure.db.tiered_events import LAST_SEQ, TieredEventMerger`.
   - Immediately after the `EVENT_ROWS` constant and its docstring, add:
     ```python
     TIERED_EVENTS: Final[TieredEventMergerInterface] = TieredEventMerger(EVENT_ROWS)
     """Raw rows merged with sealed segments (vibey#114), mapped with `EVENT_ROWS`. Built
     here, beside the row mapper it reads segment rows with; stateless, so one instance serves."""
     ```
   - `PostgresLedgerRepository.__init__` gains two keyword parameters after `appender`:
     `segments: LedgerSegmentStore | None = None` and
     `tiers: TieredEventMergerInterface = TIERED_EVENTS`; store them as `self._segments` and
     `self._tiers`.
   - `range`: keep `orm-ledger`'s raw read unchanged inside its `async with self._orm.connect() as conn:`
     block, but bind the result to `raw` (`raw = tuple(EVENT_ROWS.to_event(r) for r in rows)`)
     instead of returning it. **After** the `async with` block (one connection at a time):
     ```python
     if self._segments is None:
         return raw
     held = await self._segments.segments(project_id, from_seq=from_seq, to_seq=to_seq)
     return self._tiers.merge(project_id, raw, held, from_seq=from_seq, to_seq=to_seq)
     ```
   - `all_for_project`: the same pattern, with
     `held = await self._segments.segments_for_project(project_id)` and
     `self._tiers.merge(project_id, raw, held, from_seq=1, to_seq=LAST_SEQ)`.
   - `latest_seq` is unchanged. Add to the class a docstring (it has none today):
     "The append-only event ledger. With a `LedgerSegmentStore`, `range` and `all_for_project`
     also read sealed segments (vibey#114): raw rows win, and a segment is opened only for a seq
     they lack. `latest_seq` reads the raw table alone, which stays correct because the newest
     record always stays raw (`TierConfig.standard_n >= 1`)."
2. `bootstrap.py` is **not** changed: `build_app` keeps `PostgresLedgerRepository(orm)`.
3. `src/vibey/infrastructure/interfaces/class_contracts.py`'s `PostgresLedgerRepositoryInterface`
   (`:77-86`) is unchanged: the method signatures do not change.

## Where to change
- `src/vibey/infrastructure/db/ledger_repository.py` (`edit_file` only; the file is over 100 lines).
- `tests/infrastructure/orm/test_tiered_ledger_reads_unit.py` (new; no database).
- `tests/infrastructure/db/test_tiered_ledger_reads.py` (new; integration: the directory's
  conftest marks it).
Line 1 of each new file is the provenance comment copied byte-for-byte from line 1 of
`tests/infrastructure/db/test_ledger_repository.py`.

Rules every ORM lane keeps: production code reaches PostgreSQL only through
`PostgresOrmInterface`; no new `import asyncpg`, `text()`, `exec_driver_sql()` or SQL strings in
`src/`; substitute at the declared seam, never by patching an import; never edit a protected
test.

## Acceptance criteria
- [ ] With segments covering part of a project's history, `range` and `all_for_project` return exactly what an untiered repository returns, and `_check_r6_range` over the tiered answer with the untiered `LedgerRef` is `()`.
- [ ] Seqs held only in segments come back, merged with raw rows in seq order.
- [ ] Every existing test in `tests/infrastructure/db/test_ledger_repository.py`, `test_build_ledger.py`, `test_design_ledger.py`, `test_review_ledger.py`, `test_ledger_search_repository.py` and `tests/domain/test_noloss*.py` (protected) passes unchanged.
- [ ] `git diff --stat HEAD -- src/vibey/bootstrap.py` prints nothing.
- [ ] 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_tiered_ledger_reads_unit.py` (no database; `FakeOrm`, `FakeResult`
from `tests/infrastructure/orm/fakes.py`; `InMemoryLedgerSegmentStore` from
`tests/fakes/ledger_segments.py`; `SEGMENT_CODEC` from `vibey.infrastructure.ledger.segment_codec`).
Build four `LedgerEvent`s for one `PROJECT` (seqs 1..4, as `tests/infrastructure/ledger/test_tier_manager.py:34-50`)
and a helper `_row(event) -> dict[str, object]` giving every `event` column by name, with
`phase`, `kind` and `provenance` as their `.value` and `payload` as a `dict`:
- `test_range_merges_sealed_segments_under_raw_rows` — `store` holds `SEGMENT_CODEC.seal(PROJECT, events[:2])`; `repo = PostgresLedgerRepository(FakeOrm(FakeResult([_row(events[2]), _row(events[3])])), segments=store)`; `await repo.range(PROJECT, from_seq=1, to_seq=4) == events`.
- `test_all_for_project_merges_sealed_segments_under_raw_rows` — the same through `all_for_project`.
- `test_without_a_segment_store_reads_raw_only` — `PostgresLedgerRepository(FakeOrm(FakeResult([_row(events[2])])))`; `range(PROJECT, from_seq=1, to_seq=4) == (events[2],)`.

`tests/infrastructure/db/test_tiered_ledger_reads.py` (integration; fixtures `migrated_pool`,
`project_id`; copy the `_draft` helper of `tests/infrastructure/db/test_ledger_repository.py:20-38`):
- `test_a_tiered_ledger_reads_exactly_as_the_untiered_one` — `plain = PostgresLedgerRepository(migrated_pool)`; append six drafts with payloads `{"n": i}`; `untiered = await plain.all_for_project(project_id)`; `store = PostgresLedgerSegmentStore(migrated_pool)`; `await store.put_segment(SEGMENT_CODEC.seal(project_id, untiered[:3]))`; `tiered = PostgresLedgerRepository(migrated_pool, segments=store)`; `await tiered.all_for_project(project_id) == untiered`; `await tiered.range(project_id, from_seq=2, to_seq=5) == untiered[1:5]`; and `_check_r6_range(await tiered.range(project_id, from_seq=1, to_seq=6), LedgerRef(uri="tiered", from_seq=1, to_seq=6, event_count=6, digest=digest_range(untiered))) == ()`.
- `test_seqs_held_only_in_segments_are_read_back_in_order` — a second project row (`INSERT INTO project … RETURNING id`); append three drafts to it through `plain` (seqs 1..3); build three `LedgerEvent`s for that project in memory with seqs 4..6 (`digest=digest_event(payload)`, `produced_at` aware); `put_segment(SEGMENT_CODEC.seal(other, those))`; `tiered.range(other, from_seq=1, to_seq=6)` has seqs `[1, 2, 3, 4, 5, 6]`, its last three equal the in-memory events, and `plain.range(other, from_seq=1, to_seq=6)` has only seqs 1..3. (A segment *above* the raw seqs is not how rotation will work; this only proves the merge reads a seq that exists in no raw row.)

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    export VIBEY_TEST_TEMPLATE_DB=vibey_test_template_seg114
    # No-services unit tests:
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_tiered_ledger_reads_unit.py tests/infrastructure/orm/test_tiered_events.py
    # Postgres-backed (integration tier):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/db/test_tiered_ledger_reads.py tests/infrastructure/db/test_ledger_repository.py tests/infrastructure/db/test_build_ledger.py tests/infrastructure/db/test_design_ledger.py tests/infrastructure/db/test_review_ledger.py tests/infrastructure/db/test_ledger_search_repository.py
    uv run pytest -q -p no:cacheprovider tests/domain/test_noloss.py tests/domain/test_noloss_reference.py
    git diff --stat HEAD -- src/vibey/bootstrap.py tests/domain tests/infrastructure/db/test_chaos.py   # must print nothing
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- Wiring a segment store into `build_app` or any worker, and writing segments from the live
  ledger (the rotation lanes that `roadmap-114-design-rotation` names).
- Tier-aware ledger search (`ledger_search_repository.py`), `latest_seq` over segments, archive
  segments on the blob surface (#114 open question 4, unanswered), the `vibey ledger
  tiers|archive|restore|verify` CLI.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
