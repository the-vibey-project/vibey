# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one path every queue reorder takes (ADR-0054).

Order matters, and is the point:

1. The project the request names is found. Its current cycle and phase are where the
   request is recorded; with no project there is nowhere to record anything, and the
   request is reported, not recorded.
2. The grant is read from the project's own reviewed configuration and the caller is
   checked against it -- BEFORE the job is looked at, so a stranger asking about any
   job, real or not, is refused and recorded without learning anything about it (12.j).
3. The store makes the change and records it -- moved something or moved nothing.
4. Anything the store refuses -- an unknown job, a finished one, a dependency that can
   never finish, a ring, a lock conflict -- is recorded as refused before it reaches the
   caller. Every request is on the ledger, whatever became of it.

A bump changes order and nothing else, so nothing here touches a phase, a gate, an
admission check or a handoff: those decide whether a job may run; this decides only
which claimable job runs first.
"""

from typing import NoReturn
from uuid import UUID

from vibey.application.dto import EnqueueRequest, JobRecord, QueueEntry
from vibey.application.interfaces.projects import ProjectStore
from vibey.application.interfaces.queue import JobRepository
from vibey.application.interfaces.queue_priority import (
    CallerIdentity,
    JobPriorityStore,
    PriorityGrantReader,
)
from vibey.application.interfaces.system import Clock
from vibey.domain.config import ConfigError
from vibey.domain.errors import PriorityRefused, ReorderRefused, UnknownProject, WrongPhase
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import (
    PriorityAction,
    PriorityChange,
    PriorityContext,
    PriorityRefusal,
)


class QueuePriorityService:
    """Authorises every reorder request, records every one, and has the store move."""

    def __init__(
        self,
        *,
        projects: ProjectStore,
        jobs: JobRepository,
        store: JobPriorityStore,
        grants: PriorityGrantReader,
        caller: CallerIdentity,
        clock: Clock,
    ) -> None:
        self._projects = projects
        self._jobs = jobs
        self._store = store
        self._grants = grants
        self._caller = caller
        self._clock = clock

    async def bump(
        self, project_id: UUID, job_id: UUID, *, source: str | None = None
    ) -> PriorityChange:
        context = await self._admit(project_id, PriorityAction.BUMP, job_id, source)
        try:
            return await self._store.bump(job_id, context=context, at=self._clock.now())
        except ReorderRefused as refused:
            await self._refuse(context, PriorityAction.BUMP, job_id, refused)

    async def unbump(
        self, project_id: UUID, job_id: UUID, *, source: str | None = None
    ) -> PriorityChange:
        context = await self._admit(project_id, PriorityAction.UNBUMP, job_id, source)
        try:
            return await self._store.unbump(job_id, context=context, at=self._clock.now())
        except ReorderRefused as refused:
            await self._refuse(context, PriorityAction.UNBUMP, job_id, refused)

    async def enqueue(
        self, request: EnqueueRequest, *, source: str | None = None
    ) -> tuple[JobRecord, PriorityChange]:
        """Authorised before the enqueue, so a refused request leaves no job behind. The
        enqueue and the bump are each idempotent, so a crash between them is repaired by
        replaying the whole call; replaying it after the job finished is a recorded
        no-op, as a plain re-enqueue of a finished job is a no-op."""
        context = await self._admit(request.project_id, PriorityAction.ENQUEUE, None, source)
        job = await self._jobs.enqueue(request)
        try:
            change = await self._store.bump(
                job.id, context=context, at=self._clock.now(), action=PriorityAction.ENQUEUE
            )
        except ReorderRefused as refused:
            await self._refuse(context, PriorityAction.ENQUEUE, job.id, refused)
        return job, change

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        return await self._store.queue(project_id)

    async def _admit(
        self, project_id: UUID, action: PriorityAction, job_id: UUID | None, source: str | None
    ) -> PriorityContext:
        project = await self._projects.get(project_id)
        if project is None:
            raise UnknownProject(f"unknown project {project_id}")
        phase = project.phase
        if not isinstance(phase, Phase):
            # Writers stay strict (vibey#287): nothing can be recorded under a phase this
            # vibey cannot vouch for, so the request is reported and goes no further.
            raise WrongPhase(
                f"project {project_id} is in phase {phase.value!r}, which this vibey does not "
                "know; it will not record a queue change there"
            )
        caller = self._caller.current()
        try:
            decision = self._grants.read(project).decide(source, caller)
        except ConfigError as unreadable:
            requested_by = f"source:{source}" if source is not None else f"account:{caller.name}"
            context = PriorityContext(project_id, project.cycle, phase, requested_by)
            await self._refuse(
                context,
                action,
                job_id,
                PriorityRefused(requested_by, f"the grant cannot be read: {unreadable}"),
            )
        context = PriorityContext(project_id, project.cycle, phase, decision.principal)
        if not decision.admitted:
            await self._refuse(
                context, action, job_id, PriorityRefused(decision.principal, decision.reason)
            )
        return context

    async def _refuse(
        self,
        context: PriorityContext,
        action: PriorityAction,
        job_id: UUID | None,
        refused: ReorderRefused,
    ) -> NoReturn:
        """Record the refusal, then raise it."""
        await self._store.refuse(
            PriorityRefusal(context=context, job_id=job_id, action=action, reason=str(refused)),
            at=self._clock.now(),
        )
        raise refused
