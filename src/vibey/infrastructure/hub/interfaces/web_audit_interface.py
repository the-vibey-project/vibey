# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind recording the hub's web tools on the ledger.

Mirrors `vibey/infrastructure/hub/web_audit.py` (ADR-0016). Interfaces declare; they never
consume. It fills the application's `WebAuditPortInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.domain.ledger import EventKind


@runtime_checkable
class WebAuditInterface(Protocol):
    """Records a web search or fetch on the named project's ledger, else on every project's."""

    async def ready(self, project_id: UUID | None) -> None:
        """Return when a record can be written, else raise (`UnknownProject`,
        `WebToolUnavailable`)."""
        ...

    async def record(
        self,
        kind: EventKind,
        payload: Mapping[str, object],
        at: datetime,
        project_id: UUID | None,
    ) -> int:
        """Append the record in one transaction; the number of ledgers written."""
        ...
