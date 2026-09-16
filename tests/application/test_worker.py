# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
import logging
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey.application.dto import HumanGateRequest, JobRecord
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
