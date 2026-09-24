# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`ProjectBudgetService`: a budget read the way the brake reads it, and a change checked
before anything is written, with who made it recorded twice."""

import dataclasses
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository
from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.dto import CapChangeOutcome, HumanGateRequest, ProjectRecord
from vibey.application.interfaces import (
    OpenGateReader,
    ProjectBudgetServiceInterface,
    ProjectBudgetStore,
    ProjectReader,
)
from vibey.application.project_budget import (
    BUDGET_GATE_KIND,
    LedgerSnapshot,
    ProjectBudgetService,
)
from vibey.domain.budget_caps import CAP_CHANGE_PLANNER, CapChange, CapField, CycleCaps
from vibey.domain.errors import InvalidBudgetChange, UnknownProject
from vibey.domain.interfaces.budget_caps_interface import CapRequestInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import Caller

NOW = datetime(2026, 9, 24, 19, 2, tzinfo=UTC)
DOLLARS = CapField.MAX_CYCLE_DOLLARS
TURNS = CapField.MAX_CYCLE_TURNS


def _project(name: str, config: Mapping[str, object], *, cycle: int = 1) -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name=name,
        repo_path=Path(f"/tmp/{name}"),
        phase=Phase.BUILD,
        cycle=cycle,
        max_cycles=5,
        config=dict(config),
        created_at=NOW,
        updated_at=NOW,
    )


class _Projects:
    """A `ProjectReader` over a list, newest first."""

    def __init__(self, *projects: ProjectRecord) -> None:
        self.projects = list(projects)

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return next((p for p in self.projects if p.project_id == project_id), None)

    async def get_latest(self) -> ProjectRecord | None:
        return self.projects[0] if self.projects else None

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        return tuple(self.projects)


class _Ledger:
    def __init__(self, events: Mapping[UUID, list[LedgerEvent]] | None = None) -> None:
        self.events = dict(events or {})
        self.reads: list[UUID] = []

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        self.reads.append(project_id)
        return tuple(self.events.get(project_id, ()))


class _Store:
    """Plans against the project's config as the Postgres store does, and writes it back
    into the `_Projects` it shares, so the service reads what it wrote."""

    def __init__(self, projects: _Projects) -> None:
        self.projects = projects
        self.calls: list[tuple[UUID, CapRequestInterface, str, str, datetime]] = []

    async def apply(
        self,
        project_id: UUID,
        request: CapRequestInterface,
        *,
        by: str,
        account: str,
        at: datetime,
    ) -> CapChangeOutcome:
        self.calls.append((project_id, request, by, account, at))
        project = await self.projects.get(project_id)
        if project is None:
            raise UnknownProject(f"unknown project {project_id}")
        caps = CycleCaps(*LedgerBudgetSource.caps_from_config(project.config))
        changes = CAP_CHANGE_PLANNER.plan(caps, request)
        config = dict(project.config)
        for change in changes:
            if change.new is None:
                config.pop(change.field.value, None)
            else:
                config[change.field.value] = change.new
        settled = dataclasses.replace(project, config=config)
        self.projects.projects = [
            settled if p.project_id == project_id else p for p in self.projects.projects
        ]
        return CapChangeOutcome(project=settled, changes=changes)


class _Caller:
    def current(self) -> Caller:
        return Caller(uid=501, name="adam")


class _Clock:
    def now(self) -> datetime:
        return NOW


def _event(
    project_id: UUID,
    seq: int,
    kind: EventKind,
    payload: dict[str, object],
    *,
    cycle: int = 1,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=cycle,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,
        provenance=Provenance.TRUSTED,
        produced_at=NOW + timedelta(minutes=seq),
        payload=payload,
        digest=digest_event(payload),
    )


def _service(
    projects: _Projects,
    ledger: _Ledger | None = None,
    gates: FakeHumanGateRepository | None = None,
) -> tuple[ProjectBudgetService, _Store]:
    store = _Store(projects)
    service = ProjectBudgetService(
        projects=projects,
        ledger=ledger or _Ledger(),
        store=store,
        gates=gates or FakeHumanGateRepository(),  # type: ignore[arg-type]
        caller=_Caller(),
        clock=_Clock(),
    )
    return service, store


def test_the_service_and_its_collaborators_satisfy_their_seams() -> None:
    projects = _Projects()
    service, store = _service(projects)

    assert isinstance(service, ProjectBudgetServiceInterface)
    assert isinstance(projects, ProjectReader)
    assert isinstance(store, ProjectBudgetStore)
    assert isinstance(FakeHumanGateRepository(), OpenGateReader)
    assert BUDGET_GATE_KIND == "budget_exhausted"


async def test_a_ledger_snapshot_hands_every_reader_the_one_read() -> None:
    events = (_event(uuid4(), 1, EventKind.BUDGET_SPENT, {"dollars": 1.0}),)

    assert await LedgerSnapshot(events).all_for_project(uuid4()) is events


async def test_showing_an_unknown_project_is_refused() -> None:
    service, _ = _service(_Projects())

    with pytest.raises(UnknownProject, match="unknown project"):
        await service.show(uuid4())


async def test_a_budget_is_the_brakes_own_reading_from_one_ledger_read() -> None:
    project = _project("greeter", {"max_cycle_dollars": 15, "max_cycle_turns": 40}, cycle=2)
    pid = project.project_id
    ledger = _Ledger(
        {
            pid: [
                _event(pid, 1, EventKind.TURN_COMPLETED, {"cost_usd": 99.0}, cycle=1),
                _event(pid, 2, EventKind.TURN_COMPLETED, {"cost_usd": 2.5}, cycle=2),
                _event(pid, 3, EventKind.BUDGET_SPENT, {"dollars": 0.71, "turns": 2}, cycle=2),
                _event(
                    pid,
                    4,
                    EventKind.BUDGET_CAP_CHANGED,
                    {"field": "max_cycle_dollars", "old": None, "new": 15.0, "by": "adam"},
                    cycle=2,
                ),
            ]
        }
    )
    service, _ = _service(_Projects(project), ledger)

    budget = await service.show(pid)

    assert (budget.project_id, budget.name, budget.cycle) == (pid, "greeter", 2)
    assert (budget.budget.max_dollars, budget.budget.max_turns) == (15.0, 40)
    assert budget.budget.dollars_spent == pytest.approx(3.21)
    assert budget.budget.turns_spent == 3
    assert budget.exhausted is False
    assert [(h.field, h.old, h.new, h.by) for h in budget.history] == [
        ("max_cycle_dollars", None, 15.0, "adam")
    ]
    assert ledger.reads == [pid]


async def test_every_projects_budget_comes_back_in_the_readers_order() -> None:
    newest, oldest = _project("newest", {}), _project("oldest", {"max_cycle_turns": 1})
    service, _ = _service(_Projects(newest, oldest))

    budgets = await service.show_all()

    assert [b.name for b in budgets] == ["newest", "oldest"]
    assert await _service(_Projects())[0].show_all() == ()


async def test_a_change_is_recorded_under_the_account_unless_the_caller_names_itself() -> None:
    project = _project("greeter", {"max_cycle_turns": 40})
    projects = _Projects(project)
    service, store = _service(projects)

    change = await service.set_caps(project.project_id, max_dollars=15)
    labelled = await service.set_caps(project.project_id, max_turns=200, by=" vibey-vscode ")

    (pid, request, by, account, at), (_, _, labelled_by, labelled_account, _) = store.calls
    assert (pid, dict(request.set_to), by, account, at) == (
        project.project_id,
        {DOLLARS: 15.0},
        "adam",
        "adam",
        NOW,
    )
    assert (labelled_by, labelled_account) == ("vibey-vscode", "adam")
    assert change.by == "adam" and labelled.by == "vibey-vscode"
    assert change.changes == (CapChange(DOLLARS, None, 15.0),)
    assert labelled.changes == (CapChange(TURNS, 40, 200),)
    assert (labelled.after.budget.max_dollars, labelled.after.budget.max_turns) == (15.0, 200)


async def test_clearing_removes_the_caps_it_names() -> None:
    project = _project("greeter", {"max_cycle_dollars": 15.0, "max_cycle_turns": 40})
    service, store = _service(_Projects(project))

    change = await service.clear_caps(project.project_id, [DOLLARS], by="vibey-vscode")

    assert store.calls[0][1].clear == frozenset({DOLLARS})
    assert change.changes == (CapChange(DOLLARS, 15.0, None),)
    assert (change.after.budget.max_dollars, change.after.budget.max_turns) == (None, 40)


@pytest.mark.parametrize(
    ("call", "reason"),
    [
        (lambda s, pid: s.set_caps(pid, max_dollars=0), "a dollar cap"),
        (lambda s, pid: s.set_caps(pid, max_turns=-1), "a turn cap"),
        (lambda s, pid: s.set_caps(pid), "nothing to set"),
        (lambda s, pid: s.set_caps(pid, max_dollars=1, by="\n"), "cannot be empty"),
        (lambda s, pid: s.clear_caps(pid, []), "nothing to clear"),
        (lambda s, pid: s.clear_caps(pid, [DOLLARS], by="a‮b"), "control or formatting"),
    ],
    ids=["zero-dollars", "negative-turns", "nothing-set", "blank-label", "nothing-cleared", "bidi"],
)
async def test_a_change_vibey_would_refuse_writes_nothing(call, reason) -> None:  # type: ignore[no-untyped-def]
    project = _project("greeter", {})
    service, store = _service(_Projects(project))

    with pytest.raises(InvalidBudgetChange, match=reason):
        await call(service, project.project_id)

    assert store.calls == []


async def test_a_change_names_the_budget_gates_still_parked_on_the_project() -> None:
    project, other = _project("greeter", {}), _project("other", {})
    gates = FakeHumanGateRepository()
    parked = await gates.raise_gate(
        project.project_id, uuid4(), HumanGateRequest(kind=BUDGET_GATE_KIND, prompt="grant?")
    )
    await gates.raise_gate(
        project.project_id, uuid4(), HumanGateRequest(kind="approval", prompt="ok?")
    )
    await gates.raise_gate(
        other.project_id, uuid4(), HumanGateRequest(kind=BUDGET_GATE_KIND, prompt="?")
    )
    answered = await gates.raise_gate(
        project.project_id, uuid4(), HumanGateRequest(kind=BUDGET_GATE_KIND, prompt="grant?")
    )
    await gates.answer(answered.gate_id, answer={}, answered_by="adam")
    service, _ = _service(_Projects(project, other), gates=gates)

    change = await service.set_caps(project.project_id, max_dollars=30)

    assert change.parked == (parked,)
