# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading one `rotation_cursor` row.

Mirrors `vibey/infrastructure/db/rotation_cursor_repository.py` (ADR-0016).
Interfaces declare; they never consume. The driver and DTO types are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg

    from vibey.application.dto import RotationCursor


@runtime_checkable
class RotationCursorRowMapperInterface(Protocol):
    """Maps one row of the `rotation_cursor` table to a `RotationCursor`."""

    def to_cursor(self, row: asyncpg.Record) -> RotationCursor:
        """Every column, typed. An engine id this vibey does not know is kept as
        its stored text, never raised (vibey#287)."""
        ...
