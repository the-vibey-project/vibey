# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/budget_declaration.py` (ADR-0016). Interfaces declare;
they never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from pathlib import Path


@runtime_checkable
class BudgetDeclarationInterface(Protocol):
    """`[budget] ultra_no_cap` in a `vibey.toml`, edited as text."""

    def read(self, path: Path) -> bool:
        """The declared value; `False` for a missing, unreadable or malformed file."""
        ...

    def write(self, path: Path, enabled: bool) -> None:
        """Sets the key, leaving every other line as it was. Raises `TOMLDecodeError`
        and writes nothing when the result would not parse."""
        ...

    def edit(self, text: str, enabled: bool) -> str:
        """The text with the key set: replaced, added under `[budget]`, or appended."""
        ...
