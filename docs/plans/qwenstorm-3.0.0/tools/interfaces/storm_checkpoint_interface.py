"""What a step journal promises, declared beside `storm_checkpoint.py` (sub-doctrine 9.b).

Declares; never consumes. `tests/meta/test_storm_checkpoint.py` holds the implementation to
it, so the declaration cannot drift from the class it describes.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class StepJournalInterface(Protocol):
    """An append-only file of finished steps, which a restarted measurement resumes from."""

    path: Path

    def done(self) -> dict[str, dict[str, Any]]:
        """Every recorded step, by name, as its latest row."""
        ...

    def torn(self) -> int:
        """How many lines are not a finished step: fragments of a write a crash cut short."""
        ...

    def pending(self, steps: Iterable[str]) -> list[str]:
        """The steps, in the order given, that are not yet recorded."""
        ...

    def record(self, step: str, row: Mapping[str, Any]) -> None:
        """Append one finished step, flushed and fsynced, before returning."""
        ...
