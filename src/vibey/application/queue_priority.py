# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who may reorder the queue, and the one path every reorder takes (ADR-0054).

The grant is checked before anything moves. A source with no grant is refused, the
refusal is appended to the ledger, and `PriorityRefused` carries the reason to the
caller: the refusal is reportable output, never silence (12.d, 12.j). The operator
needs no declaration; every other source is admitted only by name, from
`[queue.priority] sources` in vibey.toml (12.h).

A bump changes order and nothing else, so nothing here touches a phase, a gate, an
admission check or a handoff: those decide whether a job may run; this decides only
which claimable job runs first.
"""

from uuid import UUID

from vibey.application.dto import EnqueueRequest, JobRecord, QueueEntry
from vibey.application.interfaces.queue import JobRepository
from vibey.application.interfaces.queue_priority import JobPriorityStore
from vibey.application.interfaces.system import Clock
from vibey.domain.errors import NotReorderable, PriorityRefused, UnknownJob
from vibey.domain.interfaces.queue_priority_interface import PriorityGrantInterface
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import (
    OPERATOR_SOURCE,
    PriorityAction,
    PriorityChange,
    PriorityRefusal,
)


class QueuePriorityService:
    """Authorises a reorder request, then has the store make it atomically."""

    def __init__(
        self,
        *,
        jobs: JobRepository,
        store: JobPriorityStore,
        grant: PriorityGrantInterface,
        clock: Clock,
    ) -> None:
        self._jobs = jobs
        self._store = store
        self._grant = grant
        self._clock = clock

    async def bump(self, job_id: UUID, *, source: str = OPERATOR_SOURCE) -> PriorityChange:
        await self._admit(PriorityAction.BUMP, source, await self._job(job_id))
        return await self._store.bump(job_id, source=source, at=self._clock.now())

    async def unbump(self, job_id: UUID, *, source: str = OPERATOR_SOURCE) -> PriorityChange:
        await self._admit(PriorityAction.UNBUMP, source, await self._job(job_id))
        return await self._store.unbump(job_id, source=source, at=self._clock.now())

    async def enqueue(
        self, request: EnqueueRequest, *, source: str = OPERATOR_SOURCE
    ) -> tuple[JobRecord, PriorityChange]:
        """Authorised before the enqueue, so a refused request leaves no job behind.
        The enqueue and the bump are each idempotent, so a crash between them is
        repaired by replaying the whole call."""
        await self._authorise(
            PriorityAction.ENQUEUE,
            source,
            project_id=request.project_id,
            cycle=request.cycle,
            phase=request.phase,
            job_id=None,
        )
        job = await self._jobs.enqueue(request)
        change = await self._store.bump(
            job.id, source=source, at=self._clock.now(), action=PriorityAction.ENQUEUE
        )
        return job, change

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        return await self._store.queue(project_id)

    async def _job(self, job_id: UUID) -> JobRecord:
        job = await self._jobs.get(job_id)
        if job is None:
            raise UnknownJob(job_id)
        return job

    async def _admit(self, action: PriorityAction, source: str, job: JobRecord) -> None:
        phase = job.phase
        if not isinstance(phase, Phase):
            # Writers stay strict (vibey#287): neither the move nor its refusal can be
            # ledgered under a phase this vibey cannot vouch for.
            raise NotReorderable(
                job.id, f"its phase {phase.value!r} is one this vibey does not know"
            )
        await self._authorise(
            action,
            source,
            project_id=job.project_id,
            cycle=job.cycle,
            phase=phase,
            job_id=job.id,
        )

    async def _authorise(
        self,
        action: PriorityAction,
        source: str,
        *,
        project_id: UUID,
        cycle: int,
        phase: Phase,
        job_id: UUID | None,
    ) -> None:
        """Admit the source, or record the attempt as refused and raise."""
        if self._grant.admits(source):
            return
        reason = self._grant.refusal(source)
        await self._store.refuse(
            PriorityRefusal(
                project_id=project_id,
                cycle=cycle,
                phase=phase,
                job_id=job_id,
                action=action,
                source=source,
                reason=reason,
            ),
            at=self._clock.now(),
        )
        raise PriorityRefused(source, reason)
