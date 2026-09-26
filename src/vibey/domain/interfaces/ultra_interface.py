# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind ULTRA (ADR-0063).

Mirrors `vibey/domain/ultra.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from uuid import UUID

    from vibey.domain.budget import BudgetLedger
    from vibey.domain.effort import Effort
    from vibey.domain.ledger import LedgerEvent
    from vibey.domain.ultra import UltraPass, UltraState, UltraVerdict


@runtime_checkable
class UltraPassInterface(Protocol):
    """One improvement pass of one work item, numbered from 1."""

    @property
    def work_item_id(self) -> str: ...

    @property
    def number(self) -> int: ...

    def next(self) -> UltraPass:
        """The pass after this one."""
        ...

    def job_key(self, project_id: UUID, cycle: int) -> str:
        """One job per (project, cycle, item, pass)."""
        ...


@runtime_checkable
class UltraPolicyInterface(Protocol):
    """Reads ULTRA's state from a ledger and decides each pass. Pure."""

    def state(self, events: Iterable[LedgerEvent]) -> UltraState:
        """The latest trusted start/stop and no-cap declaration."""
        ...

    def decide(self, state: UltraState, budget: BudgetLedger) -> UltraVerdict:
        """Stop, then the brake, then a missing cap without the declaration; else continue."""
        ...

    def effort(self, state: UltraState, ladder_effort: Effort) -> Effort:
        """ULTRA while the run is active, else the ladder's effort."""
        ...

    def pass_of(self, work_item_id: str, payload: Mapping[str, object]) -> UltraPass:
        """The pass a BUILD job's payload names; the first when it names none."""
        ...

    @staticmethod
    def phrase_matches(typed: str) -> bool:
        """Whether a person typed the no-cap phrase exactly."""
        ...

    @staticmethod
    def rate_per_hour(events: Iterable[LedgerEvent], engine_id: str | None = None) -> float | None:
        """Measured dollars per hour, or `None` when nothing was measured."""
        ...
