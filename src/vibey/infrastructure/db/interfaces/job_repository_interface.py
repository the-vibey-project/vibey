# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reading one `job` row.

Mirrors `vibey/infrastructure/db/job_repository.py` (ADR-0016). Interfaces declare;
they never consume. The driver and DTO types are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import asyncpg

    from vibey.application.dto import JobRecord
    from vibey.domain.job import StoredJobState


@runtime_checkable
class JobRowMapperInterface(Protocol):
    """Maps one row of the `job` table to a `JobRecord`."""

    def state(self, raw: str) -> StoredJobState:
        """One stored `job.state`; a state this vibey does not know is kept as its
        stored text, never raised (vibey#287)."""
        ...

    def to_record(self, row: asyncpg.Record) -> JobRecord:
        """Every column, typed. `phase` and `state` are read forward-compatibly."""
        ...
