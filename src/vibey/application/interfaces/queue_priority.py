# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority's seams (ADR-0054): the store that reorders the queue atomically
with the ledger, and the service that decides who may ask it to.

Mirrors `vibey/application/queue_priority.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import EnqueueRequest, JobRecord, QueueEntry
from vibey.domain.queue_priority import (
    OPERATOR_SOURCE,
    PriorityAction,
    PriorityChange,
    PriorityRefusal,
)


@runtime_checkable
class JobPriorityStore(Protocol):
    """Reorders one project's queue. Each write locks the rows it reads, applies the
    plan, and appends its ledger event in ONE transaction: a crash leaves the queue
    and its history as they were, and a replay is a no-op."""

    async def bump(
        self,
        job_id: UUID,
        *,
        source: str,
        at: datetime,
        action: PriorityAction = PriorityAction.BUMP,
    ) -> PriorityChange:
        """Moves the job, and its unfinished dependencies ahead of it, to the back of
        the bumped jobs. Never touches a lease. Raises `UnknownJob`, `NotReorderable`
        or `DependencyCycle`, changing nothing."""
        ...

    async def unbump(self, job_id: UUID, *, source: str, at: datetime) -> PriorityChange:
        """Returns the job, and every bumped job depending on it, to normal order."""
        ...

    async def refuse(self, refusal: PriorityRefusal, *, at: datetime) -> None:
        """Records a refused request on the ledger. Changes no job."""
        ...

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        """Every unfinished job of the project: running first, then waiting work in
        the order the claim would take it."""
        ...


@runtime_checkable
class QueuePriorityServiceInterface(Protocol):
    """Authorises a reorder request (12.j), then has the store make it."""

    async def bump(self, job_id: UUID, *, source: str = OPERATOR_SOURCE) -> PriorityChange:
        """Raises `PriorityRefused` for a source with no grant, after recording it."""
        ...

    async def unbump(self, job_id: UUID, *, source: str = OPERATOR_SOURCE) -> PriorityChange: ...

    async def enqueue(
        self, request: EnqueueRequest, *, source: str = OPERATOR_SOURCE
    ) -> tuple[JobRecord, PriorityChange]:
        """Enqueues a job already bumped. Refused, nothing is enqueued."""
        ...

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]: ...
