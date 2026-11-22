# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the hub's own local-first search.

Mirrors `vibey/infrastructure/web/hub_search.py` (ADR-0016). Interfaces declare; they never
consume. It fills the application's `WebSearchPortInterface`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import WebSearchAnswer


@runtime_checkable
class HubWebSearchInterface(Protocol):
    """SearXNG first, Brave only as its backup, with the hub process's own settings."""

    async def search(self, query: str, limit: int | None) -> WebSearchAnswer:
        """The answer and its backend, or `WebToolFailed` naming the backends asked, or
        `WebToolUnavailable` when the hub's environment sets search up wrongly."""
        ...
