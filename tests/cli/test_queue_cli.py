# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey queue`, end to end against real Postgres (ADR-0054).

The test process owns the temporary repositories it creates, so it is the operator of
their projects. A project whose repository is `/` -- owned by root -- is one this process
is not the operator of."""

import asyncio
import dataclasses
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.application.dto import EnqueueRequest, JobRecord, QueueEntry
from vibey.application.interfaces import JobPriorityStore, QueuePriorityServiceInterface
from vibey.bootstrap import AppResources, build_app, database_url
from vibey.cli.interfaces.queue_interface import QueueCommandInterface, QueuePresenterInterface
from vibey.cli.main import app
from vibey.cli.queue import QUEUE, QUEUE_PRESENTER, QueuePresenter
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import MovedJob, PriorityAction, PriorityChange
from vibey.infrastructure.db.job_priority_repository import PostgresJobPriorityStore

pytestmark = pytest.mark.integration
# See tests/cli/test_operational_commands.py: CI's GITHUB_ACTIONS makes typer
# embed ANSI codes in help and errors; plain substring checks need it off.
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
_LEASE = timedelta(seconds=30)


@pytest.fixture(autouse=True)
async def _use_test_database(monkeypatch: pytest.MonkeyPatch) -> None:
    url = os.environ.get(
        "VIBEY_TEST_DATABASE_URL",
        f"postgresql://{os.environ.get('USER', 'postgres')}@localhost:5432/vibey_test",
    )
    monkeypatch.setenv("VIBEY_PG_URL", url)
    conn = await asyncpg.connect(database_url())
    await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
    await conn.execute("CREATE SCHEMA IF NOT EXISTS public")
    await conn.close()


def _request(project_id: UUID, subject: str, **overrides: object) -> EnqueueRequest:
    fields: dict[str, object] = {
        "project_id": project_id,
        "cycle": 1,
        "phase": Phase.BUILD,
        "kind": "build.implement",
        "idempotency_key": f"key-{subject}",
        "work_item_id": subject,
    }
    fields.update(overrides)
    return EnqueueRequest(**fields)  # type: ignore[arg-type]


async def _seed(repo: Path, *subjects: str) -> tuple[UUID, list[UUID]]:
    async with build_app() as resources:
        project = await resources.projects.create(
            "queue-proj", repo, max_cycles=5, config={"project": {"name": "queue-proj"}}
        )
        ids = [(await resources.jobs.enqueue(_request(project.project_id, s))).id for s in subjects]
        return project.project_id, ids


async def _enqueue(project_id: UUID, subject: str, **overrides: object) -> UUID:
    async with build_app() as resources:
        return (await resources.jobs.enqueue(_request(project_id, subject, **overrides))).id


async def _claim(project_id: UUID) -> JobRecord | None:
    async with build_app() as resources:
        return await resources.jobs.claim(project_id, owner="w", lease=_LEASE)


async def _get(job_id: UUID) -> JobRecord | None:
    async with build_app() as resources:
        return await resources.jobs.get(job_id)


async def _events(project_id: UUID) -> list[LedgerEvent]:
    kinds = {
        EventKind.JOB_PRIORITY_BUMPED,
        EventKind.JOB_PRIORITY_UNBUMPED,
        EventKind.JOB_PRIORITY_REFUSED,
    }
    async with build_app() as resources:
        return [e for e in await resources.ledger.all_for_project(project_id) if e.kind in kinds]


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["queue", *args])
    return result.exit_code, result.output


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(QUEUE, QueueCommandInterface)
    assert isinstance(QUEUE_PRESENTER, QueuePresenterInterface)


def test_app_resources_offer_no_way_to_reorder_the_queue_but_the_service(tmp_path: Path) -> None:
    """The grant cannot be skipped by an entry point that reaches the store directly,
    because no entry point is handed one."""

    async def inspect() -> None:
        async with build_app() as resources:
            assert isinstance(resources.queue_priority, QueuePriorityServiceInterface)
            for field in dataclasses.fields(AppResources):
                value = getattr(resources, field.name)
                assert not isinstance(value, JobPriorityStore), field.name
                assert not isinstance(value, PostgresJobPriorityStore), field.name

    asyncio.run(inspect())


def test_queue_with_no_subcommand_shows_help() -> None:
    code, out = _run()
    assert code == 0
    assert "bump" in out and "unbump" in out and "list" in out
    assert "--config" not in _run("bump", "--help")[1], "the grant is never a caller's path"


# -- bump and unbump --------------------------------------------------------------------------


def test_the_owner_of_the_projects_config_bumps_as_the_operator(tmp_path: Path) -> None:
    pid, (first, target) = asyncio.run(_seed(tmp_path, "a", "b"))

    code, out = _run("bump", str(target), "--project", str(pid))

    assert code == 0, out
    assert f"bumped job {target} (by operator:" in out
    assert "moved    #" in out
    claimed = asyncio.run(_claim(pid))
    assert claimed is not None and claimed.id == target
    (event,) = asyncio.run(_events(pid))
    assert event.kind is EventKind.JOB_PRIORITY_BUMPED
    assert str(event.payload["by"]).startswith("operator:")
    del first


def test_the_project_defaults_to_the_latest_and_the_change_speaks_json(tmp_path: Path) -> None:
    _, (dep,) = asyncio.run(_seed(tmp_path, "dep"))
    pid = asyncio.run(_events_project(tmp_path))
    target = asyncio.run(_enqueue(pid, "target", depends_on=(dep,)))

    code, out = _run("bump", str(target), "--json")

    assert code == 0, out
    document = json.loads(out)
    assert document["action"] == "bump" and document["changed"] is True
    assert [m["job_id"] for m in document["moved"]] == [str(dep), str(target)]


async def _events_project(repo: Path) -> UUID:
    async with build_app() as resources:
        latest = await resources.projects.get_latest()
        assert latest is not None
        return latest.project_id


def test_a_request_that_moves_nothing_is_recorded_and_says_why(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))
    assert _run("bump", str(job))[0] == 0

    code, out = _run("bump", str(job))

    assert code == 0, out
    assert f"job {job}: it is already bumped; nothing moved (recorded; by operator:" in out
    assert len(asyncio.run(_events(pid))) == 2


def test_an_undeclared_source_is_refused_recorded_and_reported(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text('[queue.priority]\nsources = ["storm"]\n')
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))

    code, out = _run("bump", str(job), "--source", "github-label")

    assert code == 3, out
    assert "source 'github-label' is not declared" in out
    assert "vibey ledger search --kind JobPriorityRefused" in out
    record = asyncio.run(_get(job))
    assert record is not None and record.bump_seq is None
    (event,) = asyncio.run(_events(pid))
    assert event.kind is EventKind.JOB_PRIORITY_REFUSED
    assert event.provenance is Provenance.UNTRUSTED
    assert event.payload["by"] == "source:github-label"


@pytest.mark.skipif(os.getuid() == 0, reason="root owns `/`, so root is its operator")
def test_an_account_that_does_not_own_the_config_is_not_the_operator() -> None:
    pid, (job,) = asyncio.run(_seed(Path("/"), "x"))

    code, out = _run("bump", str(job))

    assert code == 3, out
    assert "is not the operator" in out
    (event,) = asyncio.run(_events(pid))
    assert str(event.payload["by"]).startswith("account:")


def test_a_refusal_is_recorded_even_for_a_job_that_does_not_exist(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text('[queue.priority]\nsources = ["storm"]\n')
    pid, _ = asyncio.run(_seed(tmp_path))
    nowhere = uuid4()

    code, out = _run("unbump", str(nowhere), "--source", "stranger")

    assert code == 3, out
    (event,) = asyncio.run(_events(pid))
    assert event.job_id == nowhere
    assert event.payload["action"] == "unbump"


def test_a_declared_source_bumps_and_unbumps(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text('[queue.priority]\nsources = ["storm"]\n')
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))

    bumped = _run("bump", str(job), "--source", "storm")
    unbumped = _run("unbump", str(job), "--source", "storm")

    assert bumped[0] == 0, bumped[1]
    assert unbumped[0] == 0, unbumped[1]
    assert f"un-bumped job {job} (by source:storm)" in unbumped[1]
    assert "was #" in unbumped[1]
    kinds = [e.kind for e in asyncio.run(_events(pid))]
    assert kinds == [EventKind.JOB_PRIORITY_BUMPED, EventKind.JOB_PRIORITY_UNBUMPED]


def test_a_malformed_grant_refuses_rather_than_admitting_nobody_silently(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text("[queue.priority]\nsources = ['operator']\n")
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))

    code, out = _run("bump", str(job))

    assert code == 3, out
    assert "the grant cannot be read" in out and "'operator' is reserved" in out
    assert len(asyncio.run(_events(pid))) == 1


@pytest.mark.skipif(os.getuid() == 0, reason="root reads through a 0000 mode")
@pytest.mark.parametrize("locked", ["directory", "file"])
def test_a_grant_it_cannot_read_is_a_recorded_refusal(tmp_path: Path, locked: str) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    config = repo / "vibey.toml"
    config.write_text('[queue.priority]\nsources = ["storm"]\n')
    pid, (job,) = asyncio.run(_seed(repo, "x"))
    target = repo if locked == "directory" else config
    target.chmod(0)
    try:
        code, out = _run("bump", str(job))
    finally:
        target.chmod(0o755)

    assert code == 3, out
    assert "the grant cannot be read" in out
    (event,) = asyncio.run(_events(pid))
    assert event.kind is EventKind.JOB_PRIORITY_REFUSED
    assert "cannot be read" in str(event.payload["reason"])


def test_unbumping_a_job_a_bumped_job_needs_is_refused_naming_it(tmp_path: Path) -> None:
    pid, (dep,) = asyncio.run(_seed(tmp_path, "dep"))
    target = asyncio.run(_enqueue(pid, "target", depends_on=(dep,)))
    assert _run("bump", str(target))[0] == 0

    code, out = _run("unbump", str(dep), "--json")

    assert code == 3, out
    assert str(target) in out and "un-bump them first" in out


def test_unbumping_a_job_that_is_not_bumped_moves_nothing(tmp_path: Path) -> None:
    _, (job,) = asyncio.run(_seed(tmp_path, "x"))
    document = json.loads(_run("unbump", str(job), "--json")[1])
    assert document["changed"] is False
    assert document["note"] == "it is not bumped; nothing moved"


def test_an_unknown_job_is_refused_and_recorded(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path))
    missing = uuid4()
    code, out = _run("bump", str(missing))
    assert code == 3
    assert f"unknown job {missing}" in out
    (event,) = asyncio.run(_events(pid))
    assert event.payload["reason"] == f"unknown job {missing}"


def test_bumping_a_finished_job_is_a_recorded_no_op(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))

    async def finish() -> None:
        async with build_app() as resources:
            await resources.jobs.claim(pid, owner="w", lease=_LEASE)
            await resources.jobs.ack(job, owner="w")

    asyncio.run(finish())
    code, out = _run("bump", str(job))
    assert code == 0, out
    assert f"job {job}: it is succeeded; nothing to move (recorded; by operator:" in out
    (event,) = asyncio.run(_events(pid))
    assert event.payload["moved"] == []


def test_an_unknown_project_exits_1(tmp_path: Path) -> None:
    code, out = _run("bump", str(uuid4()))
    assert code == 1 and "no projects found" in out
    asyncio.run(_seed(tmp_path))
    missing = uuid4()
    code, out = _run("bump", str(uuid4()), "--project", str(missing))
    assert code == 1 and f"unknown project {missing}" in out


# -- list ---------------------------------------------------------------------------------------


def test_list_shows_running_work_then_claim_order_with_bumps_marked(tmp_path: Path) -> None:
    pid, (running, plain, dep) = asyncio.run(_seed(tmp_path, "running", "plain", "dep"))
    target = asyncio.run(_enqueue(pid, "target", depends_on=(dep,)))
    asyncio.run(_claim(pid))
    assert _run("bump", str(target))[0] == 0

    code, out = _run("list", str(pid))

    assert code == 0, out
    lines = out.strip().splitlines()
    assert lines[0].split()[0] == "running" and str(running) in lines[0]
    assert lines[1].split()[:2] == ["1", "bumped"] and str(dep) in lines[1]
    assert "(pulled in as a bumped job's dependency)" in lines[1]
    assert str(target) in lines[2] and "(waits on 1 job)" in lines[2]
    assert lines[3].split()[0] == "3" and str(plain) in lines[3]
    assert lines[4] == "4 unfinished jobs, 2 bumped; the claim takes waiting work top to bottom"


def test_list_defaults_to_the_latest_project_and_speaks_json(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))
    assert _run("bump", str(job))[0] == 0

    code, out = _run("list", "--json")

    assert code == 0, out
    document = json.loads(out)
    assert document["project_id"] == str(pid)
    (entry,) = document["jobs"]
    assert entry["job_id"] == str(job) and entry["position"] == 1
    assert entry["bump_named"] is True
    assert entry["phase"] == "build" and entry["waiting_on"] == []


def test_list_marks_running_work_with_no_position_in_json(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path, "x"))
    asyncio.run(_claim(pid))
    (entry,) = json.loads(_run("list", str(pid), "--json")[1])["jobs"]
    assert entry["position"] is None and entry["state"] == "leased"
    assert entry["bump_named"] is False


def test_an_empty_queue_says_so(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path))
    code, out = _run("list", str(pid))
    assert code == 0
    assert out.strip() == "the queue is empty: nothing is running or waiting"


def test_list_with_no_projects_or_an_unknown_one_exits_1(tmp_path: Path) -> None:
    code, out = _run("list")
    assert code == 1 and "no projects found" in out
    asyncio.run(_seed(tmp_path))
    missing = uuid4()
    code, out = _run("list", str(missing))
    assert code == 1 and f"unknown project {missing}" in out


# -- design resume --priority (item 7) ------------------------------------------------------------


def _new_project(repo: Path) -> UUID:
    created = runner.invoke(app, ["new", "widget", "--repo", str(repo)])
    assert created.exit_code == 0, created.output
    project_line, _ = created.output.strip().splitlines()
    return UUID(project_line.removeprefix("project "))


def test_design_resume_with_priority_enqueues_the_interview_bumped(tmp_path: Path) -> None:
    pid = _new_project(tmp_path)

    result = runner.invoke(app, ["design", "resume", str(pid), "--priority"])

    assert result.exit_code == 0, result.output
    job_id = UUID(result.output.strip().removeprefix("design job "))
    record = asyncio.run(_get(job_id))
    assert record is not None and record.bump_seq is not None
    (event,) = asyncio.run(_events(pid))
    assert event.payload["action"] == "enqueue"


def test_design_resume_with_priority_on_a_finished_interview_is_a_recorded_no_op(
    tmp_path: Path,
) -> None:
    pid = _new_project(tmp_path)
    plain = runner.invoke(app, ["design", "resume", str(pid)])
    job_id = UUID(plain.output.strip().removeprefix("design job "))

    async def finish() -> None:
        async with build_app() as resources:
            await resources.jobs.claim(pid, owner="w", lease=_LEASE)
            await resources.jobs.ack(job_id, owner="w")

    asyncio.run(finish())

    result = runner.invoke(app, ["design", "resume", str(pid), "--priority"])

    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"design job {job_id}"
    (event,) = asyncio.run(_events(pid))
    assert event.payload["note"] == "it is succeeded; nothing to move"


# -- the presenter's rarer lines ---------------------------------------------------------------


def test_the_presenter_names_jobs_already_ahead_and_a_job_now_bumped_by_name() -> None:
    kept, target = UUID(int=1), UUID(int=3)
    change = PriorityChange(
        action=PriorityAction.BUMP,
        requested_by="operator:adam",
        target=target,
        moved=(MovedJob(job_id=target, bump_seq=4, previous=None),),
        kept=(kept,),
    )
    lines = QueuePresenter().change(change)
    assert any(str(kept) in line and "already bumped" in line for line in lines)
    named = PriorityChange(
        action=PriorityAction.BUMP,
        requested_by="operator:adam",
        target=target,
        moved=(),
        named=True,
    )
    assert "now bumped by name" in "\n".join(QueuePresenter().change(named))
    document = json.loads(QueuePresenter().change_json(change))
    assert document["kept"] == [str(kept)] and document["by"] == "operator:adam"


def test_the_presenter_counts_what_a_job_waits_on() -> None:
    now = datetime.now(UTC)
    job = JobRecord(
        id=UUID(int=9),
        project_id=UUID(int=8),
        cycle=1,
        phase=Phase.BUILD,
        kind="build.implement",
        state=JobState.READY,
        priority=0,
        work_item_id=None,
        payload={},
        requirement={},
        idempotency_key="k",
        attempts=0,
        max_attempts=7,
        run_after=now,
        lease_owner=None,
        lease_expires_at=None,
        assigned_engine=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )
    (line, summary) = QueuePresenter().entries(
        [QueueEntry(job=job, waiting_on=(UUID(int=1), UUID(int=2)))]
    )
    assert line.endswith("(waits on 2 jobs)")
    assert summary.startswith("1 unfinished job, 0 bumped")


def test_a_row_this_vibey_cannot_claim_is_marked_and_given_no_place() -> None:
    from vibey.domain.job import UnrecognizedJobState
    from vibey.domain.phase import UnrecognizedPhase

    now = datetime.now(UTC)

    def record(n: int, **overrides: object) -> JobRecord:
        fields: dict[str, object] = {
            "id": UUID(int=n),
            "project_id": UUID(int=8),
            "cycle": 1,
            "phase": Phase.BUILD,
            "kind": "build.implement",
            "state": JobState.READY,
            "priority": 0,
            "work_item_id": None,
            "payload": {},
            "requirement": {},
            "idempotency_key": f"k{n}",
            "attempts": 0,
            "max_attempts": 7,
            "run_after": now,
            "lease_owner": None,
            "lease_expires_at": None,
            "assigned_engine": None,
            "last_error": None,
            "created_at": now,
            "updated_at": now,
        }
        fields.update(overrides)
        return JobRecord(**fields)  # type: ignore[arg-type]

    entries = [
        QueueEntry(job=record(1)),
        QueueEntry(job=record(2, phase=UnrecognizedPhase("triage"))),
        QueueEntry(job=record(3, state=UnrecognizedJobState("quarantined"))),
        QueueEntry(job=record(4)),
    ]
    lines = QueuePresenter().entries(entries)
    assert lines[0].split()[0] == "1"
    assert lines[1].split()[0] == "-" and "not claimable by this vibey: phase 'triage'" in lines[1]
    assert lines[2].split()[0] == "-" and "state 'quarantined'" in lines[2]
    assert lines[3].split()[0] == "2"
    jobs = json.loads(QueuePresenter().entries_json(UUID(int=8), entries))["jobs"]
    assert [j["position"] for j in jobs] == [1, None, None, 2]
    assert [j["claimable_here"] for j in jobs] == [True, False, False, True]
