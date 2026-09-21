# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Documentation port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class DocsPort(Protocol):
    """Common protocol for documentation platforms."""

    async def create_page(self, title: str, content: str) -> str:
        """Create a documentation page and return its page identifier."""
        ...

    async def update_page(self, page_id: str, content: str) -> None:
        """Update the content of an existing documentation page."""
        ...
