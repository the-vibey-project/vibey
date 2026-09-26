# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's use cases: authorise first, delegate to the existing services, render.

Every collaborator is a small fake that records what it was asked, so each test says
two things: what a principal with given scopes may do, and that the hub asked the
service the CLI uses -- never a query of its own.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

import pytest

from vibey.application.dto import (
    GateAnswerOutcome,
    HubPrincipal,
    HumanGateRecord,
    ProjectRecord,
)
from vibey.application.hub.hub_service import HUB_QUEUE_SOURCE, HubService
from vibey.application.hub.interfaces.hub_service_interface import (
    HubDocumentsInterface,
    HubProbesInterface,
    HubServiceInterface,
)
from vibey.domain.errors import UnknownGate, UnknownProject
from vibey.domain.hub_scope import HubForbidden, HubScope
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase

AT = datetime(2026, 9, 25, 12, 0, tzinfo=UTC)
EVERYTHING = HubPrincipal(name="host", scopes=frozenset(HubScope))
NOTHING = HubPrincipal(name="stranger")


def _project(name: str = "greeter") -> ProjectRecord:
    return ProjectRecord(
        project_id=uuid4(),
        name=name,
        repo_path=Path("/repo"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config={},
        created_at=AT,
        updated_at=AT,
    )


def _gate(project: ProjectRecord, kind: str = "approval") -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=uuid4(),
        project_id=project.project_id,
        job_id=None,
        kind=kind,
        prompt="ok?",
        options=(),
        default_answer=None,
        answer=None,
        raised_at=AT,
        timeout_at=None,
        answered_at=None,
        answered_by=None,
    )


@dataclass
class World:
    """Every fake the service reads, and a log of what was asked of each."""

    projects: list[ProjectRecord] = field(default_factory=list)
    gates: list[HumanGateRecord] = field(default_factory=list)
    closed: list[HumanGateRecord] = field(default_factory=list)
    asked: list[tuple[str, Any]] = field(default_factory=list)

    # ProjectReader
    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return next((p for p in self.projects if p.project_id == project_id), None)

    async def get_latest(self) -> ProjectRecord | None:  # pragma: no cover - unused seam
        return self.projects[0] if self.projects else None

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        return tuple(self.projects)

    # HumanGateRepository (the reads the hub makes)
    async def open_all(self) -> tuple[HumanGateRecord, ...]:
        return tuple(self.gates)

    async def open_for_project(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        return tuple(g for g in self.gates if g.project_id == project_id)

    # GateLookup: every gate ever raised, open or answered.
    async def get_gate(self, gate_id: UUID) -> HumanGateRecord | None:
        return next((g for g in self.gates + self.closed if g.gate_id == gate_id), None)


class Lookup:
    def __init__(self, world: World) -> None:
        self._world = world

    async def get(self, gate_id: UUID) -> HumanGateRecord | None:
        return await self._world.get_gate(gate_id)


class Answers:
    def __init__(self, world: World) -> None:
        self._world = world

    async def answer(
        self,
        gate_id: UUID,
        answer: Mapping[str, object],
        *,
        by: str | None = None,
        request_id: str | None = None,
    ) -> GateAnswerOutcome:
        self._world.asked.append(("answer", (gate_id, dict(answer), by, request_id)))
        gate = next(g for g in self._world.gates if g.gate_id == gate_id)
        return GateAnswerOutcome(record=gate)

    def derived_request_id(  # pragma: no cover - unused seam
        self, source: str, gate_id: UUID, answer: Mapping[str, object]
    ) -> str:
        return "derived"


class Budgets:
    def __init__(self, world: World) -> None:
        self._world = world

    async def show(self, project_id: UUID) -> Any:
        self._world.asked.append(("budget", project_id))
        return "budget"

    async def show_all(self) -> Any:  # pragma: no cover - unused seam
        return ()

    async def set_caps(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("the hub never changes a cap")

    async def clear_caps(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError("the hub never changes a cap")


class Queue:
    def __init__(self, world: World) -> None:
        self._world = world

    async def bump(self, project_id: UUID, job_id: UUID, *, source: str | None = None) -> Any:
        self._world.asked.append(("bump", (project_id, job_id, source)))
        return "change"

    async def unbump(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError

    async def enqueue(self, *args: Any, **kwargs: Any) -> Any:  # pragma: no cover
        raise AssertionError

    async def queue(self, project_id: UUID) -> Any:
        self._world.asked.append(("queue", project_id))
        return ()


class Ledger:
    def __init__(self, world: World) -> None:
        self._world = world

    async def search(self, project_id: UUID, query: Any) -> Any:
        self._world.asked.append(("search", query))
        return "result"


class Range:
    def __init__(self, world: World) -> None:
        self._world = world

    async def range(self, project_id: UUID, *, from_seq: int, to_seq: int) -> Any:
        self._world.asked.append(("range", (from_seq, to_seq)))
        return ()


class Documents:
    """Renders each record as a tagged tuple, so a test sees what was rendered."""

    def projects(self, projects: Sequence[ProjectRecord], open_gates: Mapping[UUID, int]) -> Any:
        return ("projects", [p.name for p in projects], dict(open_gates))

    def gates(self, gates: Sequence[HumanGateRecord], names: Mapping[UUID, str]) -> Any:
        return ("gates", [g.gate_id for g in gates], dict(names))

    def answered(self, outcome: GateAnswerOutcome) -> Any:
        return ("answered", outcome.record.gate_id)

    def budget(self, budget: Any) -> Any:
        return ("budget", budget)

    def queue(self, project_id: UUID, entries: Any) -> Any:
        return ("queue", project_id)

    def bumped(self, change: Any) -> Any:
        return ("bumped", change)

    def ledger(self, project_id: UUID, result: Any) -> Any:
        return ("ledger", result)

    def events(self, project_id: UUID, events: Any) -> Any:
        return ("events", project_id)


class Probes:
    async def status(self, project_id: UUID) -> Any:
        return ("status", project_id)

    def loops(self) -> Any:
        return ("loops",)

    def lanes(self) -> Any:
        return ("lanes",)

    async def doctor(self) -> Any:
        return ("doctor",)

    def lane_tail(self, events_path: str, after: int) -> Any:
        return ("tail", events_path, after)


def _service(world: World) -> HubService:
    return HubService(
        projects=world,
        gates=world,  # type: ignore[arg-type]  # the reads the hub makes, nothing more
        gate_lookup=Lookup(world),
        gate_answers=Answers(world),
        budgets=Budgets(world),
        queue=Queue(world),
        ledger=Ledger(world),
        ledger_range=Range(world),
        documents=Documents(),
        probes=Probes(),
    )


def test_the_service_and_its_collaborators_meet_their_declared_seams() -> None:
    world = World()
    assert isinstance(_service(world), HubServiceInterface)
    assert isinstance(Documents(), HubDocumentsInterface)
    assert isinstance(Probes(), HubProbesInterface)


async def test_projects_counts_each_projects_open_gates() -> None:
    world = World()
    one, two = _project("one"), _project("two")
    world.projects = [one, two]
    world.gates = [_gate(one), _gate(one)]
    assert await _service(world).projects(EVERYTHING) == (
        "projects",
        ["one", "two"],
        {one.project_id: 2},
    )


async def test_gates_lists_every_projects_or_one_projects() -> None:
    world = World()
    one, two = _project("one"), _project("two")
    world.projects = [one, two]
    first, second = _gate(one), _gate(two)
    orphan = _gate(_project("gone"))
    world.gates = [first, second, orphan]
    service = _service(world)
    # A gate whose project is gone is not listed.
    assert await service.gates(EVERYTHING, None) == (
        "gates",
        [first.gate_id, second.gate_id],
        {one.project_id: "one", two.project_id: "two"},
    )
    assert await service.gates(EVERYTHING, two.project_id) == (
        "gates",
        [second.gate_id],
        {two.project_id: "two"},
    )


async def test_a_project_that_does_not_exist_is_unknown() -> None:
    service = _service(World())
    missing = uuid4()
    for call in (
        service.status(EVERYTHING, missing),
        service.gates(EVERYTHING, missing),
        service.budget(EVERYTHING, missing),
        service.queue(EVERYTHING, missing),
        service.bump(EVERYTHING, missing, uuid4()),
        service.ledger(EVERYTHING, missing, text=None, kinds=[], actor=None, limit=5),
    ):
        with pytest.raises(UnknownProject):
            await call


async def test_the_reads_delegate_and_render() -> None:
    world = World()
    project = _project()
    world.projects = [project]
    service = _service(world)
    pid = project.project_id
    assert await service.status(EVERYTHING, pid) == ("status", pid)
    assert await service.budget(EVERYTHING, pid) == ("budget", "budget")
    assert await service.queue(EVERYTHING, pid) == ("queue", pid)
    assert service.loops(EVERYTHING) == ("loops",)
    assert service.lanes(EVERYTHING) == ("lanes",)
    assert await service.doctor(EVERYTHING) == ("doctor",)
    assert ("budget", pid) in world.asked and ("queue", pid) in world.asked


async def test_a_ledger_search_builds_the_domains_query() -> None:
    world = World()
    project = _project()
    world.projects = [project]
    document = await _service(world).ledger(
        EVERYTHING,
        project.project_id,
        text="needle",
        kinds=["GateAnswered"],
        actor="vibey",
        limit=7,
    )
    assert document == ("ledger", "result")
    [(_, query)] = [entry for entry in world.asked if entry[0] == "search"]
    assert query.text == "needle" and query.limit == 7
    assert query.kinds == frozenset({EventKind.GATE_ANSWERED})
    assert query.actor is not None


async def test_a_bump_is_requested_as_the_declared_hub_source() -> None:
    world = World()
    project = _project()
    world.projects = [project]
    job = uuid4()
    assert await _service(world).bump(EVERYTHING, project.project_id, job) == ("bumped", "change")
    assert ("bump", (project.project_id, job, HUB_QUEUE_SOURCE)) in world.asked


async def test_an_answer_is_recorded_under_the_principals_name() -> None:
    world = World()
    project = _project()
    gate = _gate(project)
    world.projects, world.gates = [project], [gate]
    phone = HubPrincipal(name="device:phone", scopes=frozenset({HubScope.ANSWER}))
    document = await _service(world).answer_gate(
        phone, gate.gate_id, {"verdict": "accept"}, request_id="r-1"
    )
    assert document == ("answered", gate.gate_id)
    assert ("answer", (gate.gate_id, {"verdict": "accept"}, "device:phone", "r-1")) in world.asked


async def test_a_spending_gate_needs_spend_as_well_as_answer() -> None:
    world = World()
    project = _project()
    gate = _gate(project, kind="budget_exhausted")
    world.projects, world.gates = [project], [gate]
    service = _service(world)
    answerer = HubPrincipal(name="device:phone", scopes=frozenset({HubScope.ANSWER}))
    with pytest.raises(HubForbidden):
        await service.answer_gate(answerer, gate.gate_id, {"choice": "resume"}, request_id=None)
    assert not [entry for entry in world.asked if entry[0] == "answer"]
    spender = HubPrincipal(name="device:phone", scopes=frozenset({HubScope.ANSWER, HubScope.SPEND}))
    assert await service.answer_gate(
        spender, gate.gate_id, {"choice": "resume"}, request_id=None
    ) == ("answered", gate.gate_id)


async def test_a_gate_that_does_not_exist_is_unknown() -> None:
    with pytest.raises(UnknownGate):
        await _service(World()).answer_gate(
            EVERYTHING, uuid4(), {"verdict": "accept"}, request_id="r-1"
        )


async def test_a_replay_of_a_spending_gate_still_needs_spend() -> None:
    """The kind is read by id whatever the gate's state: an answered spending gate with a
    request id is authorised exactly as an open one (review of #1155)."""
    world = World()
    project = _project()
    answered = _gate(project, kind="budget_exhausted")
    world.projects, world.closed = [project], [answered]
    answerer = HubPrincipal(name="device:phone", scopes=frozenset({HubScope.ANSWER}))
    with pytest.raises(HubForbidden):
        await _service(world).answer_gate(
            answerer, answered.gate_id, {"choice": "resume"}, request_id="r-1"
        )
    assert world.asked == []


async def test_nothing_is_permitted_by_default() -> None:
    world = World()
    project = _project()
    gate = _gate(project)
    world.projects, world.gates = [project], [gate]
    service = _service(world)
    pid = project.project_id
    for call in (
        service.projects(NOTHING),
        service.status(NOTHING, pid),
        service.gates(NOTHING, None),
        service.answer_gate(NOTHING, gate.gate_id, {"verdict": "accept"}, request_id=None),
        service.budget(NOTHING, pid),
        service.queue(NOTHING, pid),
        service.bump(NOTHING, pid, uuid4()),
        service.ledger(NOTHING, pid, text=None, kinds=[], actor=None, limit=5),
        service.doctor(NOTHING),
    ):
        with pytest.raises(HubForbidden):
            await call
    for sync in (service.loops, service.lanes):
        with pytest.raises(HubForbidden):
            sync(NOTHING)
    assert world.asked == []


async def test_view_cannot_answer_or_bump() -> None:
    world = World()
    project = _project()
    gate = _gate(project)
    world.projects, world.gates = [project], [gate]
    service = _service(world)
    viewer = HubPrincipal(name="device:tv", scopes=frozenset({HubScope.VIEW}))
    with pytest.raises(HubForbidden):
        await service.answer_gate(viewer, gate.gate_id, {"verdict": "accept"}, request_id=None)
    with pytest.raises(HubForbidden):
        await service.bump(viewer, project.project_id, uuid4())
    assert world.asked == []


async def test_the_live_feed_reads_by_position_after_the_last_seq() -> None:
    world = World()
    project = _project()
    world.projects = [project]
    service = _service(world)
    assert await service.ledger_after(EVERYTHING, project.project_id, after=41, limit=10) == (
        "events",
        project.project_id,
    )
    assert ("range", (42, 51)) in world.asked
    assert service.lane_tail(EVERYTHING, "/x/events.jsonl", 7) == ("tail", "/x/events.jsonl", 7)
    with pytest.raises(HubForbidden):
        await service.ledger_after(NOTHING, project.project_id, after=0, limit=1)
    with pytest.raises(HubForbidden):
        service.lane_tail(NOTHING, "/x", 0)
    with pytest.raises(UnknownProject):
        await service.ledger_after(EVERYTHING, uuid4(), after=0, limit=1)
