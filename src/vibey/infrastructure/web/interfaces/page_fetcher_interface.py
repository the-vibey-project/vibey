# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind reading one page as text through the guarded fetch.

Mirrors `vibey/infrastructure/web/page_fetcher.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.web.fetch import FetchedPage


@runtime_checkable
class PageFetcherInterface(Protocol):
    """One public page as plain text, never weaker than the hub's own fetch."""

    def fetch(self, url: str, *, max_chars: int | None = None) -> FetchedPage:
        """The page at `url`; `max_chars` may lower `[web] max_chars`, never raise it. Raises
        `WebFetchError` when it is refused or cannot be read."""
        ...
