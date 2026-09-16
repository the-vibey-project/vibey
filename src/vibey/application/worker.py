# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The lease -> execute -> ack loop. Workers are stateless: all durable
state lives in JobRepository, so a worker can die at any point and a reaped
job is simply claimed by someone else (non-negotiable #6: every handler must
be idempotent under replay).

The attempt bound is a ladder like any other, so it ends the way ADR-0024
says every bounded ladder ends: in a park that advertises its grant. A job
that burns its last attempt parks as ``attempts_exhausted`` with the number
to type; it never becomes a ``failed`` row nobody was told about."""

import asyncio
import contextlib
from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID

from vibey.application.dto import HumanGateRecord, HumanGateRequest, JobRecord
from vibey.application.interfaces import (
    Defer,
    Failure,
    JobHandler,
    Logger,
    Outcome,
    Park,
    Success,
)
from vibey.application.observability import StandardLibraryLogger
from vibey.application.ports import HumanGateRepository, JobRepository
from vibey.domain.job import FailureClass

# The grant key every attempt bound in the tree reads and writes. It is the
# same key build.implement's `escalation_exhausted` gate advertises, on
# purpose: one answer widens both the queue's attempt bound and the effort
# ladder's, so a human never has to know there are two.
ATTEMPTS_GRANT_KEY = "max_attempts"
EXHAUSTED_GATE_KIND = "attempts_exhausted"


class CapacityDeferred(Exception):
    def __init__(self, retry_at: datetime, detail: str) -> None:
        super().__init__(detail)
        self.retry_at = retry_at
        self.detail = detail


class WorkerLoop:
    def __init__(
        self,
        *,
        jobs: JobRepository,
        gates: HumanGateRepository,
        handler: JobHandler,
        owner: str,
        lease: timedelta = timedelta(seconds=30),
        lease_for_kind: Callable[[str], timedelta] | None = None,
        attempts_grant_step: int = 3,
        logger: Logger | None = None,
    ) -> None:
        self._jobs = jobs
        self._gates = gates
        self._handler = handler
        self._owner = owner
        self._lease = lease
        self._lease_for_kind = lease_for_kind
        # How many further attempts the exhaustion park suggests. A number
        # a project may well want to tune, so it is a key rather than a
        # literal (ADR-0018); the default matches the one build.implement's
        # `escalation_exhausted` prompt has always printed.
        self._attempts_grant_step = attempts_grant_step
        self._log: Logger = (
            logger if logger is not None else StandardLibraryLogger(__name__, owner=owner)
        )

    async def run_once(self, project_id: UUID) -> bool:
        """Claims and executes at most one job. Returns False if there was
        nothing claimable."""
        job = await self._jobs.claim(project_id, owner=self._owner, lease=self._lease)
        if job is None:
            return False

        # Lease duration is per-kind (a build.implement run takes hours; a
        # triage takes minutes). The kind isn't known until after the claim,
        # so claim at the short default and immediately extend once resolved.
        lease = self._lease
        if self._lease_for_kind is not None:
            resolved = self._lease_for_kind(job.kind)
            if resolved != self._lease:
                await self._jobs.heartbeat(job.id, owner=self._owner, lease=resolved)
                lease = resolved

        heartbeat_task = asyncio.ensure_future(self._heartbeat_forever(job.id, lease=lease))
        try:
            try:
                outcome: Outcome = await self._handler.handle(job)
            except CapacityDeferred as exc:
                outcome = Defer(exc.retry_at, exc.detail, capacity=True)
            except Exception as exc:  # noqa: BLE001 - any handler bug becomes a VIBEY-class nack
                outcome = Failure(FailureClass.VIBEY, str(exc))
        finally:
            heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat_task

        await self._settle(job, outcome)
        return True

    async def _settle(self, job: JobRecord, outcome: Outcome) -> None:
        if isinstance(outcome, Success):
            await self._jobs.ack(job.id, owner=self._owner)
        elif isinstance(outcome, Failure):
            await self._settle_failure(job, outcome)
        elif isinstance(outcome, Park):
            await self._raise_and_park(job, outcome.request)
        elif isinstance(outcome, Defer):
            # A defer used to leave no trace outside `job.last_error`: the
            # queue showed 0 failed, 0 parked and a job quietly sliding its
            # run_after, so a BUILD that could never select an engine was
            # indistinguishable from an idle worker, and the only way to see
            # why was a hand-written SQL query. Say it out loud instead.
            #
            # The line is emitted AFTER the transition, never before. `defer`
            # returns False when this worker no longer holds the lease -- it
            # expired mid-handler and another worker claimed the row -- and it
            # can fail before committing. Announcing first would assert a
            # `retry_at` that never moved, and a reader chasing that line finds
            # a job whose run_after disagrees with the log: a false record is
            # worse than the silence this block exists to end.
            deferred = await self._jobs.defer(
                job.id,
                owner=self._owner,
                retry_at=outcome.retry_at,
                error={"class": FailureClass.CAPACITY.value, "detail": outcome.detail},
            )
            if not deferred:
                # Warning, not info: nothing was deferred, the work this worker
                # just did was discarded, and something else now owns the job.
                self._log.warning(
                    "job.defer_rejected",
                    job_id=str(job.id),
                    project_id=str(job.project_id),
                    phase=job.phase.value,
                    kind=job.kind,
                    reason="lease no longer held by this worker",
                )
                return
            # Capacity is the one that warrants a warning. Routine
            # verify-repair waits are Defers too (see `Defer.capacity`), and
            # crying wolf on every one of those is how a warning stops being
            # read at all.
            say = self._log.warning if outcome.capacity else self._log.info
            say(
                "job.deferred",
                job_id=str(job.id),
                project_id=str(job.project_id),
                phase=job.phase.value,
                kind=job.kind,
                work_item=job.work_item_id,
                capacity=outcome.capacity,
                reason=outcome.detail,
                retry_at=outcome.retry_at.isoformat(),
            )

    async def _settle_failure(self, job: JobRecord, outcome: Failure) -> None:
        """Nack while attempts remain; park with a grant once they are gone.

        `nack`'s SQL turns the last attempt into ``state='failed'``, which is
        the dead end ADR-0024 rejects by name: the work item stops, no
        human_gate row explains why, and nobody is asked. So the bound is
        read here first. An answered grant widens it durably (the row, not
        just this process) before the nack, because the repository decides
        'failed' from the row's own `max_attempts` and would otherwise kill
        a job the human had just paid for.
        """
        error = {"class": outcome.failure_class.value, "detail": outcome.detail}
        if job.attempts < job.max_attempts:
            await self._jobs.nack(job.id, owner=self._owner, error=error)
            return

        gate = await self._gates.latest_for_job(job.id)
        granted = self._granted_attempts(gate)
        if granted is not None and granted > job.attempts:
            await self._jobs.grant_attempts(job.id, owner=self._owner, max_attempts=granted)
            await self._jobs.nack(job.id, owner=self._owner, error=error)
            return

        limit = job.max_attempts
        await self._raise_and_park(
            job,
            HumanGateRequest(
                kind=EXHAUSTED_GATE_KIND,
                prompt=(
                    f"job {job.kind!r} exhausted its {limit} attempts on the last "
                    f"failure ({outcome.failure_class.value}: {outcome.detail}). Grant "
                    f"more by answering --raw "
                    f"'{{\"{ATTEMPTS_GRANT_KEY}\": {limit + self._attempts_grant_step}}}', "
                    "or fix the item by hand and answer anything to retry it once."
                ),
            ),
        )

    def _granted_attempts(self, gate: HumanGateRecord | None) -> int | None:
        """The attempt bound a human granted on this job's latest gate, if
        any. A gate of another kind, or one answered without the grant key,
        simply grants nothing."""
        if gate is None or gate.answer is None:
            return None
        # Imported inside the method, not at module scope: build_verify_handler
        # imports this module's outcome vocabulary, so a top-level import would
        # close an import cycle. Reusing the family's one parser still beats a
        # second copy of it (ADR-0017) -- see the follow-up to give the grant
        # parsers a shared home so this can become an ordinary import.
        from vibey.application.build_verify_handler import granted_limit

        return granted_limit(gate.answer, ATTEMPTS_GRANT_KEY)

    async def _raise_and_park(self, job: JobRecord, request: HumanGateRequest) -> None:
        # The gate is raised before the lease is released, so there is
        # never a window where the job looks claimable again before the
        # human_gate row exists to explain why it is parked.
        #
        # Some handlers (review.collect, the deploy gates) raise their
        # gate themselves before returning Park; raising here again
        # would leave a duplicate unanswered gate that latest_for_job
        # returns forever, re-parking the job no matter what the human
        # answered. Only raise when this job has no open gate already.
        existing = await self._gates.latest_for_job(job.id)
        if existing is None or existing.answer is not None:
            await self._gates.raise_gate(job.project_id, job.id, request)
        await self._jobs.park(job.id, owner=self._owner)

    async def _heartbeat_forever(self, job_id: UUID, *, lease: timedelta) -> None:
        interval = lease.total_seconds() / 3
        try:
            while True:
                await asyncio.sleep(interval)
                await self._jobs.heartbeat(job_id, owner=self._owner, lease=lease)
        except asyncio.CancelledError:
            pass


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "Defer",
    "Failure",
    "JobHandler",
    "Outcome",
    "Park",
    "Success",
]
