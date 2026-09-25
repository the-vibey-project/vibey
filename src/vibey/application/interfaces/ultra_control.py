# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ULTRA's seams (ADR-0063): the store that records the operator's controls, and the one
service every host entry point starts, stops and declares through.

Mirrors `vibey/application/ultra_control.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import UltraStatus
from vibey.domain.ledger import EventKind


@runtime_checkable
class UltraControlStore(Protocol):
    """Appends one trusted ULTRA control event."""

    async def record(
        self,
        project_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
        *,
        at: datetime,
    ) -> None: ...


@runtime_checkable
class UltraControlServiceInterface(Protocol):
    """Starts and stops a project's ULTRA run and declares or withdraws no cap."""

    async def status(self, project_id: UUID) -> UltraStatus:
        """Raises `UnknownProject` for no such project."""
        ...

    async def start(self, project_id: UUID, *, by: str | None = None) -> UltraStatus: ...

    async def stop(self, project_id: UUID, *, by: str | None = None) -> UltraStatus:
        """Binds at the next pass boundary. One action, always available."""
        ...

    async def declare_no_cap(
        self, project_id: UUID, *, phrase: str, by: str | None = None
    ) -> UltraStatus:
        """Raises `InvalidBudgetChange` unless `phrase` is the no-cap phrase exactly. The
        warnings are the caller's to show first; this records the declaration."""
        ...

    async def keep_cap(self, project_id: UUID, *, by: str | None = None) -> UltraStatus:
        """Withdraws the declaration. One action, binding at the next pass."""
        ...
