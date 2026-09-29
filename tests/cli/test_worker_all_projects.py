# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey worker --all-projects` (#1189): one worker serves every project's queue."""

import asyncio
import os
from collections.abc import Iterator
from pathlib import Path
from unittest.mock import AsyncMock, patch
from uuid import UUID

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.application.dto import EnqueueRequest
from vibey.bootstrap import build_app, database_url
from vibey.cli.main import app
from vibey.domain.job import JobState, idempotency_key
from vibey.domain.phase import Phase

pytestmark = pytest.mark.integration
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})


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


@pytest.fixture(autouse=True)
def _fast_engine_preflight() -> Iterator[None]:
    """The startup sweep would otherwise spawn real engine subprocesses."""
    from vibey.application.dto import PreflightResult

    with patch(
        "vibey.infrastructure.engines.loop_process_adapter.LoopProcessAdapter.preflight",
        new=AsyncMock(return_value=PreflightResult(installed=True, version="1.0.0", auth_ok=True)),
    ):
        yield


@pytest.fixture()
def notifier() -> Iterator[AsyncMock]:
    """The LISTEN connection, mocked; its wait raises KeyboardInterrupt to end a
    continuous run once the worker goes idle."""
    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as cls:
        mock = AsyncMock()
        mock.wait_for_job_ready = AsyncMock(side_effect=KeyboardInterrupt)
        cls.return_value = mock
        yield mock


def _seed(tmp_path: Path, names: tuple[str, ...], *, jobs: bool = True) -> list[UUID]:
    async def seed() -> list[UUID]:
        ids: list[UUID] = []
        async with build_app() as resources:
            for name in names:
                repo = tmp_path / name
                repo.mkdir()
                p = await resources.projects.create(name, repo, max_cycles=1, config={})
                ids.append(p.project_id)
                if jobs:
                    await resources.jobs.enqueue(
                        EnqueueRequest(
                            project_id=p.project_id,
                            cycle=p.cycle,
                            phase=Phase.INTAKE,
                            kind="test.work",
                            idempotency_key=idempotency_key(p.project_id, p.cycle, "t", name),
                            requirement={},
                        )
                    )
        return ids

    return asyncio.run(seed())


def _states(project_ids: list[UUID]) -> dict[UUID, set[JobState]]:
    async def read() -> dict[UUID, set[JobState]]:
        async with build_app() as resources:
            found: dict[UUID, set[JobState]] = {}
            for pid in project_ids:
                depth = await resources.jobs.queue_depth(pid)
                found[pid] = {
                    state for state, n in depth.items() if n and isinstance(state, JobState)
                }
            return found

    return asyncio.run(read())


@pytest.mark.parametrize(
    "extra", [["--project", "00000000-0000-0000-0000-000000000001"], ["--wait-for-project", "1"]]
)
def test_all_projects_refuses_a_single_project_flag(extra: list[str]) -> None:
    res = runner.invoke(app, ["worker", "--all-projects", *extra])
    assert res.exit_code == 2
    assert "--all-projects serves every project" in res.output


def test_all_projects_with_nothing_queued_waits_instead_of_exiting(
    notifier: AsyncMock,
) -> None:
    """No project at all is not an error for a worker that serves whatever arrives: the
    single-project worker's `no projects found` exit is exactly the restart loop a
    supervised worker must not fall into."""
    res = runner.invoke(app, ["worker", "--all-projects", "--once"])
    assert res.exit_code == 0, res.output
    assert "worker started: all projects" in res.output
    assert "no ready job" in res.output
    assert "no projects found" not in res.output


def test_all_projects_serves_the_next_job_whichever_project_holds_it(tmp_path: Path) -> None:
    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as cls:
        cls.return_value = AsyncMock()
        first, second = _seed(tmp_path, ("alpha", "beta"))
        res = runner.invoke(app, ["worker", "--all-projects", "--once"])
        assert res.exit_code == 0, res.output
        assert "processed one job" in res.output
        res = runner.invoke(app, ["worker", "--all-projects", "--once"])
        assert res.exit_code == 0, res.output
        assert "processed one job" in res.output

    assert "serving project=alpha" in res.output or "serving project=beta" in res.output
    # Both projects' jobs were claimed and settled (the kind has no handler, so each
    # burned an attempt and went back to ready with a backoff -- nothing is left leased).
    states = _states([first, second])
    assert all(JobState.LEASED not in found for found in states.values())


def test_all_projects_continuous_idles_on_any_projects_notification(
    tmp_path: Path, notifier: AsyncMock
) -> None:
    (only,) = _seed(tmp_path, ("gamma",))
    with patch("vibey.application.queue_reaper.QueueReaper.run_if_due", new=AsyncMock()) as reaper:
        res = runner.invoke(app, ["worker", "--all-projects"])

    assert "processed one job" in res.output
    # Woken by any project, not one.
    assert notifier.wait_for_job_ready.await_args.args == (None,)
    # The fleet-wide reaper pass runs, labelled with the project last served.
    reaper.assert_awaited_with(only)


def test_all_projects_skips_the_queue_reap_until_it_has_served_a_project(
    notifier: AsyncMock,
) -> None:
    with patch("vibey.application.queue_reaper.QueueReaper.run_if_due", new=AsyncMock()) as reaper:
        runner.invoke(app, ["worker", "--all-projects"])
    reaper.assert_not_awaited()
    notifier.wait_for_job_ready.assert_awaited()


def test_a_failing_queue_reap_is_reported_under_all_projects(
    tmp_path: Path, notifier: AsyncMock
) -> None:
    _seed(tmp_path, ("delta",))
    with patch(
        "vibey.application.queue_reaper.QueueReaper.run_if_due",
        new=AsyncMock(side_effect=RuntimeError("the broker went away")),
    ):
        res = runner.invoke(app, ["worker", "--all-projects"])
    assert "queue reap failed: the broker went away" in res.output


def test_a_project_it_cannot_serve_is_refused_and_its_jobs_stay_queued(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The single-project worker exits 2 on an --engines list matching none of its
    engines. Serving every project, the same refusal leaves that project's work queued
    for a worker that can take it, and the worker itself keeps running."""
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    (project_id,) = _seed(tmp_path, ("epsilon",))
    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as cls:
        cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--all-projects", "--once", "--engines", "qwenloop"])

    assert res.exit_code == 0, res.output
    assert "project epsilon refused: its jobs stay queued" in res.output
    assert "no ready job" in res.output
    assert _states([project_id])[project_id] == {JobState.READY}


def test_a_project_with_a_malformed_config_is_refused_with_its_reason(tmp_path: Path) -> None:
    (project_id,) = _seed(tmp_path, ("iota",))

    async def break_config() -> None:
        conn = await asyncpg.connect(database_url())
        try:
            await conn.execute(
                """UPDATE project SET config = '{"engine_environment": 3}'::jsonb WHERE id = $1""",
                project_id,
            )
        finally:
            await conn.close()

    asyncio.run(break_config())
    with patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as cls:
        cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--all-projects", "--once"])

    assert res.exit_code == 0, res.output
    assert "project iota refused (engine_environment project config must be an object)" in (
        res.output
    )
    assert _states([project_id])[project_id] == {JobState.READY}


def test_a_project_gone_between_listing_and_lookup_is_passed_over(tmp_path: Path) -> None:
    _seed(tmp_path, ("zeta",))
    with (
        patch("vibey.infrastructure.db.notifier.PostgresJobReadyNotifier") as cls,
        patch(
            "vibey.infrastructure.db.project_repository.PostgresProjectRepository.get",
            new=AsyncMock(return_value=None),
        ),
    ):
        cls.return_value = AsyncMock()
        res = runner.invoke(app, ["worker", "--all-projects", "--once"])
    assert res.exit_code == 0, res.output
    assert "no ready job" in res.output


def test_all_projects_parallel_loops_share_one_worker(tmp_path: Path, notifier: AsyncMock) -> None:
    _seed(tmp_path, ("eta", "theta"))
    with patch("os.cpu_count", return_value=4):
        res = runner.invoke(app, ["worker", "--all-projects", "-j", "2"])
    assert "worker started: all projects" in res.output
    assert "parallelism=2" in res.output
