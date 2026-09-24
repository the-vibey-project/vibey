# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey projects` and `vibey gates`, end to end against real Postgres.

Every command here runs as the application role, under the grants production runs it under
(ADR-0055). Both commands read every project and every gate, so each test starts from an
empty database: nothing another test left behind can be listed.
"""

import asyncio
import json
import os
import shlex
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner, Result

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import EnqueueRequest, HumanGateRecord, HumanGateRequest, ProjectRecord
from vibey.bootstrap import build_app, migrations_dir
from vibey.cli.main import app
from vibey.domain.phase import Phase

pytestmark = pytest.mark.integration
# See tests/cli/test_operational_commands.py: CI's GITHUB_ACTIONS makes typer embed ANSI codes
# in help and errors; plain substring checks need it off.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
AT = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)
APPROVAL = HumanGateRequest(
    kind="approval",
    prompt="Review artifacts ready for cycle 1. Accept, request changes, or ask questions.",
    options=("accept", "changes", "cancel"),
)
BUDGET = HumanGateRequest(
    kind="budget_exhausted",
    prompt="cycle budget exhausted: $15.02 spent of $15.00 cap (212 turns).",
)


@pytest.fixture(autouse=True)
async def _an_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]
    conn = await asyncpg.connect(owner)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()
    await TestDatabaseRoles.from_environ(os.environ).restore(owner, migrations_dir())
    monkeypatch.setenv("VIBEY_PG_URL", os.environ["VIBEY_TEST_APP_DATABASE_URL"])


def _run(*args: str) -> Result:
    return runner.invoke(app, list(args))


async def _as_owner(sql: str, *args: object) -> None:
    """Fixture work the application never does -- pinning a timestamp, widening the phase
    enum -- as the schema's owner."""
    conn = await asyncpg.connect(os.environ["VIBEY_TEST_DATABASE_URL"])
    try:
        await conn.execute(sql, *args)
    finally:
        await conn.close()


async def _new_project(name: str, repo: Path, *, created: datetime | None = None) -> ProjectRecord:
    async with build_app() as resources:
        project = await resources.projects.create(name, repo, max_cycles=3, config={})
    if created is None:
        return project
    await _as_owner("UPDATE project SET created_at = $2 WHERE id = $1", project.project_id, created)
    async with build_app() as resources:
        pinned = await resources.projects.get(project.project_id)
    assert pinned is not None
    return pinned


async def _raise(
    project_id: UUID,
    request: HumanGateRequest,
    *,
    with_job: bool = False,
    raised: datetime | None = None,
) -> HumanGateRecord:
    async with build_app() as resources:
        job_id = None
        if with_job:
            job = await resources.jobs.enqueue(
                EnqueueRequest(
                    project_id=project_id,
                    cycle=1,
                    phase=Phase.REVIEW,
                    kind="review.collect",
                    idempotency_key=f"collect-{uuid4()}",
                )
            )
            job_id = job.id
        gate = await resources.gates.raise_gate(project_id, job_id, request)
    if raised is None:
        return gate
    await _as_owner("UPDATE human_gate SET raised_at = $2 WHERE gate_id = $1", gate.gate_id, raised)
    async with build_app() as resources:
        pinned = await resources.gates.get(gate.gate_id)
    assert pinned is not None
    return pinned


async def _answer(gate_id: UUID) -> None:
    async with build_app() as resources:
        await resources.gates.answer(gate_id, answer={"verdict": "accept"}, answered_by="test")


async def _gate(gate_id: UUID) -> HumanGateRecord:
    async with build_app() as resources:
        gate = await resources.gates.get(gate_id)
    assert gate is not None
    return gate


# -- vibey projects -----------------------------------------------------------------------------


def test_projects_with_none_says_how_to_make_one_and_exits_0() -> None:
    text = _run("projects")
    assert text.exit_code == 0, text.output
    assert text.stdout == "no projects yet; create one with `vibey new <name> --repo <path>`\n"

    machine = _run("projects", "--json")
    assert machine.exit_code == 0, machine.output
    assert json.loads(machine.stdout) == []


def test_projects_lists_one_project_with_exactly_the_contract_keys(tmp_path: Path) -> None:
    async def seed() -> ProjectRecord:
        project = await _new_project("greeter", tmp_path)
        await _raise(project.project_id, APPROVAL)
        await _answer((await _raise(project.project_id, BUDGET)).gate_id)
        return project

    project = asyncio.run(seed())

    machine = _run("projects", "--json")
    assert machine.exit_code == 0, machine.output
    assert json.loads(machine.stdout) == [
        {
            "project_id": str(project.project_id),
            "name": "greeter",
            "phase": "INTAKE",
            "cycle": 1,
            "max_cycles": 3,
            "repo_path": str(tmp_path.resolve()),
            "created_at": project.created_at.isoformat(),
            "open_gates": 1,
        }
    ]

    text = _run("projects")
    assert text.exit_code == 0, text.output
    header, row, blank, summary = text.stdout.splitlines()
    assert header.split("  ")[0] == "NAME"
    assert row.split() == [
        "greeter",
        "INTAKE",
        "1/3",
        "1",
        *project.created_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M").split(),
        str(project.project_id),
    ]
    assert blank == ""
    assert summary == (
        "1 project, newest first. 1 open gate is waiting for your answer: `vibey gates` lists them."
    )


def test_projects_lists_many_newest_first_each_with_its_open_gates(tmp_path: Path) -> None:
    async def seed() -> list[ProjectRecord]:
        oldest = await _new_project("oldest", tmp_path / "a", created=AT)
        newest = await _new_project("newest", tmp_path / "b", created=AT + timedelta(hours=2))
        middle = await _new_project("middle", tmp_path / "c", created=AT + timedelta(hours=1))
        await _raise(oldest.project_id, APPROVAL)
        await _raise(oldest.project_id, BUDGET)
        await _raise(newest.project_id, APPROVAL)
        await _answer((await _raise(newest.project_id, BUDGET)).gate_id)
        return [newest, middle, oldest]

    expected = asyncio.run(seed())

    machine = _run("projects", "--json")
    assert machine.exit_code == 0, machine.output
    records = json.loads(machine.stdout)
    assert [r["project_id"] for r in records] == [str(p.project_id) for p in expected]
    assert [(r["name"], r["open_gates"]) for r in records] == [
        ("newest", 1),
        ("middle", 0),
        ("oldest", 2),
    ]

    text = _run("projects")
    rows = text.stdout.splitlines()[1:4]
    assert [row.split()[0] for row in rows] == ["newest", "middle", "oldest"]
    assert text.stdout.splitlines()[-1] == (
        "3 projects, newest first. 3 open gates are waiting for your answer: `vibey gates` "
        "lists them."
    )


def test_projects_shows_a_phase_a_newer_vibey_wrote_as_its_stored_text(tmp_path: Path) -> None:
    """vibey#287: a project in a phase this vibey does not know is listed, not a crash."""

    async def seed() -> ProjectRecord:
        project = await _new_project("from-the-future", tmp_path)
        # ALTER TYPE is the owner's (ADR-0055); the application role may not.
        await _as_owner("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'future_phase_projects'")
        await _as_owner(
            "UPDATE project SET phase = 'future_phase_projects'::phase WHERE id = $1",
            project.project_id,
        )
        return project

    project = asyncio.run(seed())

    machine = _run("projects", "--json")
    assert machine.exit_code == 0, machine.output
    (record,) = json.loads(machine.stdout)
    assert record["project_id"] == str(project.project_id)
    assert record["phase"] == "future_phase_projects"

    text = _run("projects")
    assert text.exit_code == 0, text.output
    assert text.stdout.splitlines()[1].split()[1] == "future_phase_projects"


# -- vibey gates --------------------------------------------------------------------------------


def test_gates_with_none_waiting_says_so_and_exits_0() -> None:
    text = _run("gates")
    assert text.exit_code == 0, text.output
    assert text.stdout == "no open gates: nothing is waiting for your answer\n"

    machine = _run("gates", "--json")
    assert machine.exit_code == 0, machine.output
    assert json.loads(machine.stdout) == {"gates": []}


def test_gates_lists_one_gate_with_exactly_the_contract_keys(tmp_path: Path) -> None:
    timeout = AT + timedelta(days=7)
    request = HumanGateRequest(
        kind="choice",
        prompt="Review accepted. Deploy to target infrastructure?",
        options=("local_only", "deploy"),
        default_answer="local_only",
        timeout_at=timeout,
    )

    async def seed() -> tuple[ProjectRecord, HumanGateRecord]:
        project = await _new_project("greeter", tmp_path)
        return project, await _raise(project.project_id, request, with_job=True)

    project, gate = asyncio.run(seed())
    assert gate.job_id is not None

    machine = _run("gates", "--json")
    assert machine.exit_code == 0, machine.output
    document = json.loads(machine.stdout)
    assert document == {
        "gates": [
            {
                "gate_id": str(gate.gate_id),
                "project_id": str(project.project_id),
                "project_name": "greeter",
                "job_id": str(gate.job_id),
                "kind": "choice",
                "prompt": "Review accepted. Deploy to target infrastructure?",
                "options": ["local_only", "deploy"],
                "default_answer": "local_only",
                "raised_at": gate.raised_at.isoformat(),
                "timeout_at": timeout.isoformat(),
                "answer_with": f"vibey answer {gate.gate_id} --choice local_only",
            }
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

    text = _run("gates")
    assert text.exit_code == 0, text.output
    raised = gate.raised_at.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")
    assert text.stdout.splitlines() == [
        "1 open gate, oldest first -- each is a job waiting for your answer:",
        "",
        f"1. greeter: choice gate, raised {raised}",
        "   Review accepted. Deploy to target infrastructure?",
        f"   answer with: vibey answer {gate.gate_id} --choice local_only",
    ]


def test_gates_lists_every_projects_open_gates_oldest_first(tmp_path: Path) -> None:
    async def seed() -> list[tuple[str, HumanGateRecord]]:
        greeter = await _new_project("greeter", tmp_path / "a")
        docs = await _new_project("docs", tmp_path / "b")
        newest = await _raise(greeter.project_id, APPROVAL, raised=AT + timedelta(minutes=2))
        oldest = await _raise(docs.project_id, BUDGET, raised=AT)
        middle = await _raise(greeter.project_id, BUDGET, raised=AT + timedelta(minutes=1))
        answered = await _raise(docs.project_id, APPROVAL, raised=AT - timedelta(minutes=1))
        await _answer(answered.gate_id)
        return [("docs", oldest), ("greeter", middle), ("greeter", newest)]

    expected = asyncio.run(seed())

    machine = _run("gates", "--json")
    assert machine.exit_code == 0, machine.output
    listed = json.loads(machine.stdout)["gates"]
    assert [(g["project_name"], g["gate_id"]) for g in listed] == [
        (name, str(gate.gate_id)) for name, gate in expected
    ]
    assert [g["answer_with"] for g in listed] == [
        f"""vibey answer {expected[0][1].gate_id} --raw '{{"max_dollars": N}}'""",
        f"""vibey answer {expected[1][1].gate_id} --raw '{{"max_dollars": N}}'""",
        f"vibey answer {expected[2][1].gate_id} --verdict accept",
    ]

    text = _run("gates")
    lines = text.stdout.splitlines()
    assert lines[0] == "3 open gates, oldest first -- each is a job waiting for your answer:"
    headers = [line for line in lines[1:] if line[:1].isdigit()]
    assert headers == [
        "1. docs: budget_exhausted gate, raised 2026-09-24 09:00 UTC",
        "2. greeter: budget_exhausted gate, raised 2026-09-24 09:01 UTC",
        "3. greeter: approval gate, raised 2026-09-24 09:02 UTC",
    ]
    assert lines.count("   (replace N with the new max_dollars before you run it)") == 2


def test_gates_for_one_project_lists_only_that_projects_gates(tmp_path: Path) -> None:
    async def seed() -> tuple[ProjectRecord, HumanGateRecord, HumanGateRecord]:
        greeter = await _new_project("greeter", tmp_path / "a")
        docs = await _new_project("docs", tmp_path / "b")
        mine = await _raise(greeter.project_id, APPROVAL)
        theirs = await _raise(docs.project_id, APPROVAL)
        return greeter, mine, theirs

    greeter, mine, theirs = asyncio.run(seed())

    machine = _run("gates", str(greeter.project_id), "--json")
    assert machine.exit_code == 0, machine.output
    assert [g["gate_id"] for g in json.loads(machine.stdout)["gates"]] == [str(mine.gate_id)]

    text = _run("gates", str(greeter.project_id))
    assert text.exit_code == 0, text.output
    assert text.stdout.splitlines()[0] == (
        "1 open gate for project greeter, oldest first -- each is a job waiting for your answer:"
    )
    assert str(mine.gate_id) in text.stdout
    assert str(theirs.gate_id) not in text.stdout


def test_gates_for_a_project_with_none_waiting_says_so(tmp_path: Path) -> None:
    async def seed() -> ProjectRecord:
        greeter = await _new_project("greeter", tmp_path / "a")
        docs = await _new_project("docs", tmp_path / "b")
        await _raise(docs.project_id, APPROVAL)
        return greeter

    greeter = asyncio.run(seed())

    text = _run("gates", str(greeter.project_id))
    assert text.exit_code == 0, text.output
    assert text.stdout == (
        "no open gates for project greeter: nothing is waiting for your answer\n"
    )
    machine = _run("gates", str(greeter.project_id), "--json")
    assert json.loads(machine.stdout) == {"gates": []}


@pytest.mark.parametrize("form", [(), ("--json",)], ids=["text", "json"])
def test_gates_for_an_unknown_project_exits_1_on_stderr(form: tuple[str, ...]) -> None:
    unknown = uuid4()
    result = _run("gates", str(unknown), *form)
    assert result.exit_code == 1
    assert result.stdout == ""
    assert result.stderr == f"unknown project {unknown}\n"


def test_without_a_database_both_commands_say_so_rather_than_crash(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VIBEY_PG_URL")
    for command in ("projects", "gates"):
        result = _run(command)
        assert result.exit_code == 3, command
        assert "VIBEY_PG_URL is not set" in result.stderr, command


# -- every printed command answers its gate -----------------------------------------------------


@pytest.mark.parametrize(
    ("request_", "answer"),
    [
        (
            HumanGateRequest(kind="question", prompt="scope: q1: What? [default: a CLI]"),
            {"answers": {}, "accept_defaults": True},
        ),
        (APPROVAL, {"verdict": "accept"}),
        (
            HumanGateRequest(
                kind="deploy_acceptance",
                prompt="Grant explicit mutation consent.",
                options=("accept", "reject"),
                default_answer="reject",
            ),
            {"choice": "reject"},
        ),
        (HumanGateRequest(kind="delivery_exhausted", prompt="Answer anything."), {}),
    ],
    ids=["interview", "review", "consent", "any-answer"],
)
def test_the_printed_command_answers_its_gate_as_written(
    tmp_path: Path, request_: HumanGateRequest, answer: dict[str, object]
) -> None:
    """`answer_with` is the command a beginner runs: run exactly that, through `vibey`."""

    async def seed() -> HumanGateRecord:
        project = await _new_project("greeter", tmp_path)
        return await _raise(project.project_id, request_, with_job=True)

    gate = asyncio.run(seed())
    (listed,) = json.loads(_run("gates", "--json").stdout)["gates"]
    program, *arguments = shlex.split(listed["answer_with"])
    assert program == "vibey"

    answered = _run(*arguments)

    assert answered.exit_code == 0, answered.output
    assert answered.stdout == f"answered {gate.gate_id}\n"
    settled = asyncio.run(_gate(gate.gate_id))
    assert settled.answer == answer
    assert json.loads(_run("gates", "--json").stdout) == {"gates": []}
