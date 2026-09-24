# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind the PostgreSQL side of queue reaping (ADR-0056).

Mirrors `vibey/infrastructure/db/queue_reap_store.py` (ADR-0016). Interfaces declare; they
never consume. The domain and draft types are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.interfaces.queue_reap import QueueReapStore

if TYPE_CHECKING:
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.ledger import Provenance
    from vibey.domain.phase import Phase
    from vibey.domain.queue_reap import ReapVerdict
    from vibey.infrastructure.engines.tailer import LedgerEventDraft


@runtime_checkable
class ReapEventDraftBuilderInterface(Protocol):
    """Builds the `QueueReaped` ledger draft for one verdict."""

    def draft(
        self,
        verdict: ReapVerdict,
        *,
        project_id: UUID,
        cycle: int,
        phase: Phase,
        job_id: UUID | None,
        at: datetime,
        provenance: Provenance = ...,
    ) -> LedgerEventDraft:
        """The object, condition, measured value, threshold and action, as the payload."""
        ...


@runtime_checkable
class PostgresQueueReapStoreInterface(QueueReapStore, Protocol):
    """Reaps leases, measures ready work and parks dead letters, each write in one
    transaction with its ledger event."""
