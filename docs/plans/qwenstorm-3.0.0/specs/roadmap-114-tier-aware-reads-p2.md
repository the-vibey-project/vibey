## Title
feat(db): TieredEventMerger answers one ordered range from raw rows and sealed segments, the same answer as an untiered ledger

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, Scope 5: "`PostgresLedgerRepository.range()` /
`all_for_project()` … and the no-loss gate's R6 digest all return one coherent, ordered answer
across tiers", and Acceptance: "A query spanning all three tiers returns the same ordered events
as an untiered ledger. The no-loss gate's R6 digest over a tiered range equals the untiered
digest"). R6 is `_check_r6_range` (`src/vibey/domain/noloss.py:149-172`): it compares
`ref.digest` with `digest_range(ledger)` (`src/vibey/domain/ledger.py:217-224`, a fold over each
event's `seq` and stored `digest`), the event count, and `to_seq` against `max(seq)`. The only
cross-tier read today is `TierManager.get_range` (`src/vibey/infrastructure/ledger/tier_manager.py:95-110`),
which is synchronous, per-seq, lets a compressed copy **overwrite** a raw event (`:105-109`) and
decompresses every compressed record in range. The issue says the opposite: "Hot reads stay raw:
no decompression on the working set, ever" (#114 original text, "Standard mode").

This lane is the pure merge rule, before the repository uses it (`-p3`): raw rows win; a
segment is opened with the `jsonl+zlib` codec (`roadmap-114-tier-aware-reads-p1`) only when it
covers a requested seq the raw rows lack; rows are mapped with the one shared row mapper
(`EventRowMapper`, `src/vibey/infrastructure/db/ledger_repository.py:32-46`). The merger takes
that mapper in its constructor and this module does not import the repository, because the
repository will import this module (`-p3`). Like the codec, it is a pure policy, not a seam
needing a fake (fakes amendment A4). Sub-doctrines 7.a (`src/vibey_tools/gh/docs/doctrines.md:72-78`,
one coherent answer for every searcher) and 9.b (`doctrines.md:349`) bind it.

## Required behaviour
1. `src/vibey/infrastructure/db/tiered_events.py` (new):
   - Module docstring: one ordered answer across the raw ledger and its sealed segments
     (vibey#114). Raw rows win: they are the hot tier, read with no decompression, and a
     segment is only ever a verified copy of rows that were raw. A segment is opened only when
     it covers a requested seq the raw rows lack. Built with the shared row mapper by
     `ledger_repository.py` (`TIERED_EVENTS`), not here: this module must not import the
     repository that imports it.
   - `LAST_SEQ: Final = 2**63 - 1` with the docstring "The largest `event.seq` PostgreSQL holds
     (bigint, migrations/0013_ledger_partitioning.sql:21): the upper bound of a whole-project read."
   - `class TieredEventMerger:`
     - `__init__(self, rows: EventRowMapperInterface, *, codec: LedgerSegmentCodecInterface = SEGMENT_CODEC) -> None`.
     - `merge(self, project_id: UUID, raw: Sequence[LedgerEvent], segments: Sequence[LedgerSegmentInterface], *, from_seq: int, to_seq: int) -> tuple[LedgerEvent, ...]`,
       exactly:
       ```python
       found = {event.seq: event for event in raw if from_seq <= event.seq <= to_seq}
       for segment in sorted(segments, key=attrgetter("first_seq")):
           low, high = max(segment.first_seq, from_seq), min(segment.last_seq, to_seq)
           if low > high or all(seq in found for seq in range(low, high + 1)):
               continue
           for row in self._codec.open(project_id, segment):
               event = self._rows.to_event(row)
               if low <= event.seq <= high and event.seq not in found:
                   found[event.seq] = event
       return tuple(found[seq] for seq in sorted(found))
       ```
       A segment the read needs that fails to open raises the codec's `TierRecordError`
       unchanged: a gap is never silently skipped.
2. `src/vibey/infrastructure/db/interfaces/tiered_events_interface.py` (new):
   `@runtime_checkable class TieredEventMergerInterface(Protocol)` declaring `merge` with the
   signature above and the docstring "Raw rows and sealed segments as one ordered answer; raw
   rows win and a segment is opened only for a seq they lack." Types under `TYPE_CHECKING`
   (style of `interfaces/ledger_repository_interface.py:15-25`). Export it from
   `src/vibey/infrastructure/db/interfaces/__init__.py` (`__all__` alphabetical).
3. No module-level instance of the merger in `tiered_events.py` (the repository builds it in
   `-p3`).

## Where to change
- `src/vibey/infrastructure/db/tiered_events.py` (new; line 1 is the provenance comment copied
  byte-for-byte from line 1 of `src/vibey/infrastructure/db/ledger_repository.py`).
- `src/vibey/infrastructure/db/interfaces/tiered_events_interface.py` (new; same line 1).
- `src/vibey/infrastructure/db/interfaces/__init__.py` (`edit_file`).
- `tests/infrastructure/orm/test_tiered_events.py` (new; same line 1; no database — the
  directory `tests/infrastructure/db` would mark it `integration`).

## Acceptance criteria
- [ ] For every generated ledger, split into raw and segments in any way that covers it, `merge` over any range equals the untiered slice, and `_check_r6_range(merged, ref) == ()` for the untiered `ref`.
- [ ] A read whose range raw rows fully cover opens no segment.
- [ ] Raw rows win over a segment copy of the same seq.
- [ ] `lint-imports` green (`tiered_events.py` does not import `ledger_repository`); `mypy --strict src/vibey` clean; 100% branch coverage of `src/vibey/infrastructure/`.

## Tests to write first (TDD)
`tests/infrastructure/orm/test_tiered_events.py` (no service). Reuse the module-level helpers of
`roadmap-114-tier-aware-reads-p1`'s test by copying them into this file (`PROJECT`, `T0`,
`PAYLOADS`, `_event`, `ledgers()`); do not import from another test module. `MERGER = TieredEventMerger(EVENT_ROWS)`.
A test double at the declared seam (the `codec=` keyword; no mock):
```python
class CountingCodec:
    """The real codec, counting how often a segment is opened."""

    def __init__(self) -> None:
        self.opened: list[tuple[int, int]] = []

    @property
    def name(self) -> str:
        return SEGMENT_CODEC.name

    def seal(self, project_id: UUID, events: Sequence[LedgerEvent]) -> LedgerSegmentInterface:
        return SEGMENT_CODEC.seal(project_id, events)

    def open(self, project_id: UUID, segment: LedgerSegmentInterface) -> tuple[dict[str, Any], ...]:
        self.opened.append((segment.first_seq, segment.last_seq))
        return SEGMENT_CODEC.open(project_id, segment)
```
- `test_the_merger_is_its_declared_seam` — `isinstance(MERGER, TieredEventMergerInterface)`.
- `test_a_tiered_read_is_the_untiered_read` — `@settings(deadline=None) @given(ledgers(), st.data())`:
  draw `sealed_through` in `0..n`, `raw_from` in `1..sealed_through + 1`, `size` in `1..8`,
  `from_seq` in `1..n`, `to_seq` in `from_seq..n`; segments are
  `SEGMENT_CODEC.seal(PROJECT, events[i:min(i + size, sealed_through)])` for `i` in
  `range(0, sealed_through, size)`; raw is `events[raw_from - 1:]`; `expected = events[from_seq - 1:to_seq]`;
  assert `MERGER.merge(PROJECT, raw, segments, from_seq=from_seq, to_seq=to_seq) == expected`
  and `_check_r6_range(merged, LedgerRef(uri="tiered", from_seq=from_seq, to_seq=to_seq, event_count=len(expected), digest=digest_range(expected))) == ()`
  (`from vibey.domain.noloss import _check_r6_range`; `from vibey.domain.handoff import LedgerRef`).
- `test_raw_rows_that_cover_the_range_open_no_segment` — events 1..6, segment 1..3, raw 1..6; `CountingCodec().opened == []` after `merge(..., from_seq=1, to_seq=6)`.
- `test_a_segment_outside_the_range_is_never_opened` — segment 10..12 of a 12-event ledger, raw 4..12, range 4..6; nothing opened.
- `test_a_partly_raw_segment_fills_only_the_missing_seqs` — segment 1..5, raw 3..6, range 2..6: result seqs `2..6`, seq 2 from the segment, seqs 3..6 the raw objects (`is` identity), and `opened == [(1, 5)]`.
- `test_raw_wins_over_a_segment_copy_of_the_same_seq` — segment of events 1..2; raw holds `dataclasses.replace(events[1], payload={"raw": True})` for seq 2; range 1..2; result is `(events[0], that raw event)`.
- `test_a_damaged_segment_a_read_needs_is_loud` — raw 3..4, segment 1..2 with `data` replaced by `b"rotted"`; `pytest.raises(TierRecordError)` for range 1..4.
- `test_a_damaged_segment_a_read_does_not_need_is_not_opened` — the same damaged segment, range 3..4: returns raw 3..4, no error.
- `test_the_whole_project_bound_is_the_largest_bigint` — `LAST_SEQ == 9223372036854775807`; merging events 1..3 held only in a segment with `from_seq=1, to_seq=LAST_SEQ` returns all three.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Focused (no service is used by these tests; today the root conftest still opens the database at startup):
    uv run pytest -q -p no:cacheprovider tests/infrastructure/orm/test_tiered_events.py tests/infrastructure/ledger/test_segment_codec.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/infrastructure/*' --fail-under=100

## Out of scope
- `PostgresLedgerRepository` (`roadmap-114-tier-aware-reads-p3`); the segment store
  (`roadmap-114-postgres-tier-store-p4`); tier-aware ledger **search**
  (`ledger_search_repository.py`) and publication, which the rotation ADR schedules.
- The existing `TierManager.get_range` (its future is `roadmap-114-design-rotation`'s decision).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See /private/tmp/claude-501/storm/qwenstorm-3.0.0/SPEC-TEMPLATE.md.
