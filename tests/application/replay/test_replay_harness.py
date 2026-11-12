# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The replay assertion itself is held to account: it passes a handler whose replay is
harmless and fails one whose replay is not, even when a COUNT would not notice."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from tests.application.replay.harness import (
    CallBatches,
    ContentLedger,
    EntryBatches,
    ReplayCase,
    ReplayRig,
    assert_replay_is_idempotent,
    jobs_content,
    outcome_content,
)
from vibey.application.dto import EngineEvent, EnqueueRequest, HumanGateRequest, JobRecord
from vibey.application.worker import Defer, Park, Success
from vibey.domain.job import idempotency_key
from vibey.domain.phase import Phase


class _ToyHandler:
    """Enqueues a follow-up. ``idempotent`` keys it by the job (a replay finds the row);
    otherwise it keys it by a fresh uuid, so every delivery adds a row."""

    def __init__(self, jobs: FakeJobRepository, *, idempotent: bool) -> None:
        self._jobs = jobs
        self._idempotent = idempotent

    async def handle(self, job: JobRecord) -> Success:
        key = (
            idempotency_key(job.project_id, job.cycle, "toy.follow", str(job.id))
            if self._idempotent
            else f"toy-{uuid4()}"
        )
        await self._jobs.enqueue(
            EnqueueRequest(
                project_id=job.project_id,
                cycle=job.cycle,
                phase=Phase.BUILD,
                kind="toy.follow",
                idempotency_key=key,
            )
        )
        return Success({})


class _ToyByAttempt:
    """Enqueues a follow-up whose payload carries ``job.attempts``: harmless on a first
    delivery, different on a real redelivery (which arrives as attempt 2)."""

    def __init__(self, jobs: FakeJobRepository) -> None:
        self._jobs = jobs

    async def handle(self, job: JobRecord) -> Success:
        follow = EnqueueRequest(
            project_id=job.project_id,
            cycle=job.cycle,
            phase=Phase.BUILD,
            kind="toy.follow",
            idempotency_key="toy-one",
            payload={"attempt": job.attempts},
        )
        existing = [row for row, _ in self._jobs.rows() if row.kind == "toy.follow"]
        if existing:
            self._jobs._jobs[existing[0].id] = replace(existing[0], payload=follow.payload)
        else:
            await self._jobs.enqueue(follow)
        return Success({})


def _case(make_handler) -> ReplayCase:  # type: ignore[no-untyped-def]
    def build(scratch: Path) -> ReplayRig:
        job = replace(make_job(uuid4()), kind="toy.in")
        jobs = FakeJobRepository([job])
        return ReplayRig(
            handler=make_handler(jobs),
            job=job,
            jobs=jobs,
            snapshot=lambda: {"jobs": jobs_content(jobs, job.id)},
            redeliver=lambda: make_handler(jobs),
        )

    return ReplayCase(name="toy", kind="toy", build=build)


async def test_an_idempotent_handler_passes(tmp_path: Path) -> None:
    await assert_replay_is_idempotent(
        _case(lambda jobs: _ToyHandler(jobs, idempotent=True)), tmp_path
    )


async def test_a_handler_that_adds_a_row_per_delivery_fails(tmp_path: Path) -> None:
    with pytest.raises(AssertionError, match="a redelivery changed"):
        await assert_replay_is_idempotent(
            _case(lambda jobs: _ToyHandler(jobs, idempotent=False)), tmp_path
        )


async def test_a_handler_that_behaves_differently_on_attempt_two_fails(tmp_path: Path) -> None:
    """One row after each delivery (a count passes) but its payload follows ``job.attempts``:
    only a redelivery that really arrives as attempt 2 sees it."""
    with pytest.raises(AssertionError, match="attempt"):
        await assert_replay_is_idempotent(_case(_ToyByAttempt), tmp_path)


async def test_the_redelivery_is_a_real_lease_expiry(tmp_path: Path) -> None:
    seen: list[tuple[int, str | None]] = []

    class Recorder(_ToyHandler):
        async def handle(self, job: JobRecord) -> Success:
            seen.append((job.attempts, job.lease_owner))
            return await super().handle(job)

    await assert_replay_is_idempotent(_case(lambda jobs: Recorder(jobs, idempotent=True)), tmp_path)

    assert seen == [(1, "worker-1"), (2, "worker-2")]


async def test_an_empty_snapshot_fails(tmp_path: Path) -> None:
    def build(scratch: Path) -> ReplayRig:
        job = replace(make_job(uuid4()), kind="toy.in")
        jobs = FakeJobRepository([job])
        return ReplayRig(
            handler=_ToyHandler(jobs, idempotent=True),
            job=job,
            jobs=jobs,
            snapshot=lambda: {"ledger": [], "jobs": []},
            redeliver=lambda: _ToyHandler(jobs, idempotent=True),
        )

    with pytest.raises(AssertionError, match="left nothing to compare"):
        await assert_replay_is_idempotent(ReplayCase("empty", "toy", build), tmp_path)


# ---- the ledger comparison -------------------------------------------------------------


_PID = uuid4()


def _record(ledger: ContentLedger, kind: str, *, run=None, payload=None):  # type: ignore[no-untyped-def]
    event = EngineEvent(kind=kind, at=datetime(2026, 1, 1, tzinfo=UTC), payload=payload or {})
    pid = _PID
    return ledger.record(
        project_id=pid,
        cycle=1,
        job_id=pid,
        engine_id=None,
        correlation_id=pid,
        event=event,
        causation_id=run,
    )


async def test_a_handler_writing_one_entry_twice_in_a_delivery_is_visible() -> None:
    once, twice = ContentLedger(), ContentLedger()
    pid = uuid4()
    for ledger, times in ((once, 1), (twice, 2)):
        for _ in range(times):
            await ledger.record(
                project_id=pid,
                cycle=1,
                job_id=pid,
                engine_id=None,
                correlation_id=pid,
                event=EngineEvent("A", datetime(2026, 1, 1, tzinfo=UTC), {}),
            )
    assert once.after_delivery() != twice.after_delivery()


async def test_the_same_entries_restated_on_a_redelivery_are_allowed() -> None:
    ledger = ContentLedger()
    for _ in range(2):
        run = uuid4()
        await _record(ledger, "A", payload={"x": 1})
        await _record(ledger, "Run", run=run, payload={"summary": f"run {run} done"})
        content = ledger.after_delivery()
    assert content["unmatched"] == []


async def test_a_new_or_different_entry_on_a_redelivery_is_reported() -> None:
    ledger = ContentLedger()
    await _record(ledger, "A", payload={"x": 1})
    first = ledger.after_delivery()
    await _record(ledger, "A", payload={"x": 2})
    second = ledger.after_delivery()
    assert first["unmatched"] == []
    assert second["unmatched"] != []


async def test_a_run_whose_content_differs_on_a_redelivery_is_reported() -> None:
    ledger = ContentLedger()
    await _record(ledger, "Run", run=uuid4(), payload={"complete": True})
    ledger.after_delivery()
    await _record(ledger, "Run", run=uuid4(), payload={"complete": False})
    assert ledger.after_delivery()["unmatched"] != []


def test_entry_batches_allow_a_restatement_and_report_anything_else() -> None:
    batches = EntryBatches()
    batches.add({"kind": "A", "n": 1})
    first = batches.after_delivery()
    batches.add({"kind": "A", "n": 1})
    assert batches.after_delivery()["unmatched"] == []
    batches.add({"kind": "A", "n": 1})
    batches.add({"kind": "A", "n": 1})
    assert batches.after_delivery()["unmatched"] != []  # more often than the first wrote it
    batches.add({"kind": "B", "n": 1})
    assert batches.after_delivery()["unmatched"] != []  # an entry the first never wrote
    assert first["unmatched"] == []
    assert first["own"] == [(repr({"kind": "A", "n": 1}), 1)]


def test_entry_batches_see_one_entry_written_twice_in_a_single_delivery() -> None:
    once, twice = EntryBatches(), EntryBatches()
    once.add({"kind": "A"})
    twice.add({"kind": "A"})
    twice.add({"kind": "A"})
    assert once.after_delivery() != twice.after_delivery()


def test_a_park_is_compared_by_its_request_not_by_the_gate_record_it_carries() -> None:
    request = HumanGateRequest(kind="k", prompt="p")
    assert outcome_content(Park(request)) == outcome_content(Park(request))
    assert outcome_content(Park(request)) != outcome_content(
        Park(HumanGateRequest(kind="k", prompt="another prompt"))
    )


def test_call_batches_compare_the_ordered_calls_of_each_delivery() -> None:
    calls: list[str] = []
    batches = CallBatches(lambda: calls, expected_first=["a", "b"])
    calls += ["a", "b"]
    first = batches.after_delivery()
    calls += ["a", "b"]
    assert batches.after_delivery()["unmatched"] == []
    calls += ["b", "a"]  # the same steps in another order
    assert batches.after_delivery()["unmatched"] != []
    calls += ["a", "b", "b"]  # a double call
    assert batches.after_delivery()["unmatched"] != []
    assert first["first"] == [repr("a"), repr("b")]


def test_call_batches_pin_the_first_delivery_when_told_to() -> None:
    calls = ["a", "a"]  # a double call inside the first delivery
    with pytest.raises(AssertionError):
        CallBatches(lambda: calls, expected_first=["a"]).after_delivery()


def test_a_defer_is_compared_by_its_time_and_class_not_its_prose() -> None:
    at = datetime(2026, 1, 1, tzinfo=UTC)
    assert outcome_content(Defer(at, "repair enqueued")) == outcome_content(
        Defer(at, "repair in flight")
    )
    assert outcome_content(Defer(at, "x")) != outcome_content(Defer(at + timedelta(minutes=1), "x"))
    assert outcome_content(Defer(at, "x")) != outcome_content(Defer(at, "x", capacity=True))


async def test_a_handler_that_raises_its_own_gate_must_snapshot_its_gates(tmp_path: Path) -> None:
    class _Gated:
        async def handle(self, job: JobRecord) -> Park:
            gate = object()
            return Park(HumanGateRequest(kind="k", prompt="p"), gate=gate)  # type: ignore[arg-type]

    def build(scratch: Path) -> ReplayRig:
        jobs = FakeJobRepository([job := replace(make_job(uuid4()), kind="toy")])
        return ReplayRig(
            handler=_Gated(),
            job=job,
            jobs=jobs,
            redeliver=_Gated,
            snapshot=lambda: {"jobs": jobs_content(jobs, job.id)},
        )

    with pytest.raises(AssertionError, match="gate rows"):
        await assert_replay_is_idempotent(ReplayCase(name="n", kind="k", build=build), tmp_path)
