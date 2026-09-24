"""A long measurement keeps each step as it finishes, and a restart runs only the rest (10.h).

    journal = StepJournal(Path("bench/host-sweep.jsonl"))
    for step in journal.pending(["A", "B", "C"]):
        journal.record(step, measure(step))     # on disk before the next step starts

WHY
---
The concurrency sweep lost on 2026-09-24 held its rows in memory and printed them once, at the
end. The llama-server benchmark truncated its results file every time it started. Either way,
one reboot, kill or crash cost the whole run, and a run that takes an hour and a half is
exactly the one most likely to meet one. ADR-0057.

THE FILE
--------
One JSON object per line, appended and never rewritten (the storm's ledgers work the same way,
7.c):

    {"step": "C", "recorded_at": "2026-09-24T14:02:11Z", ...the step's own fields...}

`record` writes the line, flushes it and fsyncs it before it returns. The first write also
fsyncs the directory, so the file's own entry survives a power cut. A step recorded twice
reads as its latest line, because a re-measurement is a newer fact and the older line stays
as history.

A process killed in the middle of a write leaves part of a line. That fragment is not a
finished step: `done` skips it and `torn` counts it. Before the next record, `record` ends the
fragment with a newline, so it cannot join onto the following line and spoil that one as well.

Where the journal lives is the caller's choice, and it must be durable: a journal under /tmp is
lost at the same moment as the work it was meant to save. Callers put it through
`storm_durability.DurabilityGate` first.

Underscored, not hyphenated: it is imported.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class StepJournal:
    """An append-only file of finished steps, which a restarted measurement resumes from."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def _lines(self) -> tuple[dict[str, dict[str, Any]], int]:
        done: dict[str, dict[str, Any]] = {}
        torn = 0
        if not self.path.is_file():
            return done, torn
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                torn += 1
                continue
            if isinstance(row, dict) and isinstance(row.get("step"), str):
                done[row["step"]] = row
            else:
                torn += 1
        return done, torn

    def done(self) -> dict[str, dict[str, Any]]:
        """Every recorded step, by name, as its latest row."""
        return self._lines()[0]

    def torn(self) -> int:
        """How many lines are not a finished step: fragments of a write a crash cut short."""
        return self._lines()[1]

    def pending(self, steps: Iterable[str]) -> list[str]:
        """The steps, in the order given, that are not yet recorded."""
        finished = self.done()
        return [step for step in steps if step not in finished]

    def record(self, step: str, row: Mapping[str, Any]) -> None:
        """Append one finished step, durably, before returning."""
        if "step" in row or "recorded_at" in row:
            raise ValueError("a row may not set 'step' or 'recorded_at'; the journal does")
        line = json.dumps(
            {
                "step": step,
                "recorded_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                **row,
            },
            sort_keys=False,
        )
        created = not self.path.exists()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a+b") as handle:
            handle.seek(0, os.SEEK_END)
            if handle.tell() > 0:
                handle.seek(-1, os.SEEK_END)
                if handle.read(1) != b"\n":
                    # The tail of a write a crash cut short: end it here, so it stays a
                    # fragment of its own rather than the start of this record.
                    handle.write(b"\n")
            handle.write(line.encode("utf-8") + b"\n")
            handle.flush()
            os.fsync(handle.fileno())
        if created:
            directory = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
