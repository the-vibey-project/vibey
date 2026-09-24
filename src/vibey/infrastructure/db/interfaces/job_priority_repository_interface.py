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

    from vibey.domain.queue_priority import PriorityChange, PriorityContext, PriorityRefusal
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class PriorityEventDraftBuilderInterface(Protocol):
    """Builds the ledger drafts queue priority appends (ADR-0054): one per request."""

    def changed(
        self, change: PriorityChange, *, context: PriorityContext, at: datetime
    ) -> LedgerEventDraft:
        """`JobPriorityBumped` or `JobPriorityUnbumped` -- moved something or nothing --
        filed under the project's current cycle and phase, naming who asked."""
        ...

    def refused(self, refusal: PriorityRefusal, *, at: datetime) -> LedgerEventDraft:
        """`JobPriorityRefused`, with who asked and why. `untrusted`: the request came
        from outside the grant, so its text is data (12.j)."""
        ...
