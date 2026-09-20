# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import logging
from collections.abc import Collection, Mapping, Sequence
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey.application.dto import HumanGateRequest, JobRecord
from vibey.application.interfaces.worker_interface import WorkerLoopInterface
from vibey.application.worker import (
    CapacityDeferred,
    Defer,
    Failure,
    Outcome,
    Park,
    Success,
    WorkerLoop,
)
from vibey.domain.job import FailureClass, JobState
from vibey.infrastructure.otel import TelemetryMetrics, TelemetryTracer

PROJECT_ID = uuid4()


class _FixedHandler:
    def __init__(self, outcome: Outcome | Exception) -> None:
        self._outcome = outcome
        self.received: JobRecord | None = None

    async def handle(self, job: JobRecord) -> Outcome:
        self.received = job
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome


class _SlowHandler:
    def __init__(self, delay: float, outcome: Outcome) -> None:
        self._delay = delay
        self._outcome = outcome

    async def handle(self, job: JobRecord) -> Outcome:
        await asyncio.sleep(self._delay)
        return self._outcome


class _RecordingNotifications:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def notify(self, **kwargs: object) -> dict[str, object]:
        self.calls.append(kwargs)
        return {"enabled": True}


def test_the_worker_loop_satisfies_its_declared_seam() -> None:
    """ADR-0016: the class and its interface stay in step."""
    loop = WorkerLoop(
        jobs=FakeJobRepository([]),
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Success()),
        owner="w1",
    )

    assert isinstance(loop, WorkerLoopInterface)


async def test_run_once_returns_false_when_nothing_claimable() -> None:
    jobs = FakeJobRepository([])
    gates = FakeHumanGateRepository()
    loop = WorkerLoop(jobs=jobs, gates=gates, handler=_FixedHandler(Success()), owner="w1")

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is False


async def test_success_outcome_acks_the_job() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    handler = _FixedHandler(Success())
    loop = WorkerLoop(jobs=jobs, gates=gates, handler=handler, owner="w1")

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is True
    assert handler.received is not None
    assert handler.received.id == job.id
    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.SUCCEEDED


async def test_failure_outcome_nacks_with_class_and_detail() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    handler = _FixedHandler(Failure(FailureClass.WORK, "assertion failed"))
    loop = WorkerLoop(jobs=jobs, gates=gates, handler=handler, owner="w1")

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.READY
    assert record.last_error == {"class": "work", "detail": "assertion failed"}


async def test_exhausted_attempts_park_with_a_grant_instead_of_failing() -> None:
    """ADR-0024: a bounded ladder ends in a park that can grant more. The
    attempt bound used to end in `nack`'s state='failed' with no gate row at
    all -- the work item stopped and nobody was asked."""
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    handler = _FixedHandler(Failure(FailureClass.WORK, "boom"))
    loop = WorkerLoop(jobs=jobs, gates=gates, handler=handler, owner="w1")

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN
    assert jobs.calls[-1] == "park"
    assert "nack" not in jobs.calls

    assert len(gates.raised) == 1
    gate = gates.raised[0]
    assert gate.kind == "attempts_exhausted"
    assert gate.job_id == job.id
    # The park advertises the number to type, and says what actually broke.
    assert '{"max_attempts": 4}' in gate.prompt
    assert "boom" in gate.prompt


async def test_exhaustion_park_advertises_the_configured_grant_step() -> None:
    """The step is a key, not a literal (ADR-0018)."""
    job = make_job(PROJECT_ID, max_attempts=2)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
        attempts_grant_step=10,
    )

    # Burn the first attempt (a plain nack), then trip the bound.
    await loop.run_once(PROJECT_ID)
    await loop.run_once(PROJECT_ID)

    assert '{"max_attempts": 12}' in gates.raised[0].prompt


async def test_an_answered_grant_widens_the_bound_and_retries() -> None:
    """Without widening the row, the grant would be spent immediately: the
    repository decides 'failed' from the row's own max_attempts."""
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    raised = await gates.raise_gate(
        PROJECT_ID, job.id, HumanGateRequest(kind="attempts_exhausted", prompt="more?")
    )
    await gates.answer(raised.gate_id, answer={"max_attempts": 3}, answered_by="adam")
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.max_attempts == 3
    assert record.state is JobState.READY
    assert "grant_attempts" in jobs.calls
    assert jobs.calls[-1] == "nack"


async def test_an_answer_without_the_grant_key_parks_again() -> None:
    """A human who fixed the item by hand answers anything; that buys the one
    retry the un-park gives, not a wider bound."""
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    raised = await gates.raise_gate(
        PROJECT_ID, job.id, HumanGateRequest(kind="attempts_exhausted", prompt="more?")
    )
    await gates.answer(raised.gate_id, answer={"resolution": "fixed by hand"}, answered_by="adam")
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN
    assert "grant_attempts" not in jobs.calls
    # The answered gate must not suppress the fresh one, or the human is left
    # with nothing to answer.
    assert len(gates.raised) == 2


async def test_a_grant_no_wider_than_the_current_bound_parks_again() -> None:
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    raised = await gates.raise_gate(
        PROJECT_ID, job.id, HumanGateRequest(kind="attempts_exhausted", prompt="more?")
    )
    await gates.answer(raised.gate_id, answer={"max_attempts": 1}, answered_by="adam")
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN
    assert record.max_attempts == 1
    assert "grant_attempts" not in jobs.calls


async def test_exhaustion_does_not_duplicate_an_unanswered_gate() -> None:
    """A gate already open on this job is the one the human will answer;
    a second would leave the duplicate latest_for_job returns forever."""
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    await gates.raise_gate(
        PROJECT_ID, job.id, HumanGateRequest(kind="attempts_exhausted", prompt="more?")
    )
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    assert len(gates.raised) == 1
    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN


async def test_handler_exception_becomes_a_vibey_class_failure() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    handler = _FixedHandler(RuntimeError("unexpected"))
    loop = WorkerLoop(jobs=jobs, gates=gates, handler=handler, owner="w1")

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.last_error == {"class": "vibey", "detail": "unexpected"}


async def test_capacity_exception_defers_without_consuming_an_attempt() -> None:
    job = make_job(PROJECT_ID, attempts=2)
    jobs = FakeJobRepository([job])
    retry_at = datetime(2026, 8, 14, 20, 10, tzinfo=UTC)
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(CapacityDeferred(retry_at, "five-hour window exhausted")),
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.READY
    assert record.attempts == 2
    assert record.run_after == retry_at
    assert record.last_error == {
        "class": "capacity",
        "detail": "five-hour window exhausted",
    }


async def test_park_outcome_raises_the_gate_before_parking_the_job() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    request = HumanGateRequest(kind="approval", prompt="proceed?")
    handler = _FixedHandler(Park(request))
    loop = WorkerLoop(jobs=jobs, gates=gates, handler=handler, owner="w1")

    await loop.run_once(PROJECT_ID)

    assert gates.calls == ["raise_gate"]
    assert jobs.calls[-1] == "park"
    assert gates.raised[0].job_id == job.id
    assert gates.raised[0].prompt == "proceed?"

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.AWAITING_HUMAN


@pytest.mark.parametrize(
    ("kind", "expected_notification"),
    [
        ("approval", "human_gate_raised"),
        ("budget_exhausted", "budget_exceeded"),
    ],
)
async def test_new_gates_are_sent_to_the_configured_notification_sink(
    kind: str, expected_notification: str
) -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    notifications = _RecordingNotifications()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Park(HumanGateRequest(kind=kind, prompt="answer me"))),
        owner="w1",
        notifications=notifications,  # type: ignore[arg-type]
        notification_config={"notifications": {"enabled": True}},
    )

    await loop.run_once(PROJECT_ID)

    assert len(notifications.calls) == 1
    assert notifications.calls[0]["kind"] == expected_notification
    assert notifications.calls[0]["config"] == {"notifications": {"enabled": True}}
    assert notifications.calls[0]["payload"] == {
        "gate_id": str(gates.raised[0].gate_id),
        "gate_kind": kind,
        "job_id": str(job.id),
    }


async def test_notification_sink_failure_is_logged_without_losing_the_gate() -> None:
    class _FailingNotifications:
        async def notify(self, **kwargs: object) -> dict[str, object]:
            raise RuntimeError("desktop unavailable")

    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Park(HumanGateRequest(kind="approval", prompt="answer me"))),
        owner="w1",
        logger=logger,
        notifications=_FailingNotifications(),  # type: ignore[arg-type]
        notification_config={"notifications": {"enabled": True}},
    )

    await loop.run_once(PROJECT_ID)

    assert len(gates.raised) == 1
    assert [(level, event) for level, event, _ in logger.lines] == [
        ("warning", "notification.failed")
    ]
    assert logger.lines[0][2]["notification_kind"] == "human_gate_raised"
    assert logger.lines[0][2]["error"] == "RuntimeError('desktop unavailable')"


async def test_worker_records_queue_phase_and_job_telemetry() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    tracer = TelemetryTracer()
    metrics = TelemetryMetrics()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Success()),
        owner="w1",
        tracer=tracer,
        metrics=metrics,
    )

    await loop.run_once(PROJECT_ID)

    exported = metrics.export_metrics(PROJECT_ID)
    assert list(exported["queue_latencies"]) == ["build.implement"]
    assert list(exported["phase_durations"]) == ["build"]
    assert [span.name for span in tracer.get_finished_spans()] == ["job:build.implement"]
    assert tracer.get_finished_spans()[0].attributes["outcome"] == "Success"


async def test_worker_heartbeats_during_a_long_running_handler() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    handler = _SlowHandler(delay=0.05, outcome=Success())
    loop = WorkerLoop(
        jobs=jobs, gates=gates, handler=handler, owner="w1", lease=timedelta(seconds=0.03)
    )

    await loop.run_once(PROJECT_ID)

    assert jobs.calls.count("heartbeat") >= 1


async def test_heartbeat_task_is_cancelled_cleanly_after_settling() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    handler = _FixedHandler(Success())
    loop = WorkerLoop(
        jobs=jobs, gates=gates, handler=handler, owner="w1", lease=timedelta(seconds=10)
    )

    # Should return promptly rather than waiting out the (long) heartbeat interval.
    await asyncio.wait_for(loop.run_once(PROJECT_ID), timeout=1.0)


async def test_unknown_outcome_type_is_silently_ignored() -> None:
    """When _settle receives an outcome not matching any known type, the elif
    chain falls through without taking any action on the job."""

    class _UnknownOutcome:
        pass

    class _UnknownHandler:
        async def handle(self, job: JobRecord) -> object:
            return _UnknownOutcome()

    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_UnknownHandler(),  # type: ignore[arg-type]
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.LEASED


async def test_lease_for_kind_extends_the_lease_before_handling() -> None:
    """The kind isn't known until after the claim, so the loop claims at the
    short default and immediately heartbeats up to the kind's real lease."""
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Success()),
        owner="w1",
        lease=timedelta(seconds=30),
        lease_for_kind=lambda kind: timedelta(hours=2),
    )

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is True
    # claim, then the immediate extension heartbeat, then ack
    assert jobs.calls[:2] == ["claim", "heartbeat"]
    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.SUCCEEDED


async def test_lease_for_kind_matching_default_skips_the_extra_heartbeat() -> None:
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Success()),
        owner="w1",
        lease=timedelta(seconds=30),
        lease_for_kind=lambda kind: timedelta(seconds=30),
    )

    await loop.run_once(PROJECT_ID)

    assert "heartbeat" not in jobs.calls


async def test_park_does_not_duplicate_a_handler_raised_gate() -> None:
    """Handlers like review.collect raise their gate themselves before
    returning Park; _settle raising again would leave a duplicate unanswered
    gate that latest_for_job returns forever, re-parking the job no matter
    what the human answered."""
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()

    class _SelfRaisingHandler:
        async def handle(self, handled: JobRecord) -> Outcome:
            request = HumanGateRequest(kind="approval", prompt="ok?", options=("yes",))
            await gates.raise_gate(handled.project_id, handled.id, request)
            return Park(request)

    loop = WorkerLoop(jobs=jobs, gates=gates, handler=_SelfRaisingHandler(), owner="w1")

    await loop.run_once(PROJECT_ID)

    assert len(gates.raised) == 1


async def test_park_raises_a_fresh_gate_when_the_last_one_is_answered() -> None:
    """A staged interview parks again for its next question batch after the
    previous gate was answered -- the answered gate must not suppress the
    new raise."""
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    request = HumanGateRequest(kind="question", prompt="q-1?", options=())
    first = await gates.raise_gate(PROJECT_ID, job.id, request)
    await gates.answer(first.gate_id, answer={"answers": {"q-1": "a"}}, answered_by="t")

    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Park(HumanGateRequest(kind="question", prompt="q-2?", options=()))),
        owner="w1",
    )

    await loop.run_once(PROJECT_ID)

    assert len(gates.raised) == 2


class _RecordingLogger:
    """Captures what the loop said, so a test can assert on the line itself
    rather than on the side effect it was supposed to explain."""

    def __init__(self) -> None:
        self.lines: list[tuple[str, str, dict[str, object]]] = []

    def bind(self, **kwargs: object) -> "_RecordingLogger":
        return self

    def debug(self, event: str, **kwargs: object) -> None:
        self.lines.append(("debug", event, dict(kwargs)))

    def info(self, event: str, **kwargs: object) -> None:
        self.lines.append(("info", event, dict(kwargs)))

    def warning(self, event: str, **kwargs: object) -> None:
        self.lines.append(("warning", event, dict(kwargs)))

    def error(self, event: str, **kwargs: object) -> None:
        self.lines.append(("error", event, dict(kwargs)))


async def test_capacity_defer_is_logged_with_the_reason_and_the_retry_time() -> None:
    """The livelock this fixes was invisible: 0 failed, 0 parked, and a job
    quietly sliding its run_after. A defer has to say why, and until when."""
    job = replace(make_job(PROJECT_ID, attempts=2), work_item_id="WI-7")
    jobs = FakeJobRepository([job])
    retry_at = datetime(2026, 8, 14, 20, 10, tzinfo=UTC)
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(CapacityDeferred(retry_at, "no engine had capacity")),
        owner="w1",
        logger=logger,
    )

    await loop.run_once(PROJECT_ID)

    assert logger.lines == [
        (
            "warning",
            "job.deferred",
            {
                "job_id": str(job.id),
                "project_id": str(PROJECT_ID),
                "phase": "build",
                "kind": "build.implement",
                "work_item": "WI-7",
                "capacity": True,
                "reason": "no engine had capacity",
                "retry_at": retry_at.isoformat(),
            },
        )
    ]


async def test_non_capacity_defer_is_logged_at_info_not_warning() -> None:
    """Verify-repair waits are Defers too; logging every one of them at
    WARNING is how a warning stops being read at all."""
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    retry_at = datetime(2026, 8, 14, 20, 10, tzinfo=UTC)
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Defer(retry_at, "waiting on the repair window")),
        owner="w1",
        logger=logger,
    )

    await loop.run_once(PROJECT_ID)

    assert [(level, event) for level, event, _ in logger.lines] == [("info", "job.deferred")]
    assert logger.lines[0][2]["capacity"] is False


async def test_a_defer_the_queue_refused_is_never_announced_as_one() -> None:
    """The announcement follows the transition; it does not precede it.

    `defer` returns False when the lease expired mid-handler and another worker
    claimed the row: nothing moved, and a `job.deferred` line would assert a
    `retry_at` the job never took. A reader chasing that line would find a
    run_after disagreeing with the log -- a false record, which is worse than the
    silence this whole block exists to end. The true thing is that this worker
    lost the job, and it is said at warning because the work it just did was
    discarded.
    """

    class LostLeaseJobRepository(FakeJobRepository):
        async def defer(self, job_id, *, owner, retry_at, error) -> bool:
            self.calls.append("defer")
            return False

    job = make_job(PROJECT_ID)
    jobs = LostLeaseJobRepository([job])
    retry_at = datetime(2026, 8, 14, 20, 10, tzinfo=UTC)
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(CapacityDeferred(retry_at, "no engine had capacity")),
        owner="w1",
        logger=logger,
    )

    await loop.run_once(PROJECT_ID)

    assert [(level, event) for level, event, _ in logger.lines] == [
        ("warning", "job.defer_rejected")
    ]
    assert "job.deferred" not in [event for _, event, _ in logger.lines]
    assert logger.lines[0][2]["reason"] == "lease no longer held by this worker"
    # The transition was still attempted -- the guard is on the announcement.
    assert "defer" in jobs.calls


async def test_a_worker_with_no_injected_logger_still_speaks(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Until a composition root injects the structlog adapter, the default
    stdlib-backed logger is what keeps a deferring worker from looking idle."""
    job = make_job(PROJECT_ID)
    jobs = FakeJobRepository([job])
    retry_at = datetime(2026, 8, 14, 20, 10, tzinfo=UTC)
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(CapacityDeferred(retry_at, "five-hour window exhausted")),
        owner="w1",
    )

    with caplog.at_level(logging.WARNING, logger="vibey.application.worker"):
        await loop.run_once(PROJECT_ID)

    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert message.startswith("job.deferred ")
    assert "reason=five-hour window exhausted" in message
    assert f"retry_at={retry_at.isoformat()}" in message
    assert "owner=w1" in message


class _FlakyQueue(FakeJobRepository):
    """The shared fake, with the two ways a real queue lets a worker down (#211).

    ``beats`` scripts the first heartbeats, consumed in order: an exception is
    raised, as a pool timeout or a Postgres failover would; a bool is returned
    as-is. Once the script runs out the fake beats normally. ``refuse`` names
    the lease-guarded writes that report False, as Postgres does once this
    worker's lease has expired and the row is someone else's.
    """

    def __init__(
        self,
        jobs: list[JobRecord],
        *,
        beats: Sequence[bool | Exception] = (),
        refuse: Collection[str] = (),
    ) -> None:
        super().__init__(jobs)
        self._beats = list(beats)
        self._refuse = frozenset(refuse)

    def _refused(self, name: str) -> bool:
        if name not in self._refuse:
            return False
        self.calls.append(name)
        return True

    async def heartbeat(self, job_id: UUID, *, owner: str, lease: timedelta) -> bool:
        if not self._beats:
            return await super().heartbeat(job_id, owner=owner, lease=lease)
        self.calls.append("heartbeat")
        beat = self._beats.pop(0)
        if isinstance(beat, Exception):
            raise beat
        return beat

    async def ack(self, job_id: UUID, *, owner: str) -> bool:
        return False if self._refused("ack") else await super().ack(job_id, owner=owner)

    async def nack(self, job_id: UUID, *, owner: str, error: Mapping[str, object]) -> bool:
        if self._refused("nack"):
            return False
        return await super().nack(job_id, owner=owner, error=error)

    async def grant_attempts(self, job_id: UUID, *, owner: str, max_attempts: int) -> bool:
        if self._refused("grant_attempts"):
            return False
        return await super().grant_attempts(job_id, owner=owner, max_attempts=max_attempts)

    async def park(self, job_id: UUID, *, owner: str) -> bool:
        return False if self._refused("park") else await super().park(job_id, owner=owner)


class _UntilBeaten:
    """Returns its outcome only once the loop has heartbeat ``beats`` times, so
    a test waits on the behaviour it asserts rather than on the wall clock."""

    def __init__(self, jobs: FakeJobRepository, *, beats: int, outcome: Outcome) -> None:
        self._jobs = jobs
        self._beats = beats
        self._outcome = outcome

    async def handle(self, job: JobRecord) -> Outcome:
        while self._jobs.calls.count("heartbeat") < self._beats:
            await asyncio.sleep(0.001)
        return self._outcome


def _fields(job: JobRecord) -> dict[str, object]:
    return {
        "job_id": str(job.id),
        "project_id": str(job.project_id),
        "phase": job.phase.value,
        "kind": job.kind,
    }


_LOST = "lease no longer held by this worker"
_SHORT_LEASE = timedelta(seconds=0.03)


async def test_a_heartbeat_that_raises_mid_handler_still_acks_the_finished_job() -> None:
    """#211: the heartbeat task used to die on the exception, and `run_once`
    re-raised it from its `finally` -- `_settle` never ran, a finished (paid)
    session was never acked, and the worker process went down with it."""
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], beats=[ConnectionError("pool timeout")])
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_UntilBeaten(jobs, beats=1, outcome=Success()),
        owner="w1",
        lease=_SHORT_LEASE,
        logger=logger,
    )

    claimed = await asyncio.wait_for(loop.run_once(PROJECT_ID), timeout=5.0)

    assert claimed is True
    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.SUCCEEDED
    assert logger.lines == [
        (
            "warning",
            "job.heartbeat_failed",
            {**_fields(job), "error": repr(ConnectionError("pool timeout"))},
        )
    ]


async def test_a_heartbeat_that_fails_once_keeps_beating_after() -> None:
    """A failed beat is a transient: the loop logs it and carries on, so the
    lease is still kept alive once the database comes back."""
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], beats=[TimeoutError()])
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_UntilBeaten(jobs, beats=3, outcome=Success()),
        owner="w1",
        lease=_SHORT_LEASE,
        logger=logger,
    )

    await asyncio.wait_for(loop.run_once(PROJECT_ID), timeout=5.0)

    assert jobs.calls.count("heartbeat") >= 3
    assert [(level, event) for level, event, _ in logger.lines] == [
        ("warning", "job.heartbeat_failed")
    ]
    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.SUCCEEDED


async def test_a_refused_heartbeat_stops_beating_and_the_refused_ack_is_said() -> None:
    """A refused beat means the lease is gone: say so once and stop beating a
    row that may already be another worker's. The ack that follows is refused
    by the same guard, and that is said too -- not raised, which would kill
    the worker and every parallel drive loop in it."""
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], beats=[False], refuse={"ack"})
    logger = _RecordingLogger()

    class _OutlivesTheLease:
        async def handle(self, handled: JobRecord) -> Outcome:
            while "heartbeat" not in jobs.calls:
                await asyncio.sleep(0.001)
            # Ten more beat intervals: a loop that kept beating would show it.
            await asyncio.sleep(_SHORT_LEASE.total_seconds() / 3 * 10)
            return Success()

    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_OutlivesTheLease(),
        owner="w1",
        lease=_SHORT_LEASE,
        logger=logger,
    )

    claimed = await asyncio.wait_for(loop.run_once(PROJECT_ID), timeout=5.0)

    assert claimed is True
    assert jobs.calls.count("heartbeat") == 1
    assert logger.lines == [
        ("warning", "job.lease_lost", {**_fields(job), "reason": _LOST}),
        ("warning", "job.ack_rejected", {**_fields(job), "reason": _LOST}),
    ]


async def test_the_heartbeat_loop_ends_on_its_own_once_the_lease_is_refused() -> None:
    """Stopping is the loop's own doing, not the cancellation's: it returns
    without ever being cancelled."""
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], beats=[True, False])
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Success()),
        owner="w1",
        logger=_RecordingLogger(),
    )

    await asyncio.wait_for(loop._heartbeat_forever(job, lease=_SHORT_LEASE), timeout=5.0)

    assert jobs.calls == ["heartbeat", "heartbeat"]


async def test_a_nack_the_queue_refused_is_said_not_raised() -> None:
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], refuse={"nack"})
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
        logger=logger,
    )

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is True
    assert jobs.calls[-1] == "nack"
    assert logger.lines == [("warning", "job.nack_rejected", {**_fields(job), "reason": _LOST})]


async def test_a_refused_grant_skips_the_nack() -> None:
    """The grant always widens the bound (granted > attempts >= max_attempts),
    so its refusal can only mean the lease is gone. A nack without the grant
    would be the 'failed' dead end ADR-0024 rejects -- so it is not sent."""
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = _FlakyQueue([job], refuse={"grant_attempts"})
    gates = FakeHumanGateRepository()
    raised = await gates.raise_gate(
        PROJECT_ID, job.id, HumanGateRequest(kind="attempts_exhausted", prompt="more?")
    )
    await gates.answer(raised.gate_id, answer={"max_attempts": 3}, answered_by="adam")
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
        logger=logger,
    )

    await loop.run_once(PROJECT_ID)

    assert jobs.calls[-1] == "grant_attempts"
    assert "nack" not in jobs.calls
    assert logger.lines == [("warning", "job.grant_rejected", {**_fields(job), "reason": _LOST})]


async def test_a_nack_refused_after_a_granted_widening_is_said() -> None:
    job = make_job(PROJECT_ID, max_attempts=1)
    jobs = _FlakyQueue([job], refuse={"nack"})
    gates = FakeHumanGateRepository()
    raised = await gates.raise_gate(
        PROJECT_ID, job.id, HumanGateRequest(kind="attempts_exhausted", prompt="more?")
    )
    await gates.answer(raised.gate_id, answer={"max_attempts": 3}, answered_by="adam")
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Failure(FailureClass.WORK, "boom")),
        owner="w1",
        logger=logger,
    )

    await loop.run_once(PROJECT_ID)

    assert jobs.calls[-2:] == ["grant_attempts", "nack"]
    assert logger.lines == [("warning", "job.nack_rejected", {**_fields(job), "reason": _LOST})]


async def test_a_park_the_queue_refused_is_said_not_raised() -> None:
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], refuse={"park"})
    gates = FakeHumanGateRepository()
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=gates,
        handler=_FixedHandler(Park(HumanGateRequest(kind="approval", prompt="proceed?"))),
        owner="w1",
        logger=logger,
    )

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is True
    assert jobs.calls[-1] == "park"
    assert logger.lines == [("warning", "job.park_rejected", {**_fields(job), "reason": _LOST})]


async def test_an_initial_lease_extension_that_raises_carries_on_at_the_default() -> None:
    """The per-kind extension is a heartbeat like any other: a failure is
    said, and the job runs on at the default lease the claim took."""
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], beats=[ConnectionError("failover")])
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Success()),
        owner="w1",
        lease=timedelta(seconds=30),
        lease_for_kind=lambda kind: timedelta(hours=2),
        logger=logger,
    )

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is True
    assert jobs.calls[:2] == ["claim", "heartbeat"]
    record = await jobs.get(job.id)
    assert record is not None
    assert record.state is JobState.SUCCEEDED
    assert logger.lines == [
        (
            "warning",
            "job.heartbeat_failed",
            {**_fields(job), "error": repr(ConnectionError("failover"))},
        )
    ]


async def test_an_initial_lease_extension_that_is_refused_is_said() -> None:
    job = make_job(PROJECT_ID)
    jobs = _FlakyQueue([job], beats=[False])
    logger = _RecordingLogger()
    loop = WorkerLoop(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        handler=_FixedHandler(Success()),
        owner="w1",
        lease=timedelta(seconds=30),
        lease_for_kind=lambda kind: timedelta(hours=2),
        logger=logger,
    )

    claimed = await loop.run_once(PROJECT_ID)

    assert claimed is True
    assert logger.lines == [("warning", "job.lease_lost", {**_fields(job), "reason": _LOST})]
