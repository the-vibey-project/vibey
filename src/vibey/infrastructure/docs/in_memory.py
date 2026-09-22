# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Docs implementation of the Documentation port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.docs import DocsPort


class InMemoryDocs(DocsPort):
    """Faked documentation store for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.pages: dict[str, dict[str, str]] = {}
        self._next_id = 1

    async def create_page(self, title: str, content: str) -> str:
        page_id = str(self._next_id)
        self._next_id += 1
        self.pages[page_id] = {"title": title, "content": content}
        return page_id

    async def update_page(self, page_id: str, content: str) -> None:
        if page_id not in self.pages:
            raise KeyError(f"page {page_id} not found")
        self.pages[page_id]["content"] = content
