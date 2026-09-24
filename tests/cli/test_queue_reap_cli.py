# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey queue reap`, end to end against real Postgres (ADR-0056)."""

import asyncio
import json
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

import asyncpg
import pytest
import typer
from typer.testing import CliRunner

from vibey.application.dto import EnqueueRequest, JobRecord, QueueReapReport
from vibey.bootstrap import build_app, database_url
from vibey.cli.main import app
from vibey.cli.queue import QUEUE_PRESENTER, QueueCommand
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.domain.queue_reap import PolicyOutcome, ReapAction, ReapCondition, ReapVerdict

pytestmark = pytest.mark.integration
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
PROJECT = UUID("6f1c2a4e-0000-4000-8000-000000000000")


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


async def _seed_expired(repo: Path) -> tuple[UUID, UUID]:
    async with build_app() as resources:
        project = await resources.projects.create(
            "reap-proj", repo, max_cycles=5, config={"project": {"name": "reap-proj"}}
        )
        job = await resources.jobs.enqueue(
            EnqueueRequest(
                project_id=project.project_id,
                cycle=1,
                phase=Phase.BUILD,
                kind="build.implement",
                idempotency_key="key-a",
            )
        )
        await resources.jobs.claim(project.project_id, owner="w", lease=timedelta(seconds=-1))
        return project.project_id, job.id


async def _get(job_id: UUID) -> JobRecord | None:
    async with build_app() as resources:
        return await resources.jobs.get(job_id)


def test_a_dry_run_names_the_reap_and_changes_nothing(tmp_path: Path) -> None:
    _, job_id = asyncio.run(_seed_expired(tmp_path))

    result = runner.invoke(app, ["queue", "reap", "--dry-run"])

    assert result.exit_code == 0, result.output
    assert "(dry run: nothing was changed)" in result.output
    assert "reaped (would):" in result.output
    assert f"requeue     lease_expired  {job_id}" in result.output
    assert "note: broker: none configured" in result.output
    job = asyncio.run(_get(job_id))
    assert job is not None and job.state is JobState.LEASED


def test_a_reap_requeues_and_speaks_json(tmp_path: Path) -> None:
    project_id, job_id = asyncio.run(_seed_expired(tmp_path))

    result = runner.invoke(app, ["queue", "reap", "--project", str(project_id), "--json"])

    assert result.exit_code == 0, result.output
    # stdout alone: the reaper's log lines go to stderr, so JSON stays JSON.
    body = json.loads(result.stdout)
    assert body["ok"] is True and body["dry_run"] is False
    (acted,) = body["acted"]
    assert (acted["object"], acted["action"]) == (str(job_id), "requeue")
    job = asyncio.run(_get(job_id))
    assert job is not None and job.state is JobState.READY
    again = runner.invoke(app, ["queue", "reap", "--project", str(project_id)])
    assert again.exit_code == 0
    assert "reaped: nothing" in again.output


def test_reap_with_no_projects_exits_1() -> None:
    result = runner.invoke(app, ["queue", "reap"])
    assert result.exit_code == 1
    assert "no projects found" in result.output


# -- the command's own branches, over a fake app ---------------------------------------


@dataclass
class _Projects:
    async def get_latest(self) -> Any:
        return type("P", (), {"project_id": PROJECT})()

    async def get(self, project_id: UUID) -> Any:
        return None


@dataclass
class _Reaper:
    report: QueueReapReport

    async def run(self, project_id: UUID, *, dry_run: bool = False, leases: bool = True) -> Any:
        return self.report

    async def run_if_due(self, project_id: UUID) -> Any:
        return None


def _command(reaper: _Reaper) -> QueueCommand:
    @asynccontextmanager
    async def open_app() -> AsyncIterator[Any]:
        yield type("R", (), {"projects": _Projects(), "queue_reaper": reaper})()

    return QueueCommand(open_app=open_app)


def test_a_pass_that_could_not_read_a_source_exits_1(capsys: pytest.CaptureFixture[str]) -> None:
    report = QueueReapReport(project_id=PROJECT, dry_run=False, unreadable=("broker queues: x",))
    with pytest.raises(typer.Exit) as caught:
        asyncio.run(_command(_Reaper(report)).reap(None, dry_run=False, as_json=False))
    assert caught.value.exit_code == 1
    assert "UNREAD: broker queues: x" in capsys.readouterr().out


def test_the_presenter_shows_what_is_stuck_the_policy_and_the_notes() -> None:
    stuck = ReapVerdict(
        subject="celery",
        queue="celery",
        condition=ReapCondition.STALE_READY,
        measured=1_000.0,
        threshold=900.0,
        unit="seconds ready with no consumer",
        action=ReapAction.SURFACE,
    )
    report = QueueReapReport(
        project_id=PROJECT,
        dry_run=False,
        surfaced=(stuck,),
        policy=PolicyOutcome(policy="vibey-reap", verified=False, detail="refused"),
        notes=("a note",),
    )
    lines = QUEUE_PRESENTER.reap(report)
    assert lines[0] == f"queue reap for project {PROJECT}"
    assert "reaped: nothing" in lines
    assert "stuck, surfaced, nothing moved:" in lines
    assert (
        "  surface     stale_ready    celery on celery: 1000 seconds ready with no consumer "
        "(threshold 900)"
    ) in lines
    assert "broker policy 'vibey-reap': NOT VERIFIED (refused)" in lines
    assert "note: a note" in lines
    verified = QueueReapReport(
        project_id=PROJECT,
        dry_run=False,
        policy=PolicyOutcome(policy="vibey-reap", verified=True, detail="already in force"),
    )
    assert "broker policy 'vibey-reap': verified (already in force)" in QUEUE_PRESENTER.reap(
        verified
    )
    body = json.loads(QUEUE_PRESENTER.reap_json(report))
    assert body["ok"] is False
    assert body["policy"] == {"name": "vibey-reap", "verified": False, "detail": "refused"}
    assert body["surfaced"][0]["condition"] == "stale_ready"
    assert json.loads(QUEUE_PRESENTER.reap_json(verified))["ok"] is True
    no_policy = QueueReapReport(project_id=PROJECT, dry_run=True)
    assert json.loads(QUEUE_PRESENTER.reap_json(no_policy))["policy"] is None
