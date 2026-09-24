# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The presenters and commands behind `vibey projects` and `vibey gates`, with no database:
what each reading says, exactly, and what each command does with what it reads."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
import typer

from vibey.application.dto import HumanGateRecord, ProjectRecord
from vibey.cli.gate_answers import GATE_ANSWERS
from vibey.cli.gates import GATES, GATES_PRESENTER, GatesCommand, GatesPresenter
from vibey.cli.interfaces.gates_interface import GatesCommandInterface, GatesPresenterInterface
from vibey.cli.interfaces.projects_interface import (
    ProjectsCommandInterface,
    ProjectsPresenterInterface,
)
from vibey.cli.projects import PROJECTS, PROJECTS_PRESENTER, ProjectsCommand, ProjectsPresenter
from vibey.domain.phase import Phase, StoredPhase, UnrecognizedPhase

AT = datetime(2026, 9, 24, 9, 30, tzinfo=UTC)
FIRST = UUID("11111111-1111-4111-8111-111111111111")
SECOND = UUID("22222222-2222-4222-8222-222222222222")


def _project(
    name: str,
    project_id: UUID,
    *,
    phase: StoredPhase = Phase.BUILD,
    cycle: int = 1,
    max_cycles: int = 3,
    created: datetime = AT,
) -> ProjectRecord:
    return ProjectRecord(
        project_id=project_id,
        name=name,
        repo_path=Path(f"/src/{name}"),
        phase=phase,
        cycle=cycle,
        max_cycles=max_cycles,
        config={},
        created_at=created,
        updated_at=created,
    )


def _gate(
    project_id: UUID,
    *,
    kind: str = "approval",
    prompt: str = "Accept?",
    options: tuple[str, ...] = ("accept", "changes", "cancel"),
    default_answer: str | None = None,
    job_id: UUID | None = None,
    raised: datetime = AT,
    timeout_at: datetime | None = None,
) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=uuid4(),
        project_id=project_id,
        job_id=job_id,
        kind=kind,
        prompt=prompt,
        options=options,
        default_answer=default_answer,
        answer=None,
        raised_at=raised,
        timeout_at=timeout_at,
        answered_at=None,
        answered_by=None,
    )


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(PROJECTS, ProjectsCommandInterface)
    assert isinstance(PROJECTS_PRESENTER, ProjectsPresenterInterface)
    assert isinstance(GATES, GatesCommandInterface)
    assert isinstance(GATES_PRESENTER, GatesPresenterInterface)


# -- vibey projects -----------------------------------------------------------------------------


def test_no_projects_says_how_to_make_one() -> None:
    presenter = ProjectsPresenter()
    assert presenter.projects([], {}) == [
        "no projects yet; create one with `vibey new <name> --repo <path>`"
    ]
    assert json.loads(presenter.projects_json([], {})) == []


def test_the_table_is_plain_aligned_newest_first_and_points_at_the_waiting_gates() -> None:
    greeter = _project("greeter", FIRST)
    docs = _project(
        "docs", SECOND, phase=Phase.DONE, cycle=3, created=AT - timedelta(days=1, hours=1)
    )

    lines = ProjectsPresenter().projects([greeter, docs], {FIRST: 2})

    assert lines == [
        "NAME     PHASE  CYCLE  OPEN GATES  CREATED (UTC)     PROJECT ID",
        f"greeter  BUILD  1/3    2           2026-09-24 09:30  {FIRST}",
        f"docs     DONE   3/3    0           2026-09-23 08:30  {SECOND}",
        "",
        "2 projects, newest first. 2 open gates are waiting for your answer: `vibey gates` "
        "lists them.",
    ]


def test_one_project_and_one_gate_read_in_the_singular() -> None:
    lines = ProjectsPresenter().projects([_project("greeter", FIRST)], {FIRST: 1})
    assert lines[-1] == (
        "1 project, newest first. 1 open gate is waiting for your answer: `vibey gates` lists them."
    )


def test_with_nothing_waiting_the_summary_names_no_gates() -> None:
    lines = ProjectsPresenter().projects([_project("greeter", FIRST)], {SECOND: 4})
    assert lines[-1] == "1 project, newest first."


def test_creation_times_are_shown_in_utc() -> None:
    east = datetime(2026, 9, 24, 11, 30, tzinfo=timezone(timedelta(hours=2)))
    (_, row, *_) = ProjectsPresenter().projects([_project("greeter", FIRST, created=east)], {})
    assert "2026-09-24 09:30" in row


def test_a_phase_a_newer_vibey_wrote_is_shown_as_its_stored_text() -> None:
    future = _project("greeter", FIRST, phase=UnrecognizedPhase("quantum_review"))
    presenter = ProjectsPresenter()

    (_, row, *_) = presenter.projects([future], {})
    (record,) = json.loads(presenter.projects_json([future], {}))

    assert row.split()[1] == "quantum_review"
    assert record["phase"] == "quantum_review"


def test_projects_json_carries_exactly_the_contract_keys() -> None:
    greeter = _project("greeter", FIRST, phase=Phase.VISUAL_DESIGN, cycle=2, max_cycles=5)
    docs = _project("docs", SECOND, phase=Phase.INTAKE)

    records = json.loads(ProjectsPresenter().projects_json([greeter, docs], {FIRST: 3}))

    assert records == [
        {
            "project_id": str(FIRST),
            "name": "greeter",
            "phase": "VISUAL_DESIGN",
            "cycle": 2,
            "max_cycles": 5,
            "repo_path": "/src/greeter",
            "created_at": "2026-09-24T09:30:00+00:00",
            "open_gates": 3,
        },
        {
            "project_id": str(SECOND),
            "name": "docs",
            "phase": "INTAKE",
            "cycle": 1,
            "max_cycles": 3,
            "repo_path": "/src/docs",
            "created_at": "2026-09-24T09:30:00+00:00",
            "open_gates": 0,
        },
    ]
    assert list(records[0]) == [
        "project_id",
        "name",
        "phase",
        "cycle",
        "max_cycles",
        "repo_path",
        "created_at",
        "open_gates",
    ]


# -- vibey gates --------------------------------------------------------------------------------


def test_no_open_gates_says_nothing_is_waiting() -> None:
    presenter = GatesPresenter()
    assert presenter.gates([], {}) == ["no open gates: nothing is waiting for your answer"]
    assert presenter.gates([], {}, scope="greeter") == [
        "no open gates for project greeter: nothing is waiting for your answer"
    ]
    assert json.loads(presenter.gates_json([], {})) == {"gates": []}


def test_each_gate_reads_as_its_project_kind_prompt_and_answer() -> None:
    gate = _gate(FIRST, prompt="Review artifacts ready for cycle 1.")

    lines = GatesPresenter().gates([gate], {FIRST: "greeter"})

    assert lines == [
        "1 open gate, oldest first -- each is a job waiting for your answer:",
        "",
        "1. greeter: approval gate, raised 2026-09-24 09:30 UTC",
        "   Review artifacts ready for cycle 1.",
        f"   answer with: vibey answer {gate.gate_id} --verdict accept",
    ]


def test_one_projects_list_names_the_project_in_its_header() -> None:
    gates = [_gate(FIRST), _gate(FIRST)]
    lines = GatesPresenter().gates(gates, {FIRST: "greeter"}, scope="greeter")
    assert lines[0] == (
        "2 open gates for project greeter, oldest first -- each is a job waiting for your answer:"
    )


def test_a_prompt_becomes_one_paragraph_wrapped_without_splitting_a_word() -> None:
    url = "https://greeter.example.test/a/deployment/url/that/is/long"
    prompt = f"### Phase 6 Demo Review\n\n- **Live URL**: {url}\n\n  Please   approve."
    gate = _gate(FIRST, kind="deploy_demo_review", prompt=prompt, default_answer="approve")

    lines = GatesPresenter(width=40).gates([gate], {FIRST: "greeter"})

    assert lines[3:7] == [
        "   ### Phase 6 Demo Review - **Live",
        "   URL**:",
        f"   {url}",
        "   Please approve.",
    ]
    assert lines[7] == f"   answer with: vibey answer {gate.gate_id} --verdict approve"


def test_a_gate_with_no_prompt_says_so() -> None:
    lines = GatesPresenter().gates([_gate(FIRST, prompt=" \n\t ")], {FIRST: "greeter"})
    assert lines[3] == "   (no prompt)"


def test_an_answer_with_a_placeholder_says_what_to_put_there() -> None:
    budget = _gate(FIRST, kind="budget_exhausted", options=())
    unknown = _gate(FIRST, kind="a_kind_a_newer_vibey_raises", options=())

    lines = GatesPresenter().gates([budget, unknown], {FIRST: "greeter"})

    assert (
        f"""   answer with: vibey answer {budget.gate_id} --raw '{{"max_dollars": N}}'""" in lines
    )
    assert "   (replace N with the new max_dollars before you run it)" in lines
    assert f"   answer with: vibey answer {unknown.gate_id} --raw '<json>'" in lines
    assert (
        "   (replace <json> with a JSON object that answers the prompt before you run it)"
    ) in lines


def test_the_body_of_the_tenth_gate_is_indented_past_its_number() -> None:
    gates = [_gate(FIRST, prompt=f"gate {n}") for n in range(1, 11)]
    lines = GatesPresenter().gates(gates, {FIRST: "greeter"})
    tenth = lines.index("10. greeter: approval gate, raised 2026-09-24 09:30 UTC")
    assert lines[tenth + 1] == "    gate 10"
    assert lines[tenth + 2].startswith("    answer with: vibey answer ")


def test_raise_times_are_shown_in_utc() -> None:
    raised = datetime(2026, 9, 24, 4, 30, tzinfo=timezone(timedelta(hours=-5)))
    lines = GatesPresenter().gates([_gate(FIRST, raised=raised)], {FIRST: "greeter"})
    assert lines[2] == "1. greeter: approval gate, raised 2026-09-24 09:30 UTC"


def test_gates_json_carries_exactly_the_contract_keys() -> None:
    job = uuid4()
    timeout = AT + timedelta(days=7)
    parked = _gate(FIRST, job_id=job, timeout_at=timeout, prompt="Line one.\nLine two.")
    bare = _gate(
        SECOND, kind="choice", options=("local_only", "deploy"), default_answer="local_only"
    )

    document = json.loads(
        GatesPresenter().gates_json([parked, bare], {FIRST: "greeter", SECOND: "docs"})
    )

    assert document == {
        "gates": [
            {
                "gate_id": str(parked.gate_id),
                "project_id": str(FIRST),
                "project_name": "greeter",
                "job_id": str(job),
                "kind": "approval",
                "prompt": "Line one.\nLine two.",
                "options": ["accept", "changes", "cancel"],
                "default_answer": None,
                "raised_at": "2026-09-24T09:30:00+00:00",
                "timeout_at": "2026-10-01T09:30:00+00:00",
                "answer_with": f"vibey answer {parked.gate_id} --verdict accept",
            },
            {
                "gate_id": str(bare.gate_id),
                "project_id": str(SECOND),
                "project_name": "docs",
                "job_id": None,
                "kind": "choice",
                "prompt": "Accept?",
                "options": ["local_only", "deploy"],
                "default_answer": "local_only",
                "raised_at": "2026-09-24T09:30:00+00:00",
                "timeout_at": None,
                "answer_with": GATE_ANSWERS.command(bare),
            },
        ]
    }
    assert list(document["gates"][0]) == [
        "gate_id",
        "project_id",
        "project_name",
        "job_id",
        "kind",
        "prompt",
        "options",
        "default_answer",
        "raised_at",
        "timeout_at",
        "answer_with",
    ]


# -- the commands, over a stand-in for the database --------------------------------------------


class _Projects:
    def __init__(self, projects: tuple[ProjectRecord, ...]) -> None:
        self._projects = projects

    async def list_all(self) -> tuple[ProjectRecord, ...]:
        return self._projects

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        return next((p for p in self._projects if p.project_id == project_id), None)


class _Gates:
    def __init__(self, gates: tuple[HumanGateRecord, ...]) -> None:
        self._gates = gates

    async def open_all(self) -> tuple[HumanGateRecord, ...]:
        return self._gates

    async def open_for_project(self, project_id: UUID) -> tuple[HumanGateRecord, ...]:
        return tuple(gate for gate in self._gates if gate.project_id == project_id)


def _app(
    projects: tuple[ProjectRecord, ...], gates: tuple[HumanGateRecord, ...]
) -> Callable[[], AbstractAsyncContextManager[SimpleNamespace]]:
    @asynccontextmanager
    async def open_app() -> AsyncIterator[SimpleNamespace]:
        yield SimpleNamespace(projects=_Projects(projects), gates=_Gates(gates))

    return open_app


async def test_projects_counts_each_projects_open_gates(capsys: pytest.CaptureFixture[str]) -> None:
    projects = (_project("greeter", FIRST), _project("docs", SECOND))
    gates = (_gate(FIRST), _gate(SECOND), _gate(FIRST))

    await ProjectsCommand(open_app=_app(projects, gates)).run(as_json=True)  # type: ignore[arg-type]

    records = json.loads(capsys.readouterr().out)
    assert [(r["name"], r["open_gates"]) for r in records] == [("greeter", 2), ("docs", 1)]


async def test_projects_prints_the_table_without_json(capsys: pytest.CaptureFixture[str]) -> None:
    command = ProjectsCommand(open_app=_app((_project("greeter", FIRST),), ()))  # type: ignore[arg-type]
    await command.run(as_json=False)
    assert capsys.readouterr().out.splitlines()[0].startswith("NAME     PHASE")


async def test_a_gate_whose_project_is_gone_by_the_second_read_is_not_listed(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A gate never outlives its project (ON DELETE CASCADE): one whose project vanished
    between the two reads was deleted with it, and waits on no one."""
    kept, orphaned = _gate(FIRST), _gate(SECOND)
    command = GatesCommand(open_app=_app((_project("greeter", FIRST),), (kept, orphaned)))  # type: ignore[arg-type]

    await command.run(None, as_json=True)

    listed = json.loads(capsys.readouterr().out)["gates"]
    assert [gate["gate_id"] for gate in listed] == [str(kept.gate_id)]


async def test_one_projects_gates_are_read_for_that_project_alone(
    capsys: pytest.CaptureFixture[str],
) -> None:
    mine, theirs = _gate(FIRST), _gate(SECOND)
    projects = (_project("greeter", FIRST), _project("docs", SECOND))
    command = GatesCommand(open_app=_app(projects, (mine, theirs)))  # type: ignore[arg-type]

    await command.run(FIRST, as_json=False)

    out = capsys.readouterr().out
    assert out.startswith("1 open gate for project greeter, oldest first")
    assert str(mine.gate_id) in out and str(theirs.gate_id) not in out


async def test_an_unknown_project_exits_1_and_says_so_on_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    command = GatesCommand(open_app=_app((), ()))  # type: ignore[arg-type]

    with pytest.raises(typer.Exit) as exited:
        await command.run(FIRST, as_json=True)

    assert exited.value.exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == f"unknown project {FIRST}\n"
