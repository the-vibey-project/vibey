# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over plugin text bound for a model context or a terminal (SP-LOOPS Task 6)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class SafeTextInterface(Protocol):
    def clean(self, text: str, limit: int) -> str:
        """`text` as one line with no control, format or separator characters, whitespace runs
        collapsed, at most `limit` characters; a cut text ends in an ellipsis. Raises
        `ValueError` for a `limit` below 1."""
        ...
