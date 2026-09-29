# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam between a research gap and the DESIGN ledger that records it.

Mirrors `vibey/application/research_gaps.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

# Imported at runtime, not under TYPE_CHECKING: the seam's annotations must resolve
# (tests/application/test_interfaces_convention.py), and both are a seam's vocabulary.
from vibey.application.design import DesignEvent
from vibey.domain.research_gap import ResearchGap


@runtime_checkable
class ResearchGapRecordsInterface(Protocol):
    """Writes a research gap as a ledger event, and reads a cycle's gaps back."""

    def event(self, gap: ResearchGap, *, now: datetime, cycle: int) -> DesignEvent:
        """The `ResearchGapRecorded` event for one gap: vibey's own words, so trusted."""
        ...

    def gaps(self, events: Sequence[DesignEvent], *, cycle: int) -> tuple[ResearchGap, ...]:
        """The cycle's recorded gaps, one per topic, in the order they were recorded."""
        ...
