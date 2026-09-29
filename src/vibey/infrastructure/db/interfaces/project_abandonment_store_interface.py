# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the PostgreSQL side of abandoning a project (`vibey abandon`).

Mirrors `vibey/infrastructure/db/project_abandonment_store.py` (ADR-0016). Interfaces
declare; they never consume. The record and draft types are imported under TYPE_CHECKING
only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.project_abandonment import ProjectAbandonmentStore

if TYPE_CHECKING:
    from vibey.application.dto import HumanGateRecord, ProjectRecord
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class GateWithdrawnDraftBuilderInterface(Protocol):
    """Builds the `GateWithdrawn` ledger draft for one gate an abandonment closed."""

    def build(
        self, settled: ProjectRecord, gate: HumanGateRecord, *, by: str, account: str
    ) -> LedgerEventDraft:
        """Filed under abandoned and the settled project's cycle, `trusted`, with no
        engine and no job, at the time the move into abandoned was made."""
        ...


@runtime_checkable
class PostgresProjectAbandonmentStoreInterface(ProjectAbandonmentStore, Protocol):
    """Moves a project into abandoned, withdraws its open gates and cancels its unsettled
    jobs in one transaction, under a lock on the project's row."""
