# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/error_catalog.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class ErrorEntry:
    """One error in the catalog: a permanent code, and what an operator needs to act on it.

    `code` is None only for an abstract base class, which is never raised itself. `retired`
    marks an error vibey no longer raises whose code must still explain an old log line.
    """

    qualname: str
    title: str
    cause: str
    fix: str = ""
    code: str | None = None
    abstract: bool = False
    retired: bool = False


@runtime_checkable
class ErrorCatalogInterface(Protocol):
    """The declared table of vibey's error codes."""

    def entries(self) -> Sequence[ErrorEntry]:
        """Every entry, in the order the table declares them."""
        ...

    def entry_for(self, exc_type: type[BaseException]) -> ErrorEntry | None:
        """The entry for exactly this type (no inheritance fallback), or None."""
        ...

    def by_code(self, code: str) -> ErrorEntry | None:
        """The entry with this code, matched case-insensitively, or None."""
        ...
