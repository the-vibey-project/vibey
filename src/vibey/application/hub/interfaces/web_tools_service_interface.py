# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's web tools and the three seams they stand on (ADR-0102, SP-ACP Task 9b).

Mirrors `vibey/application/hub/web_tools_service.py` (ADR-0016). Interfaces declare; they never
consume. The search, fetch and audit seams are implemented in infrastructure: the hub process's
own local-first search (it holds the Brave key), the guarded fetch, and the ledger.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.application.dto import HubPrincipal, WebPage, WebSearchAnswer
    from vibey.domain.ledger import EventKind
    from vibey.domain.web_tools import WebTarget, WebToolSettings


@runtime_checkable
class WebToolsServiceInterface(Protocol):
    """Search and fetch for a principal holding `web`: bounded, budgeted and recorded."""

    async def search(
        self,
        principal: HubPrincipal,
        query: str,
        *,
        limit: int | None = None,
        project_id: UUID | None = None,
    ) -> dict[str, object]:
        """The results, framed as untrusted, and the backend that answered. Raises
        `HubForbidden`, `WebToolRefused`, `WebBudgetExhausted`, `WebToolUnavailable` or
        `WebToolFailed`; none of them, and no record, carries the query."""
        ...

    async def fetch(
        self, principal: HubPrincipal, url: str, *, project_id: UUID | None = None
    ) -> dict[str, object]:
        """One public page as text inside a marked untrusted block. Raises as `search` does;
        the record names the hosts reached, never the URL."""
        ...


@runtime_checkable
class WebSearchPortInterface(Protocol):
    """The hub process's own local-first search: SearXNG first, Brave only as its backup."""

    async def search(self, query: str, limit: int | None) -> WebSearchAnswer:
        """The answer, or `WebToolFailed` (naming the backends asked, never the query), or
        `WebToolUnavailable` when the hub's environment sets search up wrongly."""
        ...


@runtime_checkable
class WebFetchPortInterface(Protocol):
    """A guarded fetch of one page: connects only to checked public addresses."""

    async def fetch(
        self, target: WebTarget, settings: WebToolSettings, reached: list[str] | None = None
    ) -> WebPage:
        """The page, or `WebToolRefused` / `WebToolFailed` carrying the hosts reached. Each host
        is added to `reached`, when given, as the fetch reaches it, so the caller knows where the
        fetch went whatever fails afterwards."""
        ...


@runtime_checkable
class WebAuditPortInterface(Protocol):
    """Where each use is recorded: the named project's ledger, else every project's."""

    async def ready(self, project_id: UUID | None) -> None:
        """Return when a record can be written; raise `UnknownProject` for a project that does
        not exist, or `WebToolUnavailable` when there is no ledger to write it to."""
        ...

    async def record(
        self,
        kind: EventKind,
        payload: Mapping[str, object],
        at: datetime,
        project_id: UUID | None,
    ) -> int:
        """Append the record; the number of ledgers it was written to."""
        ...
