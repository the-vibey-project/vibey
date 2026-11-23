# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ledger, not the store, decides what a run is given (SP-LOOPS Phase 3c, fix round 1:
review I2, I3).

A store's index rows can be written by anyone who can write the store -- another writer of a
shared bucket, a person editing `index.jsonl`. The ledger is append-only and written only by
vibey. So a run is given exactly the rows that match a recorded add, one row per add, compared on
everything the ledger records: digest, kind, size and -- for adds recorded since names were -- the
SHA-256 of the name (the ledger holds digests and sizes only, never a name). The order is the
ledger's, not the store's, so a planted older row cannot roll a file back and clock skew between
writers cannot reorder adds. A row no add takes is withheld and counted; an add no row matches is
missing, and the run fails naming it -- unless a `vibey_run_input_failed` correction cancels it,
which the service appends when an add's row could not be written after its record.

Pure: no I/O. Declared by `interfaces/input_ledger_interface.py::InputLedgerInterface`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Final

from vibey.domain.interfaces.input_ledger_interface import InputLedgerInterface
from vibey.domain.run_input import INPUT_KINDS, RUN_INPUT_RULE, InputKind, RunInput

ADDED_ARTIFACT_TYPE: Final = "vibey_run_input"
FAILED_ARTIFACT_TYPE: Final = "vibey_run_input_failed"
"""A correction: the add recorded with these fields never got its index row."""


@dataclass(frozen=True, slots=True)
class RecordedInput:
    """One add as the ledger records it. `name_digest` is None for an add recorded before
    names were, which matches a row of any name."""

    seq: int
    digest: str
    kind: InputKind
    size: int
    name_digest: str | None

    def matches(self, row: RunInput) -> bool:
        return (
            row.digest == self.digest
            and row.kind == self.kind
            and row.size == self.size
            and (
                self.name_digest is None or RUN_INPUT_RULE.name_digest(row.name) == self.name_digest
            )
        )

    def same_input(self, other: RecordedInput) -> bool:
        return (self.digest, self.kind, self.size, self.name_digest) == (
            other.digest,
            other.kind,
            other.size,
            other.name_digest,
        )

    def describe(self) -> str:
        return f"{self.kind} {self.digest} ({self.size} bytes)"


@dataclass(frozen=True, slots=True)
class RecordedInputs:
    """The live adds, in ledger order: every add a failure correction has not cancelled."""

    added: tuple[RecordedInput, ...]


@dataclass(frozen=True, slots=True)
class Reconciled:
    given: tuple[RunInput, ...]
    unrecorded: int
    missing: tuple[RecordedInput, ...]


class InputLedger:
    """Declared by `interfaces/input_ledger_interface.py::InputLedgerInterface`."""

    def recorded(self, events: Iterable[tuple[int, Mapping[str, object]]]) -> RecordedInputs:
        adds: list[RecordedInput] = []
        for seq, payload in sorted(events, key=lambda pair: pair[0]):
            record = self._parse(seq, payload)
            if record is None:
                continue
            if payload.get("artifact_type") == ADDED_ARTIFACT_TYPE:
                adds.append(record)
                continue
            cancelled = next(
                (i for i in range(len(adds) - 1, -1, -1) if adds[i].same_input(record)), None
            )
            if cancelled is not None:
                del adds[cancelled]
        return RecordedInputs(added=tuple(adds))

    def reconcile(self, rows: Sequence[RunInput], recorded: RecordedInputs) -> Reconciled:
        used: set[int] = set()
        given: list[RunInput] = []
        missing: list[RecordedInput] = []
        for add in recorded.added:
            index = next(
                (i for i, row in enumerate(rows) if i not in used and add.matches(row)), None
            )
            if index is None:
                missing.append(add)
            else:
                used.add(index)
                given.append(rows[index])
        return Reconciled(
            given=tuple(given), unrecorded=len(rows) - len(used), missing=tuple(missing)
        )

    @staticmethod
    def _parse(seq: int, payload: Mapping[str, object]) -> RecordedInput | None:
        if payload.get("artifact_type") not in (ADDED_ARTIFACT_TYPE, FAILED_ARTIFACT_TYPE):
            return None
        digest, kind, size = payload.get("digest"), payload.get("kind"), payload.get("size")
        name_digest = payload.get("name_digest")
        if not (isinstance(digest, str) and RUN_INPUT_RULE.is_digest(digest)):
            return None
        if kind not in INPUT_KINDS:
            return None
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            return None
        if name_digest is not None and not (
            isinstance(name_digest, str) and RUN_INPUT_RULE.is_digest(name_digest)
        ):
            return None
        return RecordedInput(
            seq=seq,
            digest=digest,
            kind=kind,
            size=size,
            name_digest=name_digest,
        )


INPUT_LEDGER: Final[InputLedgerInterface] = InputLedger()
"""The one rule. Annotated with the interface so `mypy --strict` checks the class against it."""
