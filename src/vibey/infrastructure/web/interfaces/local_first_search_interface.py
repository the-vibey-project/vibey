# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `web/local_first.py` (ADR-0016). Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable

from vibey.infrastructure.web.search import SearchAnswer


@runtime_checkable
class LocalFirstSearchInterface(Protocol):
    """Answers a query from the local SearXNG, or from the Brave backup only when SearXNG failed
    and a key is configured; raises `WebSearchError` when neither answered."""

    def answer(self, query: str, limit: int) -> SearchAnswer:
        """Up to `limit` hits for `query`, best first, and which backend answered."""
        ...
