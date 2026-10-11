# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for one web search backend (SearXNG, Brave)."""

from typing import Protocol, runtime_checkable

from vibey.infrastructure.web.search import SearchHit


@runtime_checkable
class SearchBackendInterface(Protocol):
    """Answers one query with up to `limit` hits, or raises `WebSearchError`."""

    name: str

    def search(self, query: str, limit: int) -> list[SearchHit]:
        """The hits for `query`, best first."""
        ...
