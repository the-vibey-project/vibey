# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""FullLedger writer: <worktree>/.vibey/handoff/ledger.jsonl, one JSON
object per line ordered by seq -- the complete, unabridged history handed
to every receiving engine (handoff-protocol.md §4.1). The digest in the
returned LedgerRef is exactly domain.ledger.digest_range(events), so R6 of
the no-loss gate can verify the file on disk against the ref without
re-reading the database."""

import json
from collections.abc import Sequence
from pathlib import Path
from typing import Final

from vibey.domain.handoff import LedgerRef
from vibey.domain.interfaces.ledger_record_interface import LedgerRecordCodecInterface
from vibey.domain.ledger import LedgerEvent, digest_range
from vibey.domain.ledger_record import LEDGER_RECORDS, InvalidLedgerRecord
from vibey.infrastructure.ledger.interfaces.full_ledger_writer_interface import (
    LedgerLinesInterface,
)


class LedgerLines:
    """One ledger event per line of JSON, and back.

    The object on each line is the shared ledger record (domain/ledger_record.py);
    this class adds only the line: keys sorted, no whitespace, so the same event
    always writes the same bytes. The handoff ledger and the published shard
    (`vibey ledger export`) both write through it, so the two cannot drift.
    """

    def __init__(self, records: LedgerRecordCodecInterface = LEDGER_RECORDS) -> None:
        self._records = records

    def encode(self, event: LedgerEvent) -> str:
        return json.dumps(self._records.to_fields(event), sort_keys=True, separators=(",", ":"))

    def decode(self, line: str) -> LedgerEvent:
        try:
            fields = json.loads(line, parse_constant=self._refuse_constant)
        except json.JSONDecodeError as exc:
            raise InvalidLedgerRecord(f"not JSON: {exc.msg}") from exc
        if not isinstance(fields, dict):
            raise InvalidLedgerRecord("a record line must be a JSON object")
        return self._records.from_fields(fields)

    @staticmethod
    def _refuse_constant(name: str) -> object:
        # Python's json reads NaN and Infinity, which no other JSON reader
        # accepts; a record carrying one could never be served back out.
        raise InvalidLedgerRecord(f"{name} is not a JSON number")


LEDGER_LINES: Final[LedgerLinesInterface] = LedgerLines()
"""The line codec every ledger file shares. Annotated with the interface so `mypy
--strict` checks the class against its declared seam."""


def write_full_ledger(
    events: Sequence[LedgerEvent], path: Path, *, uri: str = "handoff/ledger.jsonl"
) -> LedgerRef:
    ordered = sorted(events, key=lambda e: e.seq)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for event in ordered:
            f.write(LEDGER_LINES.encode(event) + "\n")

    if not ordered:
        return LedgerRef(uri=uri, from_seq=0, to_seq=0, event_count=0, digest=digest_range(()))

    return LedgerRef(
        uri=uri,
        from_seq=ordered[0].seq,
        to_seq=ordered[-1].seq,
        event_count=len(ordered),
        digest=digest_range(ordered),
    )


def read_full_ledger_line_count(path: Path) -> int:
    """A cheap sanity check used by tests and `vibey doctor`: the file's
    line count should equal the ref's event_count."""
    with path.open() as f:
        return sum(1 for line in f if line.strip())
