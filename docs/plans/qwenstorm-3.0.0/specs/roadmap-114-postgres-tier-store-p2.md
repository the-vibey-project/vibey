## Title
feat(domain): a sealed ledger segment is a value that knows its range, its codec and whether its bytes still hash to its digest

## Why
Issue #114 (rewrite: `issue-audit/updates/114.md`, Scope 3 "Chunks are content-addressed …
Archive verification is a hash walk with no decompression", and "Proposed child issues" 2).
The PostgreSQL tier store (`roadmap-114-postgres-tier-store-p4`), its in-memory fake (`-p3`) and
the tier-aware reads (`roadmap-114-tier-aware-reads-*`) all pass one thing around: a *sealed
segment*, one verified copy of a contiguous run of one project's events, as stored in
`ledger_segment` (`migrations/0016_ledger_segment.sql`, lane `-p1`: `project_id`, `first_seq`,
`last_seq`, `codec`, `digest` = SHA-256 of `data`, `data`). Today there is no such value: the
tier store port trades bare `bytes` per seq (`src/vibey/infrastructure/ledger/interfaces/tier_store_interface.py:28-32`),
so range, codec and integrity live nowhere. The value is pure — `hashlib` is already how the
domain digests (`src/vibey/domain/ledger.py:209-224`) — so it lives in `domain/`, with its
interface beside it (sub-doctrine 9.b, `src/vibey_tools/gh/docs/doctrines.md:349`; ADR-0016).
Sub-doctrine 7.c (`doctrines.md:82-91`) is why a segment is never replaced: "completeness grows
by new events, never by rewriting old ones".

## Required behaviour
1. `src/vibey/domain/ledger_segment.py` (new), with this module docstring and content:
   ```python
   """A sealed ledger segment: one verified copy of a contiguous run of one project's events
   (vibey#114).

   The storage tiers keep older events as segments. A segment names its `codec` -- the whole
   encoding of `data`, so a reader knows how to open it -- and carries `digest`, the SHA-256
   of `data` exactly as stored. `intact` recomputes that hash, so a segment is checked
   without decompressing it. What `data` holds is the codec's business; this value guards
   only the range, the codec name and the digest.
   """

   import hashlib
   from dataclasses import dataclass
   from typing import Self
   from uuid import UUID

   from vibey.domain.errors import VibeyError
   from vibey.domain.interfaces.ledger_segment_interface import LedgerSegmentInterface


   class LedgerSegmentConflict(VibeyError):
       """A different sealed segment already holds part of this seq range.

       An exception type, so it has no interface beside it: a `Protocol` cannot be raised or
       caught, and the seam an error crosses is its type.
       """

       def __init__(self, project_id: UUID, first_seq: int, last_seq: int) -> None:
           self.project_id = project_id
           self.first_seq = first_seq
           self.last_seq = last_seq
           super().__init__(
               f"ledger segment {project_id}:{first_seq}-{last_seq} overlaps a different "
               "sealed segment; a sealed segment is never replaced"
           )


   @dataclass(frozen=True, slots=True)
   class LedgerSegment:
       """Seqs `first_seq`..`last_seq` of one project, sealed under `codec`."""

       project_id: UUID
       first_seq: int
       last_seq: int
       codec: str
       digest: str
       data: bytes

       def __post_init__(self) -> None:
           if self.first_seq < 1 or self.last_seq < self.first_seq:
               raise ValueError(
                   "a ledger segment covers first_seq >= 1 through last_seq >= first_seq, "
                   f"not {self.first_seq}-{self.last_seq}"
               )
           if not self.codec:
               raise ValueError("a ledger segment names its codec")

       @classmethod
       def seal(
           cls, *, project_id: UUID, first_seq: int, last_seq: int, codec: str, data: bytes
       ) -> Self:
           """The segment for `data`, its digest computed here and nowhere else."""
           return cls(
               project_id=project_id,
               first_seq=first_seq,
               last_seq=last_seq,
               codec=codec,
               digest=hashlib.sha256(data).hexdigest(),
               data=data,
           )

       @property
       def record_count(self) -> int:
           return self.last_seq - self.first_seq + 1

       @property
       def intact(self) -> bool:
           """True while `data` still hashes to `digest`. Needs no decompression."""
           return hashlib.sha256(self.data).hexdigest() == self.digest

       def overlaps(self, first_seq: int, last_seq: int) -> bool:
           """True when any seq of `first_seq`..`last_seq` (inclusive) is in this segment."""
           return self.first_seq <= last_seq and first_seq <= self.last_seq

       def same_seal(self, other: LedgerSegmentInterface) -> bool:
           """Same project, range, codec and digest: storing `other` again is a replay."""
           return (
               self.project_id,
               self.first_seq,
               self.last_seq,
               self.codec,
               self.digest,
           ) == (other.project_id, other.first_seq, other.last_seq, other.codec, other.digest)
   ```
   The digest is **not** checked in `__post_init__`: a row whose bytes rotted must still be
   representable, so `intact` can report it and a reader can refuse it loudly.
2. `src/vibey/domain/interfaces/ledger_segment_interface.py` (new), in the style of
   `src/vibey/domain/interfaces/ledger_chain_interface.py:1-34` (docstring "Mirrors
   `vibey/domain/ledger_segment.py` (ADR-0016). Interfaces declare; they never consume.";
   `UUID` under `TYPE_CHECKING`): `@runtime_checkable class LedgerSegmentInterface(Protocol)`
   with read-only properties `project_id -> UUID`, `first_seq -> int`, `last_seq -> int`,
   `codec -> str`, `digest -> str`, `data -> bytes`, `record_count -> int`, `intact -> bool`,
   and methods `overlaps(self, first_seq: int, last_seq: int) -> bool` and
   `same_seal(self, other: LedgerSegmentInterface) -> bool`, each with a one-line docstring
   copied from the class above.
3. `src/vibey/domain/interfaces/__init__.py`: import `LedgerSegmentInterface` beside the
   `ledger_tier_interface` import (`:32-35`) and add `"LedgerSegmentInterface"` to `__all__`
   next to `"LedgerTierManagerInterface"` if present, else after `"LedgerRecordCodecInterface"`.

## Where to change
- `src/vibey/domain/ledger_segment.py` (new; line 1 is the provenance comment copied
  byte-for-byte from line 1 of `src/vibey/domain/ledger_tier.py`).
- `src/vibey/domain/interfaces/ledger_segment_interface.py` (new; same line 1).
- `src/vibey/domain/interfaces/__init__.py` (`edit_file`, two insertions).
- `tests/domain/test_ledger_segment.py` (new; same line 1).

## Acceptance criteria
- [ ] `isinstance(LedgerSegment.seal(...), LedgerSegmentInterface)`.
- [ ] `LedgerSegment.seal(..., data=b"abc").digest == hashlib.sha256(b"abc").hexdigest()` and the segment is `intact`.
- [ ] A segment whose `data` no longer matches its `digest` is constructible and not `intact`.
- [ ] `tests/domain/test_domain_purity.py` passes (no I/O, no async, no clock in the new module).
- [ ] `mypy --strict src/vibey` is clean; 100% branch coverage of `src/vibey/domain/`.

## Tests to write first (TDD)
`tests/domain/test_ledger_segment.py` (no service). Constant `PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000114")`;
helper `_segment(first_seq: int = 1, last_seq: int = 3, data: bytes = b"sealed") -> LedgerSegment`
returning `LedgerSegment.seal(project_id=PROJECT, first_seq=first_seq, last_seq=last_seq, codec="jsonl+zlib", data=data)`:
- `test_a_segment_is_its_declared_seam` — `isinstance(_segment(), LedgerSegmentInterface)`.
- `test_sealing_records_the_sha256_of_the_stored_bytes` — `digest == hashlib.sha256(b"sealed").hexdigest()`, `intact is True`, `record_count == 3`.
- `test_a_segment_whose_bytes_changed_is_not_intact` — `dataclasses.replace(_segment(), data=b"rotted").intact is False`.
- `test_a_range_below_one_or_running_backwards_is_refused` — parametrize `(0, 1)`, `(5, 4)`; `pytest.raises(ValueError, match="first_seq >= 1")`.
- `test_a_segment_names_its_codec` — `LedgerSegment.seal(project_id=PROJECT, first_seq=1, last_seq=1, codec="", data=b"x")` raises `ValueError` matching `names its codec`.
- `test_overlap_is_inclusive_at_both_ends` — for `_segment(3, 5)`: `overlaps(5, 9)`, `overlaps(1, 3)`, `overlaps(4, 4)` are True; `overlaps(6, 9)`, `overlaps(1, 2)` are False.
- `test_the_same_seal_is_a_replay_and_a_different_one_is_not` — `_segment().same_seal(_segment())` is True; `_segment().same_seal(_segment(data=b"other"))`, `_segment().same_seal(_segment(1, 4))` are False.
- `test_the_conflict_names_the_project_and_the_range` — `str(LedgerSegmentConflict(PROJECT, 1, 3))` contains `f"{PROJECT}:1-3"` and `never replaced`; its `first_seq == 1`, `last_seq == 3`, and it is a `VibeyError`.

## Checks the lane must run (all must pass)
    uv run ruff check . && uv run ruff format --check .
    uv run mypy --strict src/vibey
    uv run lint-imports
    export VIBEY_TEST_DATABASE_URL="${VIBEY_TEST_DATABASE_URL:-postgresql://$USER@localhost:5432/vibey_test}"
    export VIBEY_PG_URL="$VIBEY_TEST_DATABASE_URL"
    # Focused (no service is used by these tests; today the root conftest still opens the database at startup):
    uv run pytest -q -p no:cacheprovider tests/domain/test_ledger_segment.py tests/domain/test_domain_purity.py
    uv run pytest -q -p no:cacheprovider --cov=vibey --cov-branch --cov-report=
    uv run coverage report --include='src/vibey/domain/*' --fail-under=100

## Out of scope
- The store port and its fake (`roadmap-114-postgres-tier-store-p3`), the PostgreSQL store
  (`-p4`), the segment codec (`roadmap-114-tier-aware-reads-p1`).
- The content address and the chain links a segment may later carry
  (`roadmap-114-design-codec-chunking` decides them).
- The existing `LedgerTierStoreInterface`, `InMemoryLedgerTierStore` and `TierManager` (the
  rotation ADR decides their future).
- CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md and the four agent-surface trees.
  Do not push, no PRs, no remote changes; commit locally with the Title.

## Hard repository rules (always)
See STORM/SPEC-TEMPLATE.md.
