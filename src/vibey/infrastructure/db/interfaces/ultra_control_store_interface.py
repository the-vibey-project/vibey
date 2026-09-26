# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/db/ultra_control_store.py` (ADR-0016). Interfaces
declare; they never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.ledger import EventKind


@runtime_checkable
class PostgresUltraControlStoreInterface(Protocol):
    """Appends one trusted ULTRA control event under the project's row lock."""

    async def record(
        self,
        project_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
        *,
        at: datetime,
    ) -> None:
        """Raises `ValueError` for a kind that is not an ULTRA control, `UnknownProject`
        for no such project, `WrongPhase` for a phase this vibey does not know."""
        ...
