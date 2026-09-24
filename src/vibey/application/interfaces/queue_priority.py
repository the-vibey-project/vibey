# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue priority's seams (ADR-0054): the store that reorders the queue atomically with
the ledger, where the grant comes from, who is asking, and the one service every
entry point reorders through.

Mirrors `vibey/application/queue_priority.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import EnqueueRequest, JobRecord, ProjectRecord, QueueEntry
from vibey.domain.interfaces.queue_priority_interface import (
    CallerInterface,
    PriorityGrantInterface,
)
from vibey.domain.queue_priority import (
    PriorityAction,
    PriorityChange,
    PriorityContext,
    PriorityRefusal,
)


@runtime_checkable
class JobPriorityStore(Protocol):
    """Reorders one project's queue. Each change locks the rows it reads, applies the
    plan, and appends its ledger event -- moved something or moved nothing -- in ONE
    transaction: a crash leaves the queue and its history as they were. Reached only
    through `QueuePriorityServiceInterface`, which decides whether it may be."""

    async def bump(
        self,
        job_id: UUID,
        *,
        context: PriorityContext,
        at: datetime,
        action: PriorityAction = PriorityAction.BUMP,
    ) -> PriorityChange:
        """Moves the job, and its unfinished dependencies ahead of it, to the back of the
        bumped jobs. Never touches a lease. Raises a `ReorderRefused` -- unknown job, not
        movable, a dependency that can never finish, a ring, a lock conflict -- changing
        and recording nothing; the caller records the refusal."""
        ...

    async def unbump(
        self, job_id: UUID, *, context: PriorityContext, at: datetime
    ) -> PriorityChange:
        """Undoes exactly what the job's bump moved. Raises `DependentsStillBumped` while
        a bumped job needs it, and the other `ReorderRefused`s as `bump` does."""
        ...

    async def refuse(self, refusal: PriorityRefusal, *, at: datetime) -> None:
        """Records a refused request on the ledger. Changes no job."""
        ...

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        """Every unfinished job of the project: running first, then waiting work in the
        order the claim would take it."""
        ...


@runtime_checkable
class PriorityGrantReader(Protocol):
    """Reads who may reorder a project's queue from the project's own reviewed
    configuration -- never from the working directory or a path the caller chooses."""

    def read(self, project: ProjectRecord) -> PriorityGrantInterface:
        """Raises `ConfigError` for a configuration that exists and cannot be read."""
        ...


@runtime_checkable
class CallerIdentity(Protocol):
    """Who the running process is, from the operating system."""

    def current(self) -> CallerInterface: ...


@runtime_checkable
class QueuePriorityServiceInterface(Protocol):
    """The only way to reorder the queue: authorises every request (12.j) before it
    looks at the job, records every request, and has the store make the change."""

    async def bump(
        self, project_id: UUID, job_id: UUID, *, source: str | None = None
    ) -> PriorityChange:
        """Raises a `ReorderRefused` -- `PriorityRefused` for a request with no grant --
        after recording it."""
        ...

    async def unbump(
        self, project_id: UUID, job_id: UUID, *, source: str | None = None
    ) -> PriorityChange: ...

    async def enqueue(
        self, request: EnqueueRequest, *, source: str | None = None
    ) -> tuple[JobRecord, PriorityChange]:
        """Enqueues a job already bumped. Refused, nothing is enqueued. A job that has
        already finished is a recorded no-op."""
        ...

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]: ...
