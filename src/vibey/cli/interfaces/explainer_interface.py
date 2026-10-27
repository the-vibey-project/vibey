# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/explain.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class ErrorExplainerInterface(Protocol):
    """Turns an error code into the text `vibey explain` prints."""

    def explain(self, code: str) -> tuple[int, str]:
        """(exit status, text): 0 and the entry, or 2 and a message naming close codes."""
        ...

    def listing(self) -> str:
        """Every code and its title, one per line."""
        ...
