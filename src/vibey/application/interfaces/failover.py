# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Engine-level failover's seams (ADR-0070): the store that appends its three trusted
kinds, and the service that decides with them.

Mirrors `vibey/application/engine_failover.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import EngineFailoverDecision
from vibey.application.interfaces.ledger import BriefProducer
from vibey.domain.capacity import CapacityState
from vibey.domain.engine import EngineId, JobRequirement
from vibey.domain.failover import FailoverStatus
from vibey.domain.handoff import BudgetSnapshot, LedgerRef
from vibey.domain.ledger import EventKind


@runtime_checkable
class FailoverEventStore(Protocol):
    """Appends one trusted failover event."""

    async def record(
        self,
        project_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
        *,
        at: datetime,
    ) -> None: ...


@runtime_checkable
class EngineFailoverServiceInterface(Protocol):
    async def status(self, project_id: UUID) -> FailoverStatus: ...

    async def fail_over(
        self,
        project_id: UUID,
        *,
        from_engine: EngineId,
        capacity: CapacityState,
        requirement: JobRequirement,
        producer: BriefProducer,
        ref: LedgerRef,
        budget: BudgetSnapshot,
    ) -> EngineFailoverDecision: ...

    async def record_probe(
        self, project_id: UUID, *, engine: EngineId, ok: bool, detail: str = ""
    ) -> FailoverStatus: ...

    async def hand_back(
        self,
        project_id: UUID,
        *,
        producer: BriefProducer,
        ref: LedgerRef,
        budget: BudgetSnapshot,
    ) -> EngineFailoverDecision: ...
