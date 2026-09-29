# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts for reading one `project` row, and for turning a settled phase
move into a ledger draft.

Mirrors `vibey/infrastructure/db/project_repository.py` (ADR-0016).
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping
    from uuid import UUID

    import asyncpg

    from vibey.application.dto import ProjectRecord
    from vibey.domain.phase import Phase
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class ProjectRowMapperInterface(Protocol):
    """Maps one row of the `project` table to a `ProjectRecord`."""

    def to_record(self, row: asyncpg.Record) -> ProjectRecord:
        """Every column, typed. A phase this vibey does not know is kept as its
        stored text, never raised (vibey#287)."""
        ...


@runtime_checkable
class PhaseTransitionedDraftBuilderInterface(Protocol):
    """Builds the `PhaseTransitioned` draft for a move that has just landed."""

    def build(
        self,
        settled: ProjectRecord,
        expected: Phase,
        guard: str | None,
        *,
        attribution: Mapping[str, object] | None = None,
    ) -> LedgerEventDraft:
        """`settled` is the row the CAS returned; `expected` is the phase it left.
        `attribution` adds fields beside `from`, `to`, `cycle` and `guard`, never
        replacing one of them."""
        ...


@runtime_checkable
class ProjectTransitionOnConnectionInterface(Protocol):
    """A guarded phase move a caller runs inside its own transaction, and the notice of
    it the caller sends once that transaction has committed."""

    async def transition_on(
        self,
        conn: asyncpg.Connection,
        project_id: UUID,
        *,
        expected: Phase,
        to: Phase,
        cycle: int | None = None,
        guard: str | None = None,
        attribution: Mapping[str, object] | None = None,
    ) -> ProjectRecord:
        """Compare-and-set the phase from `expected` to `to` and append its
        `PhaseTransitioned`, on `conn`. Raises `ValueError` when the project is not in
        `expected`, which rolls the caller's transaction back."""
        ...

    async def announce(self, settled: ProjectRecord, *, expected: Phase) -> None:
        """Notify a committed move. Never raises for a failed delivery."""
        ...
