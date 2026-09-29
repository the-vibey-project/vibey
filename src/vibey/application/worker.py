# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The lease -> execute -> ack loop. Workers are stateless: all durable
state lives in JobRepository, so a worker can die at any point and a reaped
job is simply claimed by someone else (non-negotiable #6: every handler must
be idempotent under replay).

The attempt bound is a ladder like any other, so it ends the way ADR-0024
says every bounded ladder ends: in a park that advertises its grant. A job
that burns its last attempt parks as ``attempts_exhausted`` with the number
to type; it never becomes a ``failed`` row nobody was told about -- unless its
last failures were all one failure, when more attempts cannot help and it parks
on a ``defect`` gate instead (application/defect_triage.py).

Every gate it raises is announced through `GateNoticeService`, which records
whether anyone was told (application/gate_notices.py)."""

import asyncio
import contextlib
from collections.abc import Callable, Mapping
from datetime import UTC, datetime, timedelta
from typing import cast
from uuid import UUID

from vibey.application.dto import HumanGateRecord, HumanGateRequest, JobRecord
from vibey.application.gate_notices import GateNoticeService
from vibey.application.interfaces import (
    DefectTriageInterface,
    Defer,
    Failure,
    GateNoticeServiceInterface,
    JobHandler,
    Logger,
    NotificationSink,
    Outcome,
    Park,
    Success,
    TelemetryMetrics,
    TelemetrySpan,
    TelemetryTracer,
)
from vibey.application.interfaces.sabbath import SabbathGateInterface
from vibey.application.observability import StandardLibraryLogger
from vibey.application.ports import HumanGateRepository, JobRepository
from vibey.domain.errors import ClassifiedFailure
from vibey.domain.gate_notice import RAISED_NOTICE
from vibey.domain.job import ATTEMPTS_EXHAUSTED_GATE_KIND, DEFECT_GATE_KIND, FailureClass
from vibey.domain.phase import Phase

# The grant key every attempt bound in the tree reads and writes. It is the
# same key build.implement's `escalation_exhausted` gate advertises, on
# purpose: one answer widens both the queue's attempt bound and the effort
# ladder's, so a human never has to know there are two.
ATTEMPTS_GRANT_KEY = "max_attempts"
EXHAUSTED_GATE_KIND = ATTEMPTS_EXHAUSTED_GATE_KIND


class CapacityDeferred(Exception):
    def __init__(
        self,
        retry_at: datetime,
        detail: str,
        *,
        capacity_state: str | None = None,
    ) -> None:
        super().__init__(detail)
        self.retry_at = retry_at
        self.detail = detail
        self.capacity_state = capacity_state


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
        notifications: NotificationSink | None = None,
        notification_config: Mapping[str, object] | None = None,
        tracer: TelemetryTracer | None = None,
        metrics: TelemetryMetrics | None = None,
        telemetry_enabled: bool = True,
        sabbath: SabbathGateInterface | None = None,
        gate_notices: GateNoticeServiceInterface | None = None,
        defects: DefectTriageInterface | None = None,
    ) -> None:
        # Sub-doctrine 8.i: from sundown Friday to sundown Saturday this worker claims
        # nothing. Jobs wait exactly where the queue put them -- paused, not failed (10.f)
        # -- and the first poll after the window claims again. None keeps no Sabbath, which
        # only a caller with no host to read (a test harness) may choose.
        self._sabbath = sabbath
        self._resting_until: datetime | None = None
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
        self._notifications = notifications
        self._notification_config = notification_config
        self._tracer = tracer if telemetry_enabled else None
        self._metrics = metrics if telemetry_enabled else None
        self._log: Logger = (
            logger if logger is not None else StandardLibraryLogger(__name__, owner=owner)
        )
        # Without a store the notices are still sent and said, just not recorded: what a
        # harness composes. The composition root always hands in the recording service.
        self._gate_notices: GateNoticeServiceInterface = (
            gate_notices
            if gate_notices is not None
            else GateNoticeService(sink=notifications, store=None, logger=self._log)
        )
        # None: every exhaustion offers its grant, as before defects were told apart.
        self._defects = defects

    def _resting(self) -> bool:
        """Whether 8.i holds now. Logs the rest once when it begins and once when it ends,
        not on every poll, so a rested worker is visible without flooding the log."""
        held = self._sabbath.hold() if self._sabbath is not None else None
        if held is not None:
            if self._resting_until != held.resumes:
                self._resting_until = held.resumes
                self._log.info(
                    "sabbath.resting",
                    owner=self._owner,
                    resumes=held.resumes.isoformat(),
                    basis=held.basis,
                )
            return True
        if self._resting_until is not None:
            self._log.info(
                "sabbath.ended", owner=self._owner, rested_until=self._resting_until.isoformat()
            )
            self._resting_until = None
        return False

    async def run_once(self, project_id: UUID) -> bool:
        """Claims and executes at most one job. Returns False if there was
        nothing claimable."""
        if self._resting():
            return False
        job = await self._jobs.claim(project_id, owner=self._owner, lease=self._lease)
        if job is None:
            return False

        claimed_at = datetime.now(UTC)
        self._record_queue_latency(job, claimed_at)

        # Lease duration is per-kind (a build.implement run takes hours; a
        # triage takes minutes). The kind isn't known until after the claim,
        # so claim at the short default and immediately extend once resolved.
        # An extension that fails or is refused is said by `_beat` and the job
        # carries on at the default, which the heartbeat loop keeps alive (or
        # reports lost) at that lease's own cadence -- it is not a reason to
        # drop a job this worker has already claimed (#211).
        lease = self._lease
        if self._lease_for_kind is not None:
            resolved = self._lease_for_kind(job.kind)
            if resolved != self._lease and await self._beat(job, lease=resolved):
                lease = resolved

        started_at = datetime.now(UTC)
        with self._job_span(job) as span:
            heartbeat_task = asyncio.ensure_future(self._heartbeat_forever(job, lease=lease))
            try:
                try:
                    outcome = await self._handler.handle(job)
                except CapacityDeferred as exc:
                    outcome = Defer(
                        exc.retry_at,
                        exc.detail,
                        capacity=True,
                        capacity_state=exc.capacity_state,
                    )
                except ClassifiedFailure as exc:
                    # A failure that knows its cause is recorded as that cause: an
                    # exhausted model output budget is CAPACITY and a malformed model
                    # answer is ENGINE, and the exhausted-attempts gate says which.
                    outcome = Failure(exc.failure_class, str(exc))
                except Exception as exc:  # noqa: BLE001 - any handler bug becomes a VIBEY-class nack
                    outcome = Failure(FailureClass.VIBEY, str(exc))
            finally:
                heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await heartbeat_task
            if span is not None:
                span.set_attribute("outcome", type(outcome).__name__)

        self._record_phase_duration(job, started_at)

        await self._settle(job, outcome)
        return True

    async def _settle(self, job: JobRecord, outcome: Outcome) -> None:
        if isinstance(outcome, Success):
            acked = await self._jobs.ack(job.id, owner=self._owner)
            self._landed(acked, event="job.ack_rejected", job=job)
        elif isinstance(outcome, Failure):
            await self._settle_failure(job, outcome)
        elif isinstance(outcome, Park):
            # A gate the handler raised itself is announced as it stands; one it asks
            # for is triaged first, so an exhausted ladder is not offered as a grant
            # when its failures were all one failure.
            request = (
                outcome.request
                if outcome.gate is not None
                else await self._triaged(job, outcome.request)
            )
            await self._raise_and_park(job, request, created_gate=outcome.gate)
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
            if not self._landed(deferred, event="job.defer_rejected", job=job):
                return
            # Capacity is the one that warrants a warning. Routine
            # verify-repair waits are Defers too (see `Defer.capacity`), and
            # crying wolf on every one of those is how a warning stops being
            # read at all.
            say = self._log.warning if outcome.capacity else self._log.info
            say(
                "job.deferred",
                **self._job_fields(job),
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
        # Every failure is recorded before anything else, so the history a later
        # exhaustion reads includes this one whichever way this settle ends.
        if self._defects is not None:
            await self._defects.record(job, outcome.failure_class, outcome.detail)
        if job.attempts < job.max_attempts:
            if await self._failed_alike_after_requeue(job, outcome):
                return
            nacked = await self._jobs.nack(job.id, owner=self._owner, error=error)
            self._landed(nacked, event="job.nack_rejected", job=job)
            return

        gate = await self._gates.latest_for_job(job.id, include_queue_gates=True)
        granted = self._granted_attempts(gate)
        if granted is not None and granted > job.attempts:
            # `granted > attempts >= max_attempts`, and only a lease-guarded
            # write ever changes the row's bound, so the grant always widens
            # it: a refusal here can only mean the lease is gone. The nack is
            # then skipped, not merely logged -- a nack without the grant is
            # the 'failed' dead end this branch exists to avoid, and it would
            # be refused by the same lease guard anyway.
            widened = await self._jobs.grant_attempts(
                job.id, owner=self._owner, max_attempts=granted
            )
            if not self._landed(widened, event="job.grant_rejected", job=job):
                return
            nacked = await self._jobs.nack(job.id, owner=self._owner, error=error)
            self._landed(nacked, event="job.nack_rejected", job=job)
            return

        await self._raise_and_park(
            job, await self._triaged(job, self._exhausted_request(job, outcome))
        )

    def _exhausted_request(self, job: JobRecord, outcome: Failure) -> HumanGateRequest:
        limit = job.max_attempts
        return HumanGateRequest(
            kind=EXHAUSTED_GATE_KIND,
            prompt=(
                f"job {job.kind!r} exhausted its {limit} attempts on the last "
                f"failure ({outcome.failure_class.value}: {outcome.detail}). Grant "
                f"more by answering --raw "
                f"'{{\"{ATTEMPTS_GRANT_KEY}\": {limit + self._attempts_grant_step}}}', "
                "or fix the item by hand and answer anything to retry it once."
            ),
        )

    async def _failed_alike_after_requeue(self, job: JobRecord, outcome: Failure) -> bool:
        """Parks a requeued defect that failed the same way again, attempts left or not.

        A `defect` gate's requeue buys one run. A job parked on the ladder's exhaustion
        (build.implement) still has queue attempts left when it is requeued, and would
        otherwise spend them all on a failure already known not to change. Only while its
        latest gate is that answered defect gate: a new failure raises a new gate, so
        this applies to the requeued run alone. A different failure means the fix did
        something, and the job goes on within the attempts it has."""
        if self._defects is None:
            return False
        latest = await self._gates.latest_for_job(job.id, include_queue_gates=True)
        if latest is None or latest.kind != DEFECT_GATE_KIND or latest.answer is None:
            return False
        request = await self._defects.triage(job, self._exhausted_request(job, outcome))
        if request.kind != DEFECT_GATE_KIND:
            return False
        await self._raise_and_park(job, request)
        return True

    async def _triaged(self, job: JobRecord, request: HumanGateRequest) -> HumanGateRequest:
        """`request`, or the `defect` gate that replaces a grant when the job's recent
        failures were all one failure."""
        if self._defects is None:
            return request
        return await self._defects.triage(job, request)

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

    async def _raise_and_park(
        self,
        job: JobRecord,
        request: HumanGateRequest,
        *,
        created_gate: HumanGateRecord | None = None,
    ) -> None:
        # The gate is raised before the lease is released, so there is
        # never a window where the job looks claimable again before the
        # human_gate row exists to explain why it is parked.
        #
        # Some handlers raise their gate themselves before returning Park. They
        # return that record in the outcome so this seam can notify the newly
        # created gate exactly once; an already-open gate from an earlier run is
        # deliberately not notified again.
        gate = created_gate
        if gate is None:
            existing = await self._gates.latest_for_job(job.id, include_queue_gates=True)
            if existing is None or existing.answer is not None:
                gate = await self._gates.raise_gate(job.project_id, job.id, request)
        if gate is not None:
            await self._gate_notices.deliver(
                gate, notice=RAISED_NOTICE, config=self._notification_config
            )
        parked = await self._jobs.park(job.id, owner=self._owner)
        self._landed(parked, event="job.park_rejected", job=job)

    def _record_queue_latency(self, job: JobRecord, claimed_at: datetime) -> None:
        if self._metrics is None:
            return
        phase = job.phase if isinstance(job.phase, Phase) else job.phase.value
        with contextlib.suppress(Exception):
            self._metrics.record_queue_latency(
                job.project_id,
                phase,
                job.kind,
                max((claimed_at - job.created_at).total_seconds(), 0.0),
            )

    def _record_phase_duration(self, job: JobRecord, started_at: datetime) -> None:
        if self._metrics is None:
            return
        phase = job.phase if isinstance(job.phase, Phase) else job.phase.value
        with contextlib.suppress(Exception):
            self._metrics.record_phase_duration(
                job.project_id,
                job.cycle,
                phase,
                max((datetime.now(UTC) - started_at).total_seconds(), 0.0),
            )

    def _job_span(self, job: JobRecord) -> contextlib.AbstractContextManager[TelemetrySpan | None]:
        if self._tracer is None:
            return contextlib.nullcontext(None)
        phase = job.phase if isinstance(job.phase, Phase) else job.phase.value
        return cast(
            contextlib.AbstractContextManager[TelemetrySpan | None],
            self._tracer.trace_job(
                project_id=job.project_id,
                cycle=job.cycle,
                phase=phase,
                job_kind=job.kind,
            ),
        )

    async def _heartbeat_forever(self, job: JobRecord, *, lease: timedelta) -> None:
        """Keeps the lease alive while the handler runs.

        Nothing this loop meets may escape it. `run_once` awaits the task in
        its `finally`, so an exception stored here used to re-raise there:
        `_settle` was never reached, a finished -- and paid-for -- session was
        never acked, and the exception took the worker process down, with
        every parallel drive loop in it (#211). A beat that fails is a
        transient, said by `_beat` and retried at the next interval; beating
        at a third of the lease leaves room to miss one. A beat the queue
        *refuses* is different: the lease is gone and the row may already be
        another worker's, so there is nothing left to keep alive -- stop.
        """
        interval = lease.total_seconds() / 3
        try:
            while True:
                await asyncio.sleep(interval)
                if await self._beat(job, lease=lease) is False:
                    return
        except asyncio.CancelledError:
            pass

    async def _beat(self, job: JobRecord, *, lease: timedelta) -> bool | None:
        """One lease extension, which never raises.

        True: extended. False: refused -- this worker no longer holds the
        lease (said at warning as `job.lease_lost`). None: the call itself
        failed (a pool timeout, a failover), so whether the lease is still
        held is unknown; said at warning as `job.heartbeat_failed`, and the
        next beat finds out.
        """
        try:
            held = await self._jobs.heartbeat(job.id, owner=self._owner, lease=lease)
        except Exception as exc:  # noqa: BLE001 - a transient fault must not reach the settle path
            self._log.warning("job.heartbeat_failed", **self._job_fields(job), error=repr(exc))
            return None
        return self._landed(held, event="job.lease_lost", job=job)

    def _landed(self, applied: bool, *, event: str, job: JobRecord) -> bool:
        """Says so when a lease-guarded queue write did not land, and hands
        the answer back so the caller can stop.

        Every write this loop makes to a claimed job -- heartbeat, ack, nack,
        grant, park, defer -- is guarded on the lease and reports whether it
        took. False means the lease expired mid-handler and the row has been
        reaped or claimed by another worker: the transition did not happen,
        and on a settle the work this worker just did is discarded. That is
        said at warning, never raised: raising would kill the worker process,
        and every parallel drive loop in it, over a job that is no longer this
        worker's to settle.
        """
        if not applied:
            self._log.warning(
                event, **self._job_fields(job), reason="lease no longer held by this worker"
            )
        return applied

    @staticmethod
    def _job_fields(job: JobRecord) -> dict[str, str]:
        """The coordinates every line about a job carries."""
        return {
            "job_id": str(job.id),
            "project_id": str(job.project_id),
            "phase": job.phase.value,
            "kind": job.kind,
        }


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
