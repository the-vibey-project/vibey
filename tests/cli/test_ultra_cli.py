# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey ultra` and `vibey budget no-cap` / `cap`, end to end against real PostgreSQL as
the application role (ADR-0063, sub-doctrine 8.b's no-cap path)."""

import asyncio
import json
import os
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest
from typer.testing import CliRunner

from tests.db_roles import TestDatabaseRoles
from vibey.bootstrap import build_app, migrations_dir
from vibey.cli.main import app
from vibey.cli.ultra import UltraCommand
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.ultra import NO_CAP_PHRASE
from vibey.infrastructure.db.ultra_control_store import PostgresUltraControlStore

pytestmark = pytest.mark.integration

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})
ROLES = TestDatabaseRoles.from_environ(os.environ)


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
        await ROLES.restore(_owner(), migrations_dir())

    asyncio.run(fresh())
    monkeypatch.setenv("VIBEY_PG_URL", ROLES.app_dsn(_owner()))


def _project(tmp_path: Path, config: dict[str, object] | None = None) -> UUID:
    async def create() -> UUID:
        async with build_app() as resources:
            repo = tmp_path / "repo"
            repo.mkdir(exist_ok=True)
            project = await resources.projects.create("p", repo, max_cycles=3, config=config or {})
            return project.project_id

    return asyncio.run(create())


def _ultra_events(project_id: UUID) -> list[LedgerEvent]:
    async def read() -> list[LedgerEvent]:
        async with build_app() as resources:
            return [
                e
                for e in await resources.ledger.all_for_project(project_id)
                if e.kind
                in {
                    EventKind.ULTRA_STARTED,
                    EventKind.ULTRA_STOPPED,
                    EventKind.ULTRA_NO_CAP_CHANGED,
                }
            ]

    return asyncio.run(read())


def test_start_status_and_stop_are_trusted_events_on_the_ledger(tmp_path: Path) -> None:
    pid = _project(tmp_path, {"max_cycle_dollars": 5.0})

    result = runner.invoke(app, ["ultra", "start", str(pid)])
    assert result.exit_code == 0, result.output
    assert "ULTRA: running" in result.output and "$5.00" in result.output

    result = runner.invoke(app, ["ultra", "status", "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.output)
    assert document["active"] is True and document["rate_per_hour"] is None

    result = runner.invoke(app, ["ultra", "stop", "--by", "vibey-vscode"])
    assert result.exit_code == 0, result.output
    assert "Stopped" in result.output and "ULTRA: stopped" in result.output

    events = _ultra_events(pid)
    assert [e.kind for e in events] == [EventKind.ULTRA_STARTED, EventKind.ULTRA_STOPPED]
    assert all(e.provenance is Provenance.TRUSTED for e in events)
    assert events[1].payload["by"] == "vibey-vscode"
    assert events[1].payload["device"]


def test_status_warns_when_a_running_ultra_has_no_cap_and_no_declaration(
    tmp_path: Path,
) -> None:
    _project(tmp_path)
    runner.invoke(app, ["ultra", "start"])
    result = runner.invoke(app, ["ultra", "status"])
    assert "the next pass waits for one" in result.output
    assert "unknown" in result.output


def test_commands_name_a_missing_project(tmp_path: Path) -> None:
    result = runner.invoke(app, ["ultra", "status"])
    assert result.exit_code == 1 and "no projects found" in result.output
    _project(tmp_path)
    result = runner.invoke(app, ["ultra", "stop", str(uuid4())])
    assert result.exit_code == 1 and "unknown project" in result.output


def test_no_cap_is_refused_off_a_terminal_and_nothing_is_recorded(tmp_path: Path) -> None:
    pid = _project(tmp_path)
    toml = tmp_path / "vibey.toml"
    result = runner.invoke(app, ["budget", "no-cap", "--toml", str(toml)])
    assert result.exit_code == 2
    assert "only interactively" in result.output
    assert _ultra_events(pid) == [] and not toml.exists()


def _command(typed: str, confirmed: bool, shown: list[str]) -> UltraCommand:
    return UltraCommand(
        interactive=lambda: True,
        prompt=lambda text: shown.append(text) or typed,  # type: ignore[func-returns-value]
        confirm=lambda text: shown.append(text) or confirmed,  # type: ignore[func-returns-value]
        clear=lambda: shown.append("<clear>"),  # type: ignore[func-returns-value]
    )


def test_the_whole_path_declares_no_cap_and_one_command_withdraws_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pid = _project(tmp_path)
    toml = tmp_path / "vibey.toml"
    toml.write_text("# the operator's\n[features]\ngptossloop = true\n", encoding="utf-8")
    shown: list[str] = []

    asyncio.run(_command(NO_CAP_PHRASE, True, shown).no_cap(None, by=None, toml=toml))

    out = capsys.readouterr().out
    assert shown[0] == "<clear>"
    assert "WARNING: UNLIMITED SPEND" in out and "Measured cost: unknown" in out
    assert "LAST CHANCE" in out and "Declared: no cap" in out
    assert "UNLIMITED SPEND declared" in out
    assert "ultra_no_cap = true" in toml.read_text(encoding="utf-8")
    assert toml.read_text(encoding="utf-8").startswith("# the operator's")
    [declared] = _ultra_events(pid)
    assert declared.payload["enabled"] is True and declared.payload["device"]

    result = runner.invoke(app, ["budget", "cap", "--toml", str(toml)])
    assert result.exit_code == 0, result.output
    assert "withdrawn" in result.output
    assert "ultra_no_cap = false" in toml.read_text(encoding="utf-8")
    assert _ultra_events(pid)[-1].payload["enabled"] is False


def test_a_wrong_phrase_or_the_default_keeps_the_cap(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    pid = _project(tmp_path)
    toml = tmp_path / "vibey.toml"
    with pytest.raises(Exception) as wrong:
        asyncio.run(_command("yes", True, []).no_cap(pid, by=None, toml=toml))
    assert getattr(wrong.value, "exit_code", None) == 1
    asyncio.run(_command(NO_CAP_PHRASE, False, []).no_cap(pid, by=None, toml=toml))
    assert "Kept the cap" in capsys.readouterr().out
    assert _ultra_events(pid) == [] and not toml.exists()


def test_cap_without_a_toml_records_the_withdrawal_only(tmp_path: Path) -> None:
    pid = _project(tmp_path)
    toml = tmp_path / "absent.toml"
    result = runner.invoke(app, ["budget", "cap", str(pid), "--toml", str(toml)])
    assert result.exit_code == 0, result.output
    assert not toml.exists()
    assert _ultra_events(pid)[-1].payload["enabled"] is False


def test_the_measured_rate_is_shown_when_there_is_one() -> None:
    from vibey.application.dto import UltraStatus

    status = UltraStatus(uuid4(), "p", True, False, 3, 10.0, 2.5, 1.25)
    assert UltraCommand.rate(status) == "$1.25/h"


def test_the_store_refuses_other_kinds_and_unknown_projects(tmp_path: Path) -> None:
    from datetime import UTC, datetime

    from vibey.domain.errors import UnknownProject

    async def check() -> None:
        pool = await asyncpg.create_pool(ROLES.app_dsn(_owner()))
        try:
            store = PostgresUltraControlStore(pool)
            with pytest.raises(ValueError, match="not an ULTRA control"):
                await store.record(uuid4(), EventKind.TURN_COMPLETED, {}, at=datetime.now(UTC))
            with pytest.raises(UnknownProject):
                await store.record(uuid4(), EventKind.ULTRA_STARTED, {}, at=datetime.now(UTC))
        finally:
            await pool.close()

    asyncio.run(check())
