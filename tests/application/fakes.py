# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory fakes for application/ports.py, used to unit test worker.py
without a database (real-DB behavior is covered separately against
Postgres in tests/infrastructure/db/)."""

from collections.abc import Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from vibey.application.dto import (
    EnqueueRequest,
    GateAnswerOutcome,
    HumanGateRecord,
    HumanGateRequest,
    JobRecord,
)
from vibey.application.interfaces.queue import JobHandler, Outcome
from vibey.domain.engine import EngineId
from vibey.domain.errors import GateAlreadyAnswered, UnknownGate
from vibey.domain.job import QUEUE_GATE_KINDS, JobState, StoredJobState
from vibey.domain.phase import Phase


class FakeJobRepository:
    def __init__(self, jobs: list[JobRecord] | None = None) -> None:
        self._jobs: dict[UUID, JobRecord] = {j.id: j for j in (jobs or [])}
        self.calls: list[str] = []
        # job id -> the job ids it depends on, as `enqueue_batch` resolved them.
        self.dependencies: dict[UUID, tuple[UUID, ...]] = {}
        # Jobs a handler test runs without putting them in the queue (`adopt`): they exist for
        # the `job_dependency` foreign key but are not rows the test can list or claim.
        self._adopted: set[UUID] = set()

    async def enqueue(self, request: EnqueueRequest) -> JobRecord:
        """Idempotent on (project_id, idempotency_key), like the Postgres insert."""
        return self._enqueue_all([request])[0]

    async def enqueue_batch(self, requests: Sequence[EnqueueRequest]) -> tuple[JobRecord, ...]:
        """All-or-nothing and idempotent per request, like the Postgres batch:
        nothing lands until every request has resolved its dependency keys."""
        self.calls.append("enqueue_batch")
        return self._enqueue_all(requests)

    def _enqueue_all(self, requests: Sequence[EnqueueRequest]) -> tuple[JobRecord, ...]:
        by_key = {(job.project_id, job.idempotency_key): job for job in self._jobs.values()}
        staged: dict[UUID, JobRecord] = {}
        staged_dependencies: dict[UUID, tuple[UUID, ...]] = {}
        records: list[JobRecord] = []
        for request in requests:
            depends_on = [*request.depends_on]
            for dependency_id in depends_on:
                # The `job_dependency` foreign key: a dependency must be a job that exists.
                if (
                    dependency_id not in self._jobs
                    and dependency_id not in staged
                    and dependency_id not in self._adopted
                ):
                    raise LookupError(f"depends_on names unknown job {dependency_id}")
            for key in request.depends_on_keys:
                dependency = by_key.get((request.project_id, key))
                if dependency is None:
                    raise LookupError(f"depends_on_keys names unknown job {key!r}")
                depends_on.append(dependency.id)
            existing = by_key.get((request.project_id, request.idempotency_key))
            if existing is not None:
                records.append(existing)
                continue
            job = self._record(request)
            by_key[(job.project_id, job.idempotency_key)] = job
            staged[job.id] = job
            staged_dependencies[job.id] = tuple(depends_on)
            records.append(job)
        self._jobs.update(staged)
        self.dependencies.update(staged_dependencies)
        return tuple(records)

    async def list_for_cycle(
        self, project_id: UUID, *, cycle: int, kind: str
    ) -> tuple[JobRecord, ...]:
        return tuple(
            job
            for job in self._jobs.values()
            if job.project_id == project_id and job.cycle == cycle and job.kind == kind
        )

    def _record(self, request: EnqueueRequest) -> JobRecord:
        return JobRecord(
            id=uuid4(),
            project_id=request.project_id,
            cycle=request.cycle,
            phase=request.phase,
            kind=request.kind,
            state=JobState.READY,
            priority=0,
            work_item_id=request.work_item_id,
            payload=request.payload,
            requirement=request.requirement,
            idempotency_key=request.idempotency_key,
            attempts=0,
            max_attempts=request.max_attempts,
            run_after=request.run_after or datetime.now(UTC),
            lease_owner=None,
            lease_expires_at=None,
            assigned_engine=None,
            last_error=None,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )

    def _claimable(self) -> list[JobRecord]:
        """What `PostgresJobRepository._CLAIMABLE` admits, in its `_CLAIM_ORDER`: ready, due,
        every dependency succeeded; bumped jobs first (by place), then priority high to low,
        then the earlier due time, then id."""
        now = datetime.now(UTC)

        def dependencies_met(job: JobRecord) -> bool:
            return all(
                (dependency := self._jobs.get(dependency_id)) is not None
                and dependency.state is JobState.SUCCEEDED
                for dependency_id in self.dependencies.get(job.id, ())
            )

        due = [
            job
            for job in self._jobs.values()
            if job.state is JobState.READY and job.run_after <= now and dependencies_met(job)
        ]
        return sorted(
            due,
            key=lambda job: (
                job.bump_seq is None,
                job.bump_seq or 0,
                -job.priority,
                job.run_after,
                str(job.id),
            ),
        )

    async def claim(self, project_id: UUID, *, owner: str, lease: timedelta) -> JobRecord | None:
        self.calls.append("claim")
        for job in self._claimable():
            if job.project_id == project_id:
                return self.lease(job.id, owner=owner, lease=lease)
        return None

    def lease(self, job_id: UUID, *, owner: str, lease: timedelta) -> JobRecord:
        """What `claim` does to the row it picks: leased to `owner`, one more attempt. For a
        test that must lease a particular job, not whichever the queue would hand out."""
        job = self._jobs[job_id]
        leased = _with(
            job,
            state=JobState.LEASED,
            lease_owner=owner,
            lease_expires_at=datetime.now(UTC) + lease,
            attempts=job.attempts + 1,
        )
        self._jobs[job_id] = leased
        return leased

    def expire_lease(self, job_id: UUID) -> None:
        """The worker died: its lease lapses, so `reap` requeues the job."""
        job = self._jobs[job_id]
        self._jobs[job_id] = _with(job, lease_expires_at=datetime.now(UTC) - timedelta(seconds=1))

    def rows(self) -> tuple[tuple[JobRecord, tuple[UUID, ...]], ...]:
        """Every row of the queue with the ids it depends on (adopted jobs are not rows)."""
        return tuple((job, self.dependencies.get(job.id, ())) for job in self._jobs.values())

    def seed_leased(self, job: JobRecord) -> None:
        """Puts a job a handler is about to run into the repository as the leased job it is, so
        what the handler enqueues can depend on it (the `job_dependency` foreign key)."""
        if job.id not in self._jobs:
            self._jobs[job.id] = _with(
                job,
                state=JobState.LEASED,
                lease_owner="seeded-worker",
                lease_expires_at=datetime.now(UTC) + timedelta(hours=1),
            )

    def adopt(self, job: JobRecord) -> None:
        """Lets what a handler enqueues depend on `job` without making `job` a row of this
        queue: for the many handler tests that assert on the queue's contents."""
        self._adopted.add(job.id)

    def make_all_due(self) -> None:
        """Lets the backoff a nack scheduled pass, without a test sleeping through it."""
        now = datetime.now(UTC)
        self._jobs = {
            job_id: _with(job, run_after=min(job.run_after, now))
            for job_id, job in self._jobs.items()
        }

    async def claimable_projects(self) -> tuple[UUID, ...]:
        self.calls.append("claimable_projects")
        return tuple(dict.fromkeys(job.project_id for job in self._claimable()))

    async def heartbeat(self, job_id: UUID, *, owner: str, lease: timedelta) -> bool:
        self.calls.append("heartbeat")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner or job.state is not JobState.LEASED:
            return False
        self._jobs[job_id] = _with(job, lease_expires_at=datetime.now(UTC) + lease)
        return True

    async def ack(self, job_id: UUID, *, owner: str) -> bool:
        self.calls.append("ack")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner:
            return False
        self._jobs[job_id] = _with(
            job, state=JobState.SUCCEEDED, lease_owner=None, lease_expires_at=None
        )
        return True

    async def nack(self, job_id: UUID, *, owner: str, error: Mapping[str, object]) -> bool:
        self.calls.append("nack")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner:
            return False
        state = JobState.FAILED if job.attempts >= job.max_attempts else JobState.READY
        # Postgres: run_after = now() + least(2^attempts * 2s, 15min) * random(). The fake takes
        # the ceiling of that range, so it is deterministic and never earlier than the real one.
        backoff = min(timedelta(seconds=2 * 2**job.attempts), timedelta(minutes=15))
        self._jobs[job_id] = _with(
            job,
            state=state,
            lease_owner=None,
            lease_expires_at=None,
            run_after=datetime.now(UTC) + backoff,
            last_error=dict(error),
        )
        return True

    async def park(self, job_id: UUID, *, owner: str) -> bool:
        self.calls.append("park")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner:
            return False
        self._jobs[job_id] = _with(
            job,
            state=JobState.AWAITING_HUMAN,
            lease_owner=None,
            lease_expires_at=None,
            attempts=max(job.attempts - 1, 0),
        )
        return True

    async def grant_attempts(self, job_id: UUID, *, owner: str, max_attempts: int) -> bool:
        self.calls.append("grant_attempts")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner or job.max_attempts >= max_attempts:
            return False
        self._jobs[job_id] = _with(job, max_attempts=max_attempts)
        return True

    async def defer(
        self,
        job_id: UUID,
        *,
        owner: str,
        retry_at: datetime,
        error: Mapping[str, object],
    ) -> bool:
        self.calls.append("defer")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner:
            return False
        self._jobs[job_id] = _with(
            job,
            state=JobState.READY,
            lease_owner=None,
            lease_expires_at=None,
            attempts=max(job.attempts - 1, 0),
            run_after=retry_at,
            last_error=dict(error),
        )
        return True

    async def reap(self) -> int:
        """Every lapsed lease: requeued while attempts remain, parked once they are spent (one
        attempt refunded), as `PostgresQueueReapStore.reap_leases` does. The `delivery_exhausted`
        gate it also raises belongs to the gate store, not to this fake.

        In the store's order (`_EXPIRED`: `ORDER BY lease_expires_at, id`), and each at an
        instant of its own: the store reaps every lease in a transaction of its own, so each
        requeued job's `greatest(run_after, now())` is later than the one before, and the
        next claims hand them out in lapse order rather than by id."""
        now = datetime.now(UTC)
        lapsed = sorted(
            (
                job
                for job in self._jobs.values()
                if job.state is JobState.LEASED
                and job.lease_expires_at is not None
                and job.lease_expires_at < now
            ),
            key=lambda job: (job.lease_expires_at or now, str(job.id)),
        )
        tick = timedelta(microseconds=1)
        for job in lapsed:
            now = max(datetime.now(UTC), now + tick)
            if job.attempts >= job.max_attempts:
                self._jobs[job.id] = _with(
                    job,
                    state=JobState.AWAITING_HUMAN,
                    lease_owner=None,
                    lease_expires_at=None,
                    attempts=max(job.attempts - 1, 0),
                )
            else:
                self._jobs[job.id] = _with(
                    job,
                    state=JobState.READY,
                    lease_owner=None,
                    lease_expires_at=None,
                    run_after=max(job.run_after, now),
                )
        return len(lapsed)

    async def assign_engine(self, job_id: UUID, *, owner: str, engine_id: EngineId) -> bool:
        self.calls.append("assign_engine")
        job = self._jobs.get(job_id)
        if job is None or job.lease_owner != owner or job.state is not JobState.LEASED:
            return False
        self._jobs[job_id] = _with(job, assigned_engine=engine_id.value)
        return True

    async def count_unsettled(
        self, project_id: UUID, *, cycle: int, phase: Phase, exclude: UUID | None = None
    ) -> int:
        terminal = {JobState.SUCCEEDED, JobState.FAILED, JobState.CANCELLED}
        return sum(
            1
            for job in self._jobs.values()
            if job.project_id == project_id
            and job.cycle == cycle
            and job.phase is phase
            and job.state not in terminal
            and job.id != exclude
        )

    async def queue_depth(self, project_id: UUID) -> Mapping[StoredJobState, int]:
        from collections import Counter

        counts: Counter[StoredJobState] = Counter({state: 0 for state in JobState})
        for job in self._jobs.values():
            if job.project_id == project_id:
                counts[job.state] += 1
        return dict(counts)

    async def get(self, job_id: UUID) -> JobRecord | None:
        return self._jobs.get(job_id)


class FakeHumanGateRepository:
    def __init__(self) -> None:
        self.raised: list[HumanGateRecord] = []
        self.calls: list[str] = []
        self.accounts: dict[UUID, str | None] = {}

    async def raise_gate(
        self, project_id: UUID, job_id: UUID | None, request: HumanGateRequest
    ) -> HumanGateRecord:
        self.calls.append("raise_gate")
        record = HumanGateRecord(
            gate_id=uuid4(),
            project_id=project_id,
            job_id=job_id,
            kind=request.kind,
            prompt=request.prompt,
            options=request.options,
            default_answer=request.default_answer,
            answer=None,
            raised_at=datetime.now(UTC),
            timeout_at=request.timeout_at,
            answered_at=None,
            answered_by=None,
        )
        self.raised.append(record)
        return record

    async def answer(
        self,
        gate_id: UUID,
        *,
        answer: Mapping[str, object],
        answered_by: str,
        account: str | None = None,
        request_id: str | None = None,
    ) -> HumanGateRecord:
        outcome = await self.answer_once(
            gate_id,
            answer=answer,
            answered_by=answered_by,
            account=account,
            request_id=request_id if request_id is not None else str(uuid4()),
        )
        return outcome.record

    async def answer_once(
        self,
        gate_id: UUID,
        *,
        answer: Mapping[str, object],
        answered_by: str,
        account: str | None,
        request_id: str,
    ) -> GateAnswerOutcome:
        """The Postgres repository's compare-and-set, in memory: an open gate is answered
        once; the same request and answer again is a replay; anything else is refused."""
        self.calls.append("answer")
        existing = next((r for r in self.raised if r.gate_id == gate_id), None)
        if existing is None:
            raise UnknownGate(f"no gate {gate_id}")
        if existing.answered_at is not None:
            same_request = existing.answer_request_id == request_id
            if same_request and existing.answer == dict(answer):
                return GateAnswerOutcome(record=existing, replayed=True)
            raise GateAlreadyAnswered(
                gate_id,
                answered_by=existing.answered_by,
                answered_at=existing.answered_at,
                same_request=same_request,
            )
        answered = replace(
            existing,
            answer=dict(answer),
            answered_at=datetime.now(UTC),
            answered_by=answered_by,
            answer_request_id=request_id,
        )
        self.accounts[gate_id] = account
        self.raised = [answered if r.gate_id == gate_id else r for r in self.raised]
        return GateAnswerOutcome(record=answered)

    async def latest_for_job(
        self, job_id: UUID, *, include_queue_gates: bool = False
    ) -> HumanGateRecord | None:
        matching = [
            record
            for record in self.raised
            if record.job_id == job_id
            and (include_queue_gates or record.kind not in QUEUE_GATE_KINDS)
        ]
        return matching[-1] if matching else None

    async def open_for_project(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        return tuple(
            record
            for record in self.raised
            if record.project_id == project_id and record.answered_at is None
        )

    async def open_all(self) -> tuple[HumanGateRecord, ...]:
        return tuple(
            sorted(
                (record for record in self.raised if record.answered_at is None),
                key=lambda record: (record.raised_at, record.gate_id),
            )
        )


async def handle_leased(handler: JobHandler, job: JobRecord) -> Outcome:
    """Runs `handler` on `job` as a worker would: the job exists for the handler's repository. Handlers enqueue follow-ups that depend on their own job, and a dependency on a
    job that does not exist is refused (as Postgres refuses it)."""
    jobs = getattr(handler, "_jobs", None)
    if isinstance(jobs, FakeJobRepository):
        jobs.adopt(job)
    return await handler.handle(job)


def _with(job: JobRecord, **overrides: object) -> JobRecord:
    from dataclasses import replace

    return replace(job, **overrides)  # type: ignore[arg-type]


def make_job(
    project_id: UUID,
    *,
    state: JobState = JobState.READY,
    max_attempts: int = 7,
    attempts: int = 0,
) -> JobRecord:
    now = datetime.now(UTC)
    return JobRecord(
        id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        kind="build.implement",
        state=state,
        priority=0,
        work_item_id=None,
        payload={},
        requirement={},
        idempotency_key=f"key-{uuid4()}",
        attempts=attempts,
        max_attempts=max_attempts,
        run_after=now,
        lease_owner=None,
        lease_expires_at=None,
        assigned_engine=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
