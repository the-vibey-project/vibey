# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for web search and fetch tools."""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable


@runtime_checkable
class WebSearchInterface(Protocol):
    """Protocol for web search operations."""

    async def search(self, query: str, limit: int = 5) -> dict[str, object]:
        """Perform a web search for `query` up to `limit` results."""
        ...

    async def fetch(self, url: str) -> dict[str, object]:
        """Fetch the text content of `url`."""
        ...


@runtime_checkable
class WebSearchToolInterface(Protocol):
    """Protocol for model-invoked web search and fetch tool dispatch."""

    async def execute(self, name: str, arguments: Mapping[str, object]) -> dict[str, object]:
        """Execute web_search or web_fetch with model-provided arguments."""
        ...
