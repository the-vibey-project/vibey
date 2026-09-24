# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queue-priority service: the grant decides, the store moves (ADR-0054, 12.j)."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EnqueueRequest, QueueEntry
from vibey.application.interfaces import JobPriorityStore, QueuePriorityServiceInterface
from vibey.application.queue_priority import QueuePriorityService
from vibey.domain.errors import NotReorderable, PriorityRefused, UnknownJob
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.domain.queue_priority import (
    OPERATOR_SOURCE,
    MovedJob,
    PriorityAction,
    PriorityChange,
    PriorityGrant,
    PriorityRefusal,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
PROJECT = UUID(int=77)


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FakePriorityStore:
    """Records what it was asked. The real store is exercised against Postgres."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, UUID | None, str, PriorityAction]] = []
        self.refusals: list[PriorityRefusal] = []
        self.at: list[datetime] = []

    async def bump(
        self,
        job_id: UUID,
        *,
        source: str,
        at: datetime,
        action: PriorityAction = PriorityAction.BUMP,
    ) -> PriorityChange:
        self.calls.append(("bump", job_id, source, action))
        self.at.append(at)
        return PriorityChange(
            action=action,
            source=source,
            target=job_id,
            moved=(MovedJob(job_id=job_id, bump_seq=1, previous=None),),
        )

    async def unbump(self, job_id: UUID, *, source: str, at: datetime) -> PriorityChange:
        self.calls.append(("unbump", job_id, source, PriorityAction.UNBUMP))
        self.at.append(at)
        return PriorityChange(action=PriorityAction.UNBUMP, source=source, target=job_id, moved=())

    async def refuse(self, refusal: PriorityRefusal, *, at: datetime) -> None:
        self.refusals.append(refusal)
        self.at.append(at)

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        self.calls.append(("queue", project_id, "", PriorityAction.BUMP))
        return ()


def _request(subject: str = "x") -> EnqueueRequest:
    return EnqueueRequest(
        project_id=PROJECT,
        cycle=3,
        phase=Phase.REVIEW,
        kind="review.collect",
        idempotency_key=f"key-{subject}",
    )


def _service(
    jobs: FakeJobRepository, store: FakePriorityStore, *declared: str
) -> QueuePriorityService:
    return QueuePriorityService(
        jobs=jobs, store=store, grant=PriorityGrant(declared), clock=FixedClock()
    )


def test_the_fakes_and_the_service_satisfy_their_seams() -> None:
    store = FakePriorityStore()
    assert isinstance(store, JobPriorityStore)
    assert isinstance(_service(FakeJobRepository(), store), QueuePriorityServiceInterface)


async def test_the_operator_bumps_without_any_declaration() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()
    job = await jobs.enqueue(_request())

    change = await _service(jobs, store).bump(job.id)

    assert change.changed
    assert store.calls == [("bump", job.id, OPERATOR_SOURCE, PriorityAction.BUMP)]
    assert store.at == [NOW]
    assert store.refusals == []


async def test_a_declared_source_bumps_and_unbumps_under_its_own_name() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()
    job = await jobs.enqueue(_request())
    service = _service(jobs, store, "storm")

    await service.bump(job.id, source="storm")
    await service.unbump(job.id, source="storm")

    assert store.calls == [
        ("bump", job.id, "storm", PriorityAction.BUMP),
        ("unbump", job.id, "storm", PriorityAction.UNBUMP),
    ]


@pytest.mark.parametrize("action", ["bump", "unbump"])
async def test_an_undeclared_source_is_refused_and_the_refusal_is_recorded(action: str) -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()
    job = await jobs.enqueue(_request())
    service = _service(jobs, store, "storm")

    with pytest.raises(PriorityRefused) as caught:
        await getattr(service, action)(job.id, source="github-label")

    assert caught.value.source == "github-label"
    assert "[queue.priority] sources" in caught.value.reason
    assert store.calls == [], "a refused request moves nothing"
    (refusal,) = store.refusals
    assert refusal == PriorityRefusal(
        project_id=PROJECT,
        cycle=3,
        phase=Phase.REVIEW,
        job_id=job.id,
        action=PriorityAction(action),
        source="github-label",
        reason=caught.value.reason,
    )
    assert store.at == [NOW]


async def test_an_unknown_job_is_reported_before_anything_is_recorded() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()
    missing = uuid4()

    with pytest.raises(UnknownJob):
        await _service(jobs, store).bump(missing, source="anyone")
    with pytest.raises(UnknownJob):
        await _service(jobs, store).unbump(missing)
    assert store.calls == [] and store.refusals == []


async def test_a_job_in_a_phase_this_vibey_does_not_know_is_left_alone() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()
    job = await jobs.enqueue(_request())
    jobs._jobs[job.id] = replace(job, phase=UnrecognizedPhase("triage"))

    with pytest.raises(NotReorderable, match="triage"):
        await _service(jobs, store).bump(job.id)
    assert store.calls == [] and store.refusals == []


async def test_enqueue_with_priority_enqueues_then_bumps_what_it_made() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()

    job, change = await _service(jobs, store, "storm").enqueue(_request(), source="storm")

    assert await jobs.get(job.id) == job
    assert change.action is PriorityAction.ENQUEUE
    assert store.calls == [("bump", job.id, "storm", PriorityAction.ENQUEUE)]


async def test_a_refused_enqueue_enqueues_nothing_and_records_the_request() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()

    with pytest.raises(PriorityRefused):
        await _service(jobs, store).enqueue(_request(), source="issue-comment")

    assert await jobs.list_for_cycle(PROJECT, cycle=3, kind="review.collect") == ()
    (refusal,) = store.refusals
    assert refusal.job_id is None
    assert refusal.action is PriorityAction.ENQUEUE
    assert (refusal.project_id, refusal.cycle, refusal.phase) == (PROJECT, 3, Phase.REVIEW)


async def test_the_queue_is_read_through_the_store() -> None:
    jobs, store = FakeJobRepository(), FakePriorityStore()
    assert await _service(jobs, store).queue(PROJECT) == ()
    assert store.calls == [("queue", PROJECT, "", PriorityAction.BUMP)]
