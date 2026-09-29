# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository
from vibey.application.design import DesignEvent
from vibey.application.design_acceptance import DesignAcceptanceService
from vibey.application.dto import EnqueueRequest, ProjectRecord
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase, VisualDecision
from vibey.domain.spec import AcceptanceCriterion, DesignSpec


def spec() -> DesignSpec:
    return DesignSpec(
        "Ship",
        (),
        (),
        (AcceptanceCriterion("AC-1", "input", "run", "output", "test passes"),),
        (),
        "one path",
    )


class Projects:
    def __init__(self, project: ProjectRecord | None) -> None:
        self.project = project

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return self.project

    async def transition(self, project_id: UUID, *, expected: Phase, to: Phase) -> ProjectRecord:
        assert self.project is not None
        assert self.project.phase is expected
        self.project = replace(self.project, phase=to)
        return self.project


class Ledger:
    def __init__(self, events: tuple[DesignEvent, ...] = ()) -> None:
        self.events = events
        self.appended: list[DesignEvent] = []

    async def all_for_project(self, project_id: UUID) -> tuple[DesignEvent, ...]:
        return self.events

    async def append(self, project_id, cycle, job_id, engine_id, event):  # type: ignore[no-untyped-def]
        self.appended.append(event)


class Specs:
    def __init__(self, value: DesignSpec | None) -> None:
        self.value = value
        self.published = False

    async def save(self, project_id: UUID, cycle: int, value: DesignSpec) -> None:
        self.value = value

    async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None:
        return self.value

    async def publish(self, project_id: UUID, cycle: int, value: DesignSpec) -> None:
        self.published = True


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 14, tzinfo=UTC)


def project() -> ProjectRecord:
    now = datetime.now(UTC)
    return ProjectRecord(uuid4(), "demo", Path("."), Phase.DESIGN, 1, 10, {}, now, now)


def _service(
    *, projects: Projects, ledger: Ledger, specs: Specs, jobs: FakeJobRepository | None = None
) -> DesignAcceptanceService:
    return DesignAcceptanceService(
        projects=projects,
        ledger=ledger,
        specs=specs,
        jobs=jobs or FakeJobRepository(),
        clock=FixedClock(),
    )


async def test_accept_publishes_and_transitions_to_build_by_default() -> None:
    projects = Projects(project())
    specs = Specs(spec())
    ledger = Ledger()
    accepted = await _service(projects=projects, ledger=ledger, specs=specs).accept(
        projects.project.project_id  # type: ignore[union-attr]
    )
    assert accepted.phase is Phase.BUILD
    assert specs.published
    assert [e.kind for e in ledger.appended] == [EventKind.VISUAL_DESIGN_DECLINED]
    assert ledger.appended[0].provenance is Provenance.TRUSTED


async def test_accept_opting_in_enters_visual_design_and_enqueues_inventory() -> None:
    projects = Projects(project())
    specs = Specs(spec())
    ledger = Ledger()
    jobs = FakeJobRepository()
    accepted = await _service(projects=projects, ledger=ledger, specs=specs, jobs=jobs).accept(
        projects.project.project_id,  # type: ignore[union-attr]
        visual_choice=VisualDecision.OPTED_IN,
    )
    assert accepted.phase is Phase.VISUAL_DESIGN
    assert [e.kind for e in ledger.appended] == [EventKind.VISUAL_DESIGN_OPTED_IN]
    enqueued = await jobs.claim(accepted.project_id, owner="test", lease=timedelta(seconds=5))
    assert enqueued is not None
    assert enqueued.kind == "visual.inventory"
    assert enqueued.phase is Phase.VISUAL_DESIGN


async def test_accept_rejects_missing_project_or_spec() -> None:
    with pytest.raises(ValueError, match="unknown project"):
        await _service(projects=Projects(None), ledger=Ledger(), specs=Specs(spec())).accept(
            uuid4()
        )
    value = project()
    with pytest.raises(ValueError, match="no synthesized"):
        await _service(projects=Projects(value), ledger=Ledger(), specs=Specs(None)).accept(
            value.project_id
        )


async def test_accept_rejects_open_blocking_question() -> None:
    value = project()
    event = DesignEvent(
        EventKind.QUESTION_ASKED,
        Provenance.AGENT,
        datetime.now(UTC),
        {"item_id": "q-1", "blocking": True},
    )
    with pytest.raises(ValueError, match="blocking question"):
        await _service(
            projects=Projects(value), ledger=Ledger((event,)), specs=Specs(spec())
        ).accept(value.project_id)


async def _design_job(jobs: FakeJobRepository, value: ProjectRecord, kind: str) -> UUID:
    record = await jobs.enqueue(
        EnqueueRequest(
            project_id=value.project_id,
            cycle=value.cycle,
            phase=Phase.DESIGN,
            kind=kind,
            idempotency_key=f"{value.project_id}:{kind}",
        )
    )
    return record.id


async def test_accept_refuses_while_the_design_chain_is_still_queued() -> None:
    """Live 2026-09-29: accepted straight after the interview, a stale spec.json on disk
    took the project to BUILD with research, synthesis and spec still ready."""
    value = project()
    projects = Projects(value)
    ledger = Ledger()
    specs = Specs(spec())
    jobs = FakeJobRepository()
    for kind in ("design.research", "design.synthesize", "design.spec"):
        await _design_job(jobs, value, kind)
    with pytest.raises(ValueError, match="3 design job\\(s\\) still unsettled"):
        await _service(projects=projects, ledger=ledger, specs=specs, jobs=jobs).accept(
            value.project_id
        )
    assert projects.project is not None
    assert projects.project.phase is Phase.DESIGN
    assert ledger.appended == []
    assert not specs.published
    assert await jobs.list_for_cycle(value.project_id, cycle=1, kind="build.decompose") == ()


async def test_accept_proceeds_once_every_design_job_has_settled() -> None:
    value = project()
    projects = Projects(value)
    jobs = FakeJobRepository()
    for kind in ("design.interview", "design.synthesize", "design.spec"):
        await _design_job(jobs, value, kind)
    while (
        claimed := await jobs.claim(value.project_id, owner="w", lease=timedelta(1))
    ) is not None:
        assert await jobs.ack(claimed.id, owner="w")
    service = _service(projects=projects, ledger=Ledger(), specs=Specs(spec()), jobs=jobs)
    accepted = await service.accept(value.project_id)
    assert accepted.phase is Phase.BUILD
    (decompose,) = await jobs.list_for_cycle(value.project_id, cycle=1, kind="build.decompose")
    assert decompose.state is JobState.READY
