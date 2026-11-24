# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind an engine session's own client to the hub (SP-LOOPS Phase 6, Task 4).

Mirrors `vibey/infrastructure/web/session_hub_client.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import WebSearchAnswer
    from vibey.infrastructure.web.fetch import FetchedPage


@runtime_checkable
class SessionHubClientInterface(Protocol):
    """Search and fetch through the hub with the session's own token, read afresh each call."""

    def search(self, query: str, limit: int | None) -> WebSearchAnswer:
        """The hub's answer to `query`; `limit` None leaves it to the hub. Raises
        `SessionHubError`, whose `kind` says why, never with the token in it."""
        ...

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        """The page at `url` as the hub framed it; `max_chars` cuts the page's own words inside
        the frame, never the frame. Raises `SessionHubError`."""
        ...
