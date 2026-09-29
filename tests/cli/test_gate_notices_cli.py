# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey gates --remind`, end to end against real Postgres, as the application role.

The defaults this ships with -- notifications off -- are the case that used to leave no
trace: a gate nobody was told about is now said once, and recorded, and a second sweep
records nothing more.
"""

import asyncio
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest
from typer.testing import CliRunner, Result

from tests.db_roles import TestDatabaseRoles
from vibey.application.dto import HumanGateRequest, ProjectRecord
from vibey.bootstrap import build_app, migrations_dir
from vibey.cli.main import app

pytestmark = pytest.mark.integration
runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
APPROVAL = HumanGateRequest(kind="approval", prompt="Accept?", options=("accept", "changes"))


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


async def _seed(repo: Path, *, stale: bool = False) -> tuple[ProjectRecord, UUID]:
    async with build_app() as resources:
        project = await resources.projects.create("greeter", repo, max_cycles=3, config={})
        gate = await resources.gates.raise_gate(project.project_id, None, APPROVAL)
    if stale:
        conn = await asyncpg.connect(os.environ["VIBEY_TEST_DATABASE_URL"])
        try:
            await conn.execute(
                "UPDATE human_gate SET raised_at = $2 WHERE gate_id = $1",
                gate.gate_id,
                datetime.now(UTC) - timedelta(days=3),
            )
        finally:
            await conn.close()
    return project, gate.gate_id


async def _notices(project_id: UUID) -> list[tuple[str, dict[str, object]]]:
    conn = await asyncpg.connect(os.environ["VIBEY_TEST_DATABASE_URL"])
    try:
        rows = await conn.fetch(
            "SELECT kind, payload FROM event WHERE project_id = $1 "
            "AND kind IN ('GateNotified', 'GateNoticeUndeliverable') ORDER BY seq",
            project_id,
        )
    finally:
        await conn.close()
    return [(row["kind"], json.loads(row["payload"])) for row in rows]


def test_a_gate_nobody_can_be_told_about_is_said_once_and_recorded(tmp_path: Path) -> None:
    project, gate_id = asyncio.run(_seed(tmp_path, stale=True))

    planned = _run("gates", "--remind", "--dry-run", "--json")
    assert planned.exit_code == 0, planned.output
    assert [entry["notice"] for entry in json.loads(planned.stdout)["planned"]] == [0]
    assert asyncio.run(_notices(project.project_id)) == []  # a dry run records nothing

    first = _run("gates", "--remind")
    assert first.exit_code == 0, first.output
    assert "UNDELIVERABLE (disabled) raise notice" in first.stdout
    ((kind, payload),) = asyncio.run(_notices(project.project_id))
    assert kind == "GateNoticeUndeliverable"
    assert payload["gate_id"] == str(gate_id)
    assert payload["reason"] == "disabled"

    # Said once: notifications are off, so there are no reminders to send either.
    again = _run("gates", str(project.project_id), "--remind", "--json")
    assert again.exit_code == 0, again.output
    assert json.loads(again.stdout)["sent"] == []
    assert len(asyncio.run(_notices(project.project_id))) == 1


def test_dry_run_applies_only_with_remind() -> None:
    result = _run("gates", "--dry-run")
    assert result.exit_code == 2
    assert "--dry-run applies only with --remind" in result.output


def test_the_doctor_counts_the_gates_nobody_will_be_told_about(tmp_path: Path) -> None:
    """Read over a pool of its own, as the application role: no build_app, no migration."""
    from vibey.cli.gate_notices import GATE_NOTICE_DOCTOR

    asyncio.run(_seed(tmp_path))
    line = asyncio.run(GATE_NOTICE_DOCTOR.line())
    assert line.startswith(
        "WARN gate-notices         1 gate waiting, nobody will be told: "
        "greeter 1 (notifications disabled)."
    )
