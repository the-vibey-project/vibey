# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queue-priority service: authorise before looking, record every request, and
let the store move (ADR-0054, 12.j)."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EnqueueRequest, ProjectRecord, QueueEntry
from vibey.application.interfaces import (
    CallerIdentity,
    JobPriorityStore,
    PriorityGrantReader,
    QueuePriorityServiceInterface,
)
from vibey.application.queue_priority import QueuePriorityService
from vibey.domain.config import ConfigError
from vibey.domain.errors import (
    DependencyCannotFinish,
    PriorityRefused,
    ReorderRefused,
    UnknownJob,
    UnknownProject,
    WrongPhase,
)
from vibey.domain.phase import Phase, StoredPhase, UnrecognizedPhase
from vibey.domain.queue_priority import (
    Caller,
    MovedJob,
    PriorityAction,
    PriorityChange,
    PriorityContext,
    PriorityGrant,
    PriorityRefusal,
)

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)
PROJECT = UUID(int=77)
OWNER = Caller(uid=501, name="adam")
STRANGER = Caller(uid=502, name="mallory")


class FixedClock:
    def now(self) -> datetime:
        return NOW


class FakeProjects:
    def __init__(self, phase: StoredPhase = Phase.BUILD) -> None:
        self.record = ProjectRecord(
            project_id=PROJECT,
            name="demo",
            repo_path=Path("/repo"),
            phase=phase,
            cycle=3,
            max_cycles=5,
            config={},
            created_at=NOW,
            updated_at=NOW,
        )

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self.record if project_id == PROJECT else None

    async def transition(
        self, project_id: UUID, *, expected: Phase, to: Phase, guard: str | None = None
    ) -> ProjectRecord:
        raise NotImplementedError


class FakeGrants:
    def __init__(self, *declared: str, broken: bool = False) -> None:
        self._grant = PriorityGrant(declared, owner_uid=OWNER.uid, anchor="/repo/vibey.toml")
        self._broken = broken
        self.read_for: list[UUID] = []

    def read(self, project: ProjectRecord) -> PriorityGrant:
        self.read_for.append(project.project_id)
        if self._broken:
            raise ConfigError("/repo/vibey.toml", "is not valid TOML")
        return self._grant


class FakeCaller:
    def __init__(self, caller: Caller = OWNER) -> None:
        self._caller = caller

    def current(self) -> Caller:
        return self._caller


class FakePriorityStore:
    """Records what it was asked. The real store is exercised against Postgres."""

    def __init__(self, refuse_with: ReorderRefused | None = None) -> None:
        self.calls: list[tuple[str, UUID, PriorityContext, PriorityAction]] = []
        self.refusals: list[PriorityRefusal] = []
        self.at: list[datetime] = []
        self._refuse_with = refuse_with

    async def bump(
        self,
        job_id: UUID,
        *,
        context: PriorityContext,
        at: datetime,
        action: PriorityAction = PriorityAction.BUMP,
    ) -> PriorityChange:
        self.calls.append(("bump", job_id, context, action))
        self.at.append(at)
        if self._refuse_with is not None:
            raise self._refuse_with
        return PriorityChange(
            action=action,
            requested_by=context.requested_by,
            target=job_id,
            moved=(MovedJob(job_id=job_id, bump_seq=1, previous=None),),
        )

    async def unbump(
        self, job_id: UUID, *, context: PriorityContext, at: datetime
    ) -> PriorityChange:
        self.calls.append(("unbump", job_id, context, PriorityAction.UNBUMP))
        self.at.append(at)
        if self._refuse_with is not None:
            raise self._refuse_with
        return PriorityChange(
            action=PriorityAction.UNBUMP, requested_by=context.requested_by, target=job_id, moved=()
        )

    async def refuse(self, refusal: PriorityRefusal, *, at: datetime) -> None:
        self.refusals.append(refusal)
        self.at.append(at)

    async def queue(self, project_id: UUID) -> tuple[QueueEntry, ...]:
        return ()


def _request() -> EnqueueRequest:
    return EnqueueRequest(
        project_id=PROJECT,
        cycle=3,
        phase=Phase.REVIEW,
        kind="review.collect",
        idempotency_key="key-x",
    )


def _service(
    store: FakePriorityStore,
    *,
    grants: FakeGrants | None = None,
    caller: Caller = OWNER,
    projects: FakeProjects | None = None,
    jobs: FakeJobRepository | None = None,
) -> QueuePriorityService:
    return QueuePriorityService(
        projects=projects or FakeProjects(),
        jobs=jobs or FakeJobRepository(),
        store=store,
        grants=grants or FakeGrants(),
        caller=FakeCaller(caller),
        clock=FixedClock(),
    )


def test_the_fakes_and_the_service_satisfy_their_seams() -> None:
    store = FakePriorityStore()
    assert isinstance(store, JobPriorityStore)
    assert isinstance(FakeGrants(), PriorityGrantReader)
    assert isinstance(FakeCaller(), CallerIdentity)
    assert isinstance(_service(store), QueuePriorityServiceInterface)


async def test_the_owner_naming_no_source_bumps_as_the_operator() -> None:
    store = FakePriorityStore()
    job = uuid4()

    change = await _service(store).bump(PROJECT, job)

    assert change.requested_by == "operator:adam"
    ((verb, target, context, action),) = store.calls
    assert (verb, target, action) == ("bump", job, PriorityAction.BUMP)
    assert context == PriorityContext(PROJECT, 3, Phase.BUILD, "operator:adam")
    assert store.at == [NOW]
    assert store.refusals == []


async def test_a_declared_source_run_by_the_owner_bumps_and_unbumps() -> None:
    store = FakePriorityStore()
    job = uuid4()
    service = _service(store, grants=FakeGrants("storm"))

    await service.bump(PROJECT, job, source="storm")
    await service.unbump(PROJECT, job, source="storm")

    assert [(c[0], c[2].requested_by) for c in store.calls] == [
        ("bump", "source:storm"),
        ("unbump", "source:storm"),
    ]


@pytest.mark.parametrize("action", ["bump", "unbump"])
@pytest.mark.parametrize(
    ("source", "caller", "requested_by"),
    [
        (None, STRANGER, "account:mallory"),
        ("storm", STRANGER, "source:storm"),
        ("github-label", OWNER, "source:github-label"),
    ],
)
async def test_a_request_with_no_grant_is_refused_and_recorded_before_the_job_is_looked_at(
    action: str, source: str | None, caller: Caller, requested_by: str
) -> None:
    store = FakePriorityStore()
    nowhere = uuid4()  # no such job: the refusal must not depend on it existing
    service = _service(store, grants=FakeGrants("storm"), caller=caller)

    with pytest.raises(PriorityRefused) as caught:
        await getattr(service, action)(PROJECT, nowhere, source=source)

    assert caught.value.requested_by == requested_by
    assert store.calls == [], "a refused request never reaches the store's change path"
    (refusal,) = store.refusals
    assert refusal == PriorityRefusal(
        context=PriorityContext(PROJECT, 3, Phase.BUILD, requested_by),
        job_id=nowhere,
        action=PriorityAction(action),
        reason=str(caught.value),
    )


async def test_an_unreadable_grant_refuses_every_request_and_records_it() -> None:
    store = FakePriorityStore()
    service = _service(store, grants=FakeGrants(broken=True))

    with pytest.raises(PriorityRefused, match="the grant cannot be read"):
        await service.bump(PROJECT, uuid4())
    with pytest.raises(PriorityRefused, match="the grant cannot be read"):
        await service.bump(PROJECT, uuid4(), source="storm")

    assert [r.context.requested_by for r in store.refusals] == ["account:adam", "source:storm"]
    assert store.calls == []


@pytest.mark.parametrize("action", ["bump", "unbump"])
async def test_what_the_store_refuses_is_recorded_before_it_is_raised(action: str) -> None:
    job = uuid4()
    store = FakePriorityStore(refuse_with=UnknownJob(job))

    with pytest.raises(UnknownJob):
        await getattr(_service(store), action)(PROJECT, job)

    (refusal,) = store.refusals
    assert refusal.job_id == job
    assert refusal.reason == f"unknown job {job}"
    assert refusal.context.requested_by == "operator:adam"


async def test_an_unknown_project_is_reported_with_nothing_to_record_against() -> None:
    store = FakePriorityStore()
    with pytest.raises(UnknownProject):
        await _service(store).bump(uuid4(), uuid4())
    assert store.calls == [] and store.refusals == []


async def test_a_project_in_an_unknown_phase_is_not_written_under() -> None:
    store = FakePriorityStore()
    projects = FakeProjects(phase=UnrecognizedPhase("triage"))
    with pytest.raises(WrongPhase, match="triage"):
        await _service(store, projects=projects).bump(PROJECT, uuid4())
    assert store.calls == [] and store.refusals == []


async def test_enqueue_with_priority_enqueues_then_bumps_what_it_made() -> None:
    store = FakePriorityStore()
    jobs = FakeJobRepository()

    job, change = await _service(store, jobs=jobs).enqueue(_request())

    assert await jobs.get(job.id) == job
    assert change.action is PriorityAction.ENQUEUE
    assert [(c[0], c[1], c[3]) for c in store.calls] == [("bump", job.id, PriorityAction.ENQUEUE)]


async def test_a_refused_enqueue_enqueues_nothing_and_records_the_request() -> None:
    store = FakePriorityStore()
    jobs = FakeJobRepository()

    with pytest.raises(PriorityRefused):
        await _service(store, jobs=jobs, caller=STRANGER).enqueue(_request())

    assert await jobs.list_for_cycle(PROJECT, cycle=3, kind="review.collect") == ()
    (refusal,) = store.refusals
    assert refusal.job_id is None
    assert refusal.action is PriorityAction.ENQUEUE


async def test_an_enqueue_the_store_refuses_is_recorded_against_the_job_it_made() -> None:
    blocked = DependencyCannotFinish(uuid4(), ((uuid4(), "failed"),))
    store = FakePriorityStore(refuse_with=blocked)

    with pytest.raises(DependencyCannotFinish):
        await _service(store).enqueue(_request())

    (refusal,) = store.refusals
    assert refusal.job_id == store.calls[0][1]
    assert refusal.action is PriorityAction.ENQUEUE


async def test_the_queue_is_read_through_the_store() -> None:
    assert await _service(FakePriorityStore()).queue(PROJECT) == ()
