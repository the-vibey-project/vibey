# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for turning a settled phase move into a ledger draft.

Mirrors `vibey/infrastructure/db/project_repository.py` (ADR-0016).
Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.dto import ProjectRecord
    from vibey.domain.phase import Phase
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class PhaseTransitionedDraftBuilderInterface(Protocol):
    """Builds the `PhaseTransitioned` draft for a move that has just landed."""

    def build(self, settled: ProjectRecord, expected: Phase, guard: str | None) -> LedgerEventDraft:
        """`settled` is the row the CAS returned; `expected` is the phase it left."""
        ...
