# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/db/failover_store.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.ledger import EventKind


@runtime_checkable
class PostgresFailoverStoreInterface(Protocol):
    async def record(
        self,
        project_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
        *,
        at: datetime,
    ) -> None: ...
