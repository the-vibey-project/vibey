# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey abandon`, end to end against real PostgreSQL, as the application role.

Every test starts from an empty schema, migrated and granted as `vibey migrate` leaves
it, and runs the command as the restricted role production connects as (ADR-0055): a
query the command needs that the role was not granted fails here as `permission
denied`. The JSON is a fixed contract, so its shape is pinned key by key.
"""

import asyncio
import dataclasses
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import AbandonmentReport, EnqueueRequest, HumanGateRequest
from vibey.application.interfaces import ProjectAbandonmentInterface
from vibey.bootstrap import AppResources, build_app, migrations_dir
from vibey.cli.abandon import ABANDON, ABANDON_PRESENTER
from vibey.cli.interfaces.abandon_interface import (
    AbandonCommandInterface,
    AbandonPresenterInterface,
)
from vibey.cli.main import app
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase
from vibey.infrastructure.db.project_abandonment_store import PostgresProjectAbandonmentStore
from vibey.infrastructure.queue_priority_grant import ProcessCaller

pytestmark = pytest.mark.integration
# CI's GITHUB_ACTIONS makes typer embed ANSI codes; plain substring checks need them off.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
ROLES = TestDatabaseRoles.from_environ(os.environ)
ACCOUNT = ProcessCaller().current().name
KEYS = [
    "project_id",
    "name",
    "from",
    "to",
    "cycle",
    "dry_run",
    "already_abandoned",
    "written",
    "reason",
    "by",
    "account",
    "cancelled_jobs",
    "withdrawn_gates",
]


def _owner() -> str:
    return os.environ["VIBEY_TEST_DATABASE_URL"]


@pytest.fixture(autouse=True)
def _an_empty_schema_the_application_role_runs_on(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fresh() -> None:
        conn = await asyncpg.connect(_owner())
        try:
            await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
            await conn.execute("CREATE SCHEMA public")
        finally:
            await conn.close()
        # Dropping `public` dropped the application role's grants with it: put the
        # schema back as `vibey migrate` leaves it before the role touches it.
        await ROLES.restore(_owner(), migrations_dir())

    asyncio.run(fresh())
    monkeypatch.setenv("VIBEY_PG_URL", ROLES.app_dsn(_owner()))


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["abandon", *args])
    return result.exit_code, result.output


async def _create(repo: Path, phase: Phase) -> tuple[UUID, UUID, UUID]:
    """A project in `phase` with one ready job and one gate on a parked job."""
    async with build_app() as resources:
        project = await resources.projects.create("greeter", repo, max_cycles=3, config={})
        pid = project.project_id
        ready, parked = [
            await resources.jobs.enqueue(
                EnqueueRequest(
                    project_id=pid,
                    cycle=1,
                    phase=Phase.BUILD,
                    kind=kind,
                    idempotency_key=f"key-{kind}",
                )
            )
            for kind in ("build.implement", "build.verify")
        ]
    conn = await asyncpg.connect(_owner())
    try:
        await conn.execute("UPDATE project SET phase = $2 WHERE id = $1", pid, phase.value)
        await conn.execute("UPDATE job SET state = 'awaiting_human' WHERE id = $1", parked.id)
    finally:
        await conn.close()
    async with build_app() as resources:
        gate = await resources.gates.raise_gate(
            pid, parked.id, HumanGateRequest(kind="defect", prompt="requeue or abandon?")
        )
    return pid, ready.id, gate.gate_id


def _project(tmp_path: Path, phase: Phase = Phase.BUILD) -> tuple[UUID, UUID, UUID]:
    repo = tmp_path / "greeter"
    repo.mkdir(exist_ok=True)
    return asyncio.run(_create(repo, phase))


async def _state(pid: UUID) -> tuple[str, list[str], list[EventKind]]:
    """The project's phase, its jobs' states and its ledger's kinds."""
    async with build_app() as resources:
        project = await resources.projects.get(pid)
        assert project is not None
        depth = await resources.jobs.queue_depth(pid)
        events = await resources.ledger.all_for_project(pid)
    states = sorted(state.value for state, count in depth.items() for _ in range(count))
    return project.phase.value, states, [event.kind for event in events]  # type: ignore[misc]


# -- the command -------------------------------------------------------------------------


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(ABANDON, AbandonCommandInterface)
    assert isinstance(ABANDON_PRESENTER, AbandonPresenterInterface)


def test_app_resources_offer_no_way_to_abandon_a_project_but_the_service() -> None:
    async def inspect() -> None:
        async with build_app() as resources:
            assert isinstance(resources.project_abandonment, ProjectAbandonmentInterface)
            for field in dataclasses.fields(AppResources):
                # The store's protocol shares the service's method names, so the concrete
                # class is what tells them apart.
                value = getattr(resources, field.name)
                assert not isinstance(value, PostgresProjectAbandonmentStore), field.name

    asyncio.run(inspect())


def test_abandon_is_a_top_level_command_that_needs_a_project_and_a_reason() -> None:
    top = runner.invoke(app, ["--help"])
    assert "abandon" in top.output
    code, out = _run(str(uuid4()))
    assert code == 2 and "--reason" in out
    code, _ = _run("--reason", "why")
    assert code == 2


@pytest.mark.parametrize(
    ("args", "hint"),
    [
        (("--reason", "   "), "--reason"),
        (("--reason", "why\nforged"), "--reason"),
        (("--reason", "why", "--by", " "), "--by"),
    ],
)
def test_a_reason_or_label_vibey_would_refuse_is_a_usage_error_that_changes_nothing(
    tmp_path: Path, args: tuple[str, ...], hint: str
) -> None:
    pid, _, _ = _project(tmp_path)
    before = asyncio.run(_state(pid))

    code, out = _run(str(pid), *args)

    assert code == 2 and hint in out
    assert asyncio.run(_state(pid)) == before


def test_an_unknown_project_exits_1_and_names_it(tmp_path: Path) -> None:
    _project(tmp_path)
    missing = str(uuid4())

    for extra in ((), ("--dry-run",)):
        code, out = _run(missing, "--reason", "why", *extra)
        assert (code, out.strip()) == (1, f"unknown project {missing}")


# -- abandoning --------------------------------------------------------------------------


def test_abandon_stops_everything_and_says_what_it_stopped(tmp_path: Path) -> None:
    pid, ready, gate = _project(tmp_path)

    code, out = _run(str(pid), "--reason", "built on a foreign spec")

    assert code == 0, out
    lines = out.splitlines()
    assert lines[0] == f"Abandoned greeter ({pid}): build -> abandoned, cycle 1."
    assert lines[1] == f"  by {ACCOUNT} (account {ACCOUNT})"
    assert lines[2] == "  reason: built on a foreign spec"
    assert lines[3] == "  cancelled 2 jobs:"
    assert f"    {ready} build.implement (was ready)" in lines
    assert lines[-2] == "  withdrew 1 gate:"
    assert lines[-1] == f"    {gate} defect"
    phase, states, kinds = asyncio.run(_state(pid))
    assert (phase, states) == ("abandoned", ["cancelled", "cancelled"])
    assert kinds[-2:] == [EventKind.PHASE_TRANSITIONED, EventKind.GATE_WITHDRAWN]


def test_the_json_is_a_fixed_contract(tmp_path: Path) -> None:
    pid, ready, gate = _project(tmp_path)

    code, out = _run(str(pid), "--reason", "superseded", "--by", "vibey-vscode", "--json")

    assert code == 0, out
    document = json.loads(out)
    assert list(document) == KEYS
    assert document["project_id"] == str(pid)
    assert (document["name"], document["from"], document["to"], document["cycle"]) == (
        "greeter",
        "build",
        "abandoned",
        1,
    )
    assert (document["dry_run"], document["already_abandoned"], document["written"]) == (
        False,
        False,
        True,
    )
    assert (document["reason"], document["by"], document["account"]) == (
        "superseded",
        "vibey-vscode",
        ACCOUNT,
    )
    assert document["cancelled_jobs"][0] == {
        "job_id": str(ready),
        "kind": "build.implement",
        "state": "ready",
    }
    assert [job["state"] for job in document["cancelled_jobs"]] == ["ready", "awaiting_human"]
    (withdrawn,) = document["withdrawn_gates"]
    assert (withdrawn["gate_id"], withdrawn["kind"]) == (str(gate), "defect")
    assert withdrawn["job_id"] == document["cancelled_jobs"][1]["job_id"]


def test_a_dry_run_lists_what_would_stop_and_writes_nothing(tmp_path: Path) -> None:
    pid, ready, gate = _project(tmp_path)
    before = asyncio.run(_state(pid))

    code, out = _run(str(pid), "--reason", "superseded", "--dry-run")

    assert code == 0, out
    lines = out.splitlines()
    assert lines[0] == "Dry run: nothing was written."
    assert lines[1] == f"Would abandon greeter ({pid}): build -> abandoned, cycle 1."
    assert "  would cancel 2 jobs:" in lines
    assert f"    {ready} build.implement (was ready)" in lines
    assert lines[-2:] == ["  would withdraw 1 gate:", f"    {gate} defect"]
    document = json.loads(_run(str(pid), "--reason", "superseded", "--dry-run", "--json")[1])
    assert (document["dry_run"], document["written"], document["from"]) == (True, False, "build")
    assert asyncio.run(_state(pid)) == before


def test_abandoning_an_abandoned_project_changes_nothing_and_exits_0(tmp_path: Path) -> None:
    pid, _, _ = _project(tmp_path)
    assert _run(str(pid), "--reason", "first")[0] == 0
    settled = asyncio.run(_state(pid))

    code, out = _run(str(pid), "--reason", "second")
    assert (code, out.strip()) == (
        0,
        f"greeter ({pid}) is already abandoned; nothing was changed.",
    )
    code, out = _run(str(pid), "--reason", "second", "--dry-run")
    assert (code, out.strip()) == (
        0,
        f"greeter ({pid}) is already abandoned; nothing would change.",
    )
    document = json.loads(_run(str(pid), "--reason", "second", "--json")[1])
    assert (document["already_abandoned"], document["written"], document["from"]) == (
        True,
        False,
        "abandoned",
    )
    assert (document["cancelled_jobs"], document["withdrawn_gates"]) == ([], [])
    assert asyncio.run(_state(pid)) == settled


def test_a_done_project_is_refused_with_exit_3_and_left_as_it_is(tmp_path: Path) -> None:
    pid, _, _ = _project(tmp_path, Phase.DONE)
    before = asyncio.run(_state(pid))

    for extra in ((), ("--dry-run",)):
        result = runner.invoke(app, ["abandon", str(pid), "--reason", "no", *extra])
        assert result.exit_code == 3
        assert "Error: the project is done" in result.output

    assert asyncio.run(_state(pid)) == before


# -- the checkout it leaves -------------------------------------------------------------


def _new(repo: Path) -> tuple[int, str]:
    result = runner.invoke(app, ["new", "greeter", "--repo", str(repo)])
    return result.exit_code, result.output


def test_abandoning_a_project_frees_its_checkout_for_a_new_one(tmp_path: Path) -> None:
    """Live on #963: the retry's `vibey new` in the abandoned project's checkout died on a
    raw unique violation. Abandoning now lets the checkout go, and the new project is
    created beside the abandoned one, which stays readable by id."""
    repo = tmp_path / "triaged-963"
    repo.mkdir()
    code, out = _new(repo)
    assert code == 0, out
    first = UUID(out.splitlines()[0].removeprefix("project "))
    code, out = _run(str(first), "--reason", "retry approved by the operator")
    assert code == 0, out

    code, out = _new(repo)

    assert code == 0, out
    second = UUID(out.splitlines()[0].removeprefix("project "))
    assert second != first
    assert asyncio.run(_state(first))[0] == "abandoned"
    assert asyncio.run(_state(second))[0] == "design"


def test_new_in_a_live_projects_checkout_is_refused_naming_it(tmp_path: Path) -> None:
    """Two live projects never share a checkout: the refusal is one `Error:` naming the
    holder's id and phase, with what to do next -- never a traceback -- and exit 3."""
    repo = tmp_path / "held"
    repo.mkdir()
    code, out = _new(repo)
    assert code == 0, out
    holder = UUID(out.splitlines()[0].removeprefix("project "))

    result = runner.invoke(app, ["new", "second", "--repo", str(repo)])

    assert result.exit_code == 3
    assert (
        f"Error: checkout {repo.resolve()} is held by live project {holder} (phase design)"
        in result.output
    )
    assert "vibey abandon PROJECT_ID --reason TEXT" in result.output
    assert "Traceback" not in result.output
    assert "UniqueViolationError" not in result.output

    async def count() -> int:
        async with build_app() as resources:
            return len(await resources.projects.list_all())

    assert asyncio.run(count()) == 1


# -- the presenter -----------------------------------------------------------------------


def test_one_job_and_no_gates_read_in_the_singular_and_as_none(tmp_path: Path) -> None:
    pid, ready, _ = _project(tmp_path)

    async def one_job_report() -> AbandonmentReport:
        async with build_app() as resources:
            report = await resources.project_abandonment.preview(pid, reason="why")
        return dataclasses.replace(report, jobs=report.jobs[:1], gates=())

    lines = ABANDON_PRESENTER.report(asyncio.run(one_job_report()), dry_run=False)

    assert "  cancelled 1 job:" in lines
    assert lines[-1] == "  withdrew 0 gates"
