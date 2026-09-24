## Title
feat(ledger): a LedgerSegmentStore port with a registered in-memory fake and a contract suite

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, "Proposed child issues" 2: "The unit tests use
an in-memory fake so the default test run needs no service"). The existing tier store port
cannot be the seam for a PostgreSQL store: `LedgerTierStoreInterface`
(`src/vibey/infrastructure/ledger/interfaces/tier_store_interface.py:18-32`) is **synchronous**,
while every PostgreSQL access goes through the async `PostgresOrmInterface` (draft ADR
`specs/ADR-orm.md` §1); it trades bare bytes **per seq** (`:28-32`), not ranges; and its raw half
(`put_raw`, `remove_raw`, `:24-26`) would insert into and delete from `event`, which is
append-only (`migrations/0013_ledger_partitioning.sql:63-66`) — whether a raw row may ever leave
`event` is exactly what `roadmap-114-design-rotation` decides. So the segment half gets its own
async port, over the sealed-segment value of `roadmap-114-postgres-tier-store-p2`. It is an
**application** port (`src/vibey/application/interfaces/`), because the rotation job that will
write segments is an application handler, and `application/` may not import `infrastructure/`
(`.importlinter` `application-independence`). The operator's fakes standard (draft amendment
`specs/ADR-test-harness-fakes-amendment.md` A2) requires every port to have a registered,
comprehensive in-memory fake bound by the same contract suite as the real adapter (A5);
sub-doctrine 9.b (`src/vibey_tools/gh/docs/doctrines.md:349`) requires substitution at the
declared seam. The existing sync port and `TierManager` are left alone.

## Required behaviour
1. `src/vibey/application/interfaces/ledger_segments.py` (new):
   ```python
   """Sealed ledger segments (vibey#114): verified copies of contiguous runs of one project's
   events, stored once, never rewritten or removed, and read back by seq range."""

   from __future__ import annotations

   from typing import Protocol, runtime_checkable
   from uuid import UUID

   from vibey.domain.interfaces.ledger_segment_interface import LedgerSegmentInterface


   @runtime_checkable
   class LedgerSegmentStore(Protocol):
       """Where sealed segments live. The PostgreSQL store and the in-memory fake both
       satisfy `tests/contracts/test_ledger_segment_store_contract.py`."""

       async def put_segment(self, segment: LedgerSegmentInterface) -> None:
           """Store `segment`.

           Storing the same seal again (same project, range, codec and digest) is a no-op,
           so a replayed job is safe. A segment whose data does not hash to its digest raises
           `ValueError` ("does not hash to its digest") and stores nothing. Any other segment
           overlapping its range raises `LedgerSegmentConflict` and stores nothing: a sealed
           segment is never replaced.
           """
           ...

       async def segments(
           self, project_id: UUID, *, from_seq: int, to_seq: int
       ) -> tuple[LedgerSegmentInterface, ...]:
           """Every segment of `project_id` overlapping `from_seq`..`to_seq`, by first_seq."""
           ...

       async def segments_for_project(
           self, project_id: UUID
       ) -> tuple[LedgerSegmentInterface, ...]:
           """Every segment of `project_id`, by first_seq."""
           ...
   ```
2. `src/vibey/application/interfaces/__init__.py`: add
   `from vibey.application.interfaces.ledger_segments import LedgerSegmentStore` after the
   `from vibey.application.interfaces.ledger import (...)` block (`:90-101`), and
   `"LedgerSegmentStore",` to `__all__` right after `"LedgerReader",` (`:221`).
3. `tests/fakes/ledger_segments.py` (new) — `class InMemoryLedgerSegmentStore`, a plain class
   implementing `LedgerSegmentStore` with real in-memory behaviour:
   - `__init__(self) -> None`: `self._segments: dict[UUID, dict[int, LedgerSegmentInterface]] = {}`
     and `self._fail_next: BaseException | None = None`.
   - `fail_next_put(self, exc: BaseException) -> None`: the next `put_segment` raises `exc`
     and stores nothing (fault injection, as `fakes-ledger`'s `fail_next_append`).
   - `async put_segment(self, segment)`: if a fault is armed, clear it and raise it; if
     `not segment.intact`, raise
     `ValueError(f"ledger segment {segment.project_id}:{segment.first_seq}-{segment.last_seq} does not hash to its digest; refusing to store it")`;
     then for each held segment of that project that `overlaps(segment.first_seq, segment.last_seq)`:
     return if it `same_seal(segment)`, else raise
     `LedgerSegmentConflict(segment.project_id, segment.first_seq, segment.last_seq)`; with no
     overlap, store it under its `first_seq`.
   - `async segments(self, project_id, *, from_seq, to_seq)`: the held segments of the project
     that `overlaps(from_seq, to_seq)`, ordered by `first_seq`, as a tuple.
   - `async segments_for_project(self, project_id)`: all held segments of the project, ordered
     by `first_seq`, as a tuple (`()` for an unknown project).
   - No update, delete, remove or clear method (the store is append-only).
4. `tests/fakes/registry.py` (lane `fakes-registry`): import `LedgerSegmentStore` and
   `InMemoryLedgerSegmentStore`, and add
   `FakeRegistration(port=LedgerSegmentStore, build=InMemoryLedgerSegmentStore)` to `REGISTRY`.
   `LedgerSegmentStore` is an application port, so it goes in `REGISTRY`, not `DRIVER_SEAMS`;
   `test_every_application_port_is_accounted_for` then finds it registered.
5. `tests/contracts/test_ledger_segment_store_contract.py` (new) — the port's contract suite:
   - a frozen dataclass `SegmentStoreCase` with `store: LedgerSegmentStore`,
     `project_id: UUID`, `other_project_id: UUID`;
   - a fixture `case` with `params=["memory"]` (comment on the decorator:
     `# roadmap-114-postgres-tier-store-p4 widens this to backends() and adds "postgres"`),
     returning `SegmentStoreCase(InMemoryLedgerSegmentStore(), uuid4(), uuid4())` for
     `"memory"`;
   - a helper `_seal(project_id: UUID, first_seq: int, last_seq: int, data: bytes = b"sealed") -> LedgerSegment`
     returning `LedgerSegment.seal(project_id=project_id, first_seq=first_seq, last_seq=last_seq, codec="jsonl+zlib", data=data)`;
   - the tests below, using only the port's methods.

## Where to change
- `src/vibey/application/interfaces/ledger_segments.py` (new; line 1 is the provenance comment
  copied byte-for-byte from line 1 of `src/vibey/application/interfaces/ledger.py`).
- `src/vibey/application/interfaces/__init__.py` (`edit_file`, two insertions).
- `tests/fakes/ledger_segments.py`, `tests/fakes/test_fake_ledger_segments.py`,
  `tests/contracts/test_ledger_segment_store_contract.py` (new; same line 1).
- `tests/fakes/registry.py` (`edit_file`: two imports, one `REGISTRY` entry).

Standing constraints of every fakes lane (`specs/fakes-registry.md` "Lane card"): a fake is a
plain class with real behaviour for every port method; `unittest.mock` is never used under
`tests/fakes/`; no method body is only `...`, `pass`, `return None` or
`raise NotImplementedError`; substitution only at a declared seam; protected tests are never
edited.

## Acceptance criteria
- [ ] `isinstance(InMemoryLedgerSegmentStore(), LedgerSegmentStore)`; `tests/fakes/test_port_parity.py` passes, including `test_fake_signatures_match_the_port` and `test_fakes_are_not_stubs` for the new registration.
- [ ] `uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_ledger_segment_store_contract.py` runs every contract test on `memory` and passes with PostgreSQL stopped.
- [ ] `lint-imports` is green: the new port module imports only `vibey.domain` (contract `interfaces-declare-only`).
- [ ] `mypy --strict src/vibey` is clean; 100% branch coverage of `src/vibey/application/` (the port has no executable body beyond `...`).

## Tests to write first (TDD)
`tests/contracts/test_ledger_segment_store_contract.py` (every test takes the `case` fixture):
- `test_a_sealed_segment_reads_back_bit_for_bit` — put `_seal(pid, 1, 3)`; `segments_for_project(pid) == (segment,)` and the one read back has `data`, `digest`, `codec`, `first_seq`, `last_seq`, `project_id` equal to the original.
- `test_a_replayed_seal_is_a_no_op` — put the same segment twice; `segments_for_project(pid)` has length 1.
- `test_an_overlapping_different_segment_is_refused_and_nothing_is_stored` — put `_seal(pid, 1, 5)`; `_seal(pid, 3, 8)` and `_seal(pid, 1, 5, b"other")` each raise `LedgerSegmentConflict`; `segments_for_project(pid)` is still only the first.
- `test_segments_are_read_by_overlap_in_seq_order` — put `(6, 10)`, `(1, 5)`, `(11, 12)` in that order; `segments(pid, from_seq=4, to_seq=6)` is `(1-5, 6-10)`; `segments(pid, from_seq=13, to_seq=20) == ()`; `segments_for_project(pid)` is the three by `first_seq`.
- `test_another_projects_segments_are_invisible` — put `_seal(other, 1, 3)`; `segments_for_project(pid) == ()` and `segments(pid, from_seq=1, to_seq=3) == ()`.
- `test_a_segment_that_does_not_hash_to_its_digest_is_refused` — `LedgerSegment(project_id=pid, first_seq=1, last_seq=1, codec="jsonl+zlib", digest=hashlib.sha256(b"a").hexdigest(), data=b"b")`; `pytest.raises(ValueError, match="does not hash to its digest")`; nothing stored.

`tests/fakes/test_fake_ledger_segments.py` (what the contract does not cover):
- `test_a_failed_put_stores_nothing_and_the_next_put_succeeds` — `fail_next_put(RuntimeError("store down"))`; the put raises `RuntimeError`; `segments_for_project` is `()`; the same put then succeeds.
- `test_no_update_or_delete_is_offered` — `not hasattr(InMemoryLedgerSegmentStore, name)` for `update`, `delete`, `remove`, `clear`, `put_raw`, `remove_raw`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Default tier (no service):
    uv run pytest -q -p no:cacheprovider -m "not integration" tests/contracts/test_ledger_segment_store_contract.py tests/fakes tests/meta
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/application/*' --fail-under=100

## Out of scope
- The PostgreSQL store and the `postgres` backend of the contract (`roadmap-114-postgres-tier-store-p4`).
- The existing sync `LedgerTierStoreInterface`, `InMemoryLedgerTierStore` and `TierManager`
  (their future is `roadmap-114-design-rotation`'s decision).
- Wiring anything into `bootstrap.py`.
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
