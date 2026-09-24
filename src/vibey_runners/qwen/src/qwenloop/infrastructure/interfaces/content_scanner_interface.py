# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for searching the text of files a tool call has already confined."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class ContentScannerInterface(Protocol):
    """Matches lines, and reports every candidate file it could not search and why."""

    def scan(
        self, candidates: Sequence[tuple[str, str]], pattern: str, flags: int, limit: int
    ) -> dict[str, object]:
        """`matches`, `count`, `truncated` and `complete`; plus `skipped` and `note` when a
        candidate was too large, binary, not UTF-8 or unreadable."""
        ...
