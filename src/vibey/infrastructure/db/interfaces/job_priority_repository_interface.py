# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for turning a queue-priority change into its ledger draft.

Mirrors `vibey/infrastructure/db/job_priority_repository.py` (ADR-0016). Interfaces
declare; they never consume. The domain and draft types are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.phase import Phase
    from vibey.domain.queue_priority import PriorityChange, PriorityRefusal
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class PriorityEventDraftBuilderInterface(Protocol):
    """Builds the ledger drafts queue priority appends (ADR-0054)."""

    def changed(
        self,
        change: PriorityChange,
        *,
        project_id: UUID,
        cycle: int,
        phase: Phase,
        at: datetime,
    ) -> LedgerEventDraft:
        """`JobPriorityBumped` or `JobPriorityUnbumped`, filed under the target job's
        project, cycle and phase, listing every job the change moved."""
        ...

    def refused(self, refusal: PriorityRefusal, *, at: datetime) -> LedgerEventDraft:
        """`JobPriorityRefused`, with the source and the reason. `untrusted`: the
        request came from outside the grant, so its text is data (12.j)."""
        ...
