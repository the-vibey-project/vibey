# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey queue`, end to end against real Postgres (ADR-0054)."""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.application.dto import EnqueueRequest, JobRecord, QueueEntry
from vibey.bootstrap import build_app, database_url
from vibey.cli.interfaces.queue_interface import QueueCommandInterface, QueuePresenterInterface
from vibey.cli.main import app
from vibey.cli.queue import QUEUE, QUEUE_PRESENTER, QueuePresenter
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import MovedJob, PriorityAction, PriorityChange

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


async def _seed(tmp_path: Path, *subjects: str) -> tuple[UUID, list[UUID]]:
    async with build_app() as resources:
        project = await resources.projects.create(
            "queue-proj", tmp_path, max_cycles=5, config={"project": {"name": "queue-proj"}}
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
    async with build_app() as resources:
        return [
            e
            for e in await resources.ledger.all_for_project(project_id)
            if e.kind
            in {
                EventKind.JOB_PRIORITY_BUMPED,
                EventKind.JOB_PRIORITY_UNBUMPED,
                EventKind.JOB_PRIORITY_REFUSED,
            }
        ]


def _run(*args: str) -> tuple[int, str]:
    result = runner.invoke(app, ["queue", *args])
    return result.exit_code, result.output


def test_the_shared_instances_satisfy_their_interfaces() -> None:
    assert isinstance(QUEUE, QueueCommandInterface)
    assert isinstance(QUEUE_PRESENTER, QueuePresenterInterface)


def test_queue_with_no_subcommand_shows_help() -> None:
    code, out = _run()
    assert code == 0
    assert "bump" in out and "unbump" in out and "list" in out


# -- bump ------------------------------------------------------------------------


def test_the_operator_bumps_a_job_to_run_next(tmp_path: Path) -> None:
    pid, (first, second, target) = asyncio.run(_seed(tmp_path, "a", "b", "c"))

    code, out = _run("bump", str(target))

    assert code == 0, out
    assert f"bumped job {target} (source: operator)" in out
    assert "moved    #" in out
    claimed = asyncio.run(_claim(pid))
    assert claimed is not None and claimed.id == target
    (event,) = asyncio.run(_events(pid))
    assert event.kind is EventKind.JOB_PRIORITY_BUMPED
    assert event.payload["source"] == "operator"
    assert event.provenance is Provenance.TRUSTED
    del first, second


def test_bump_pulls_dependencies_forward_and_says_so_in_json(tmp_path: Path) -> None:
    pid, (dep,) = asyncio.run(_seed(tmp_path, "dep"))
    target = asyncio.run(_enqueue(pid, "target", depends_on=(dep,)))

    code, out = _run("bump", str(target), "--json")

    assert code == 0, out
    document = json.loads(out)
    assert document["action"] == "bump"
    assert document["changed"] is True
    assert [m["job_id"] for m in document["moved"]] == [str(dep), str(target)]


def test_a_replayed_bump_moves_nothing_and_says_so(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))
    assert _run("bump", str(job))[0] == 0

    code, out = _run("bump", str(job))

    assert code == 0, out
    assert f"job {job} is already bumped; nothing moved" in out
    assert len(asyncio.run(_events(pid))) == 1


def test_an_undeclared_source_is_refused_recorded_and_reported(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))
    config = tmp_path / "vibey.toml"
    config.write_text('[queue.priority]\nsources = ["storm"]\n')

    code, out = _run("bump", str(job), "--source", "github-label", "--config", str(config))

    assert code == 3, out
    assert "refused: source 'github-label' may not reorder the queue" in out
    assert "vibey ledger search --kind JobPriorityRefused" in out
    record = asyncio.run(_get(job))
    assert record is not None and record.bump_seq is None
    (event,) = asyncio.run(_events(pid))
    assert event.kind is EventKind.JOB_PRIORITY_REFUSED
    assert event.provenance is Provenance.UNTRUSTED
    assert event.payload["source"] == "github-label"


def test_a_declared_source_bumps_and_unbumps(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))
    config = tmp_path / "vibey.toml"
    config.write_text('[queue.priority]\nsources = ["storm"]\n')

    bumped = _run("bump", str(job), "--source", "storm", "--config", str(config))
    unbumped = _run("unbump", str(job), "--source", "storm", "--config", str(config))

    assert bumped[0] == 0, bumped[1]
    assert unbumped[0] == 0, unbumped[1]
    assert f"un-bumped job {job} (source: storm)" in unbumped[1]
    assert "was #" in unbumped[1]
    kinds = [e.kind for e in asyncio.run(_events(pid))]
    assert kinds == [EventKind.JOB_PRIORITY_BUMPED, EventKind.JOB_PRIORITY_UNBUMPED]


def test_the_operator_is_admitted_with_no_config_file_at_all(tmp_path: Path) -> None:
    _, (job,) = asyncio.run(_seed(tmp_path, "x"))
    code, out = _run("bump", str(job), "--config", str(tmp_path / "absent.toml"))
    assert code == 0, out


def test_a_malformed_declaration_is_an_error_not_an_empty_grant(tmp_path: Path) -> None:
    _, (job,) = asyncio.run(_seed(tmp_path, "x"))
    config = tmp_path / "vibey.toml"
    config.write_text("[queue.priority]\nsources = ['operator']\n")

    code, out = _run("bump", str(job), "--config", str(config))

    assert code == 3, out
    assert "'operator' is reserved" in out


def test_unbumping_a_job_that_is_not_bumped_moves_nothing(tmp_path: Path) -> None:
    _, (job,) = asyncio.run(_seed(tmp_path, "x"))

    code, out = _run("unbump", str(job), "--json")

    assert code == 0, out
    document = json.loads(out)
    assert document["changed"] is False
    assert _run("unbump", str(job))[1].strip() == f"job {job} is not bumped; nothing moved"


def test_an_unknown_job_is_an_error(tmp_path: Path) -> None:
    missing = uuid4()
    asyncio.run(_seed(tmp_path))
    code, out = _run("bump", str(missing))
    assert code == 3
    assert f"unknown job {missing}" in out


def test_a_finished_job_cannot_be_moved(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))

    async def finish() -> None:
        async with build_app() as resources:
            await resources.jobs.claim(pid, owner="w", lease=_LEASE)
            await resources.jobs.ack(job, owner="w")

    asyncio.run(finish())
    code, out = _run("bump", str(job))
    assert code == 3
    assert "cannot be moved in the queue: it is succeeded" in out
    assert "vibey queue list" in out


# -- list ------------------------------------------------------------------------------


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
    assert str(target) in lines[2] and "(waits on 1 job)" in lines[2]
    assert lines[3].split()[0] == "3" and str(plain) in lines[3]
    assert lines[4] == "4 unfinished jobs, 2 bumped; the claim takes waiting work top to bottom"


def test_list_defaults_to_the_latest_project_and_speaks_json(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))

    code, out = _run("list", "--json")

    assert code == 0, out
    document = json.loads(out)
    assert document["project_id"] == str(pid)
    (entry,) = document["jobs"]
    assert entry["job_id"] == str(job)
    assert entry["position"] == 1
    assert entry["bump_seq"] is None
    assert entry["phase"] == "build"
    assert entry["waiting_on"] == []


def test_list_marks_running_work_with_no_position_in_json(tmp_path: Path) -> None:
    pid, (job,) = asyncio.run(_seed(tmp_path, "x"))
    asyncio.run(_claim(pid))
    (entry,) = json.loads(_run("list", str(pid), "--json")[1])["jobs"]
    assert entry["position"] is None and entry["state"] == "leased"
    del job


def test_an_empty_queue_says_so(tmp_path: Path) -> None:
    pid, _ = asyncio.run(_seed(tmp_path))
    code, out = _run("list", str(pid))
    assert code == 0
    assert out.strip() == "the queue is empty: nothing is running or waiting"


def test_list_with_no_projects_or_an_unknown_one_exits_1(tmp_path: Path) -> None:
    code, out = _run("list")
    assert code == 1
    assert "no projects found" in out
    asyncio.run(_seed(tmp_path))
    missing = uuid4()
    code, out = _run("list", str(missing))
    assert code == 1
    assert f"unknown project {missing}" in out


# -- design resume --priority ----------------------------------------------------------


def test_design_resume_with_priority_enqueues_the_interview_bumped(tmp_path: Path) -> None:
    created = runner.invoke(app, ["new", "widget", "--repo", str(tmp_path)])
    assert created.exit_code == 0, created.output
    project_line, _ = created.output.strip().splitlines()
    pid = UUID(project_line.removeprefix("project "))

    result = runner.invoke(app, ["design", "resume", str(pid), "--priority"])

    assert result.exit_code == 0, result.output
    job_id = UUID(result.output.strip().removeprefix("design job "))
    record = asyncio.run(_get(job_id))
    assert record is not None and record.bump_seq is not None
    (event,) = asyncio.run(_events(pid))
    assert event.payload["action"] == "enqueue"


# -- the presenter's rarer lines -------------------------------------------------------


def test_the_presenter_names_jobs_already_ahead_and_jobs_that_block() -> None:
    kept, blocked, target = UUID(int=1), UUID(int=2), UUID(int=3)
    change = PriorityChange(
        action=PriorityAction.BUMP,
        source="operator",
        target=target,
        moved=(MovedJob(job_id=target, bump_seq=4, previous=None),),
        kept=(kept,),
        blocked_by=(blocked,),
    )
    lines = QueuePresenter().change(change)
    assert any(str(kept) in line and "already bumped" in line for line in lines)
    assert any(str(blocked) in line and "until someone resolves it" in line for line in lines)
    document = json.loads(QueuePresenter().change_json(change))
    assert document["kept"] == [str(kept)] and document["blocked_by"] == [str(blocked)]


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
