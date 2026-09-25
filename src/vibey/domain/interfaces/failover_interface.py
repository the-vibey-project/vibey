# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind failover and handback (ADR-0070).

Mirrors `vibey/domain/failover.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping, Sequence
    from datetime import datetime

    from vibey.domain.capacity import CapacityState
    from vibey.domain.failover import (
        FailoverPlan,
        FailoverRecord,
        FailoverSettings,
        FailoverStatus,
    )


@runtime_checkable
class CapacitySignalClassifierInterface(Protocol):
    """Maps a Claude Code `StopFailure` error type onto a capacity state."""

    def classify(self, error: str, detail: str = "") -> CapacityState: ...


@runtime_checkable
class FailoverPolicyInterface(Protocol):
    """Plans failovers and reads their state from records. Pure."""

    def plan(
        self, state: CapacityState, *, now: datetime, settings: FailoverSettings
    ) -> FailoverPlan | None:
        """A failover for a capacity rejection; None for anything else or when off."""
        ...

    def status(self, records: Iterable[FailoverRecord]) -> FailoverStatus:
        """The latest failover and the first successful probe recorded after it."""
        ...

    def outranks_completion(self, capacity: CapacityState) -> bool:
        """Whether this state overrides a completion claimed in the same turn."""
        ...

    def read_rows(self, rows: Sequence[Mapping[str, object]]) -> tuple[FailoverRecord, ...]:
        """Stored rows as records; unknown kinds are skipped."""
        ...
