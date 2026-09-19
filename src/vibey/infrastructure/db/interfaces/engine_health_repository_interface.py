# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading one `engine_health` row.

Mirrors `vibey/infrastructure/db/engine_health_repository.py` (ADR-0016). Interfaces
declare; they never consume. The driver and DTO types are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg

    from vibey.application.dto import EngineHealthRecord


@runtime_checkable
class EngineHealthRowMapperInterface(Protocol):
    """Maps one row of the `engine_health` table to an `EngineHealthRecord`."""

    def to_record(self, row: asyncpg.Record) -> EngineHealthRecord:
        """Every column, typed. An engine id this vibey does not know is kept as
        its stored text, never raised (vibey#287)."""
        ...
