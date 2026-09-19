# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import asyncio
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibey.bootstrap import build_app
from vibey.cli.main import _work_once, app
from vibey.domain.errors import WrongPhase

runner = CliRunner()


@pytest.mark.asyncio
async def test_work_once_raises_wrong_phase_on_unrecognized_phase(tmp_path: Path) -> None:
    async with build_app() as resources:
        project = await resources.projects.create(
            "test-proj-work-once", tmp_path, max_cycles=3, config={}
        )
        async with resources.projects._pool.acquire() as conn:
            await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'future_phase_cli'")
            await conn.execute(
                "UPDATE project SET phase = 'future_phase_cli'::phase WHERE id = $1",
                project.project_id,
            )

    with pytest.raises(WrongPhase, match="is unknown; upgrade vibey"):
        await _work_once(project.project_id, "scripted", 10, 10.0)


def test_worker_refuses_project_with_unrecognized_phase(tmp_path: Path) -> None:
    async def seed():
        async with build_app() as resources:
            project = await resources.projects.create(
                "test-proj-worker", tmp_path, max_cycles=3, config={}
            )
            async with resources.projects._pool.acquire() as conn:
                await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'future_phase_cli2'")
                await conn.execute(
                    "UPDATE project SET phase = 'future_phase_cli2'::phase WHERE id = $1",
                    project.project_id,
                )
            return project.project_id

    asyncio.run(seed())

    res = runner.invoke(app, ["worker", "--once"])
    assert res.exit_code == 1
    assert "refusing to dispatch; upgrade vibey" in res.output
