# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`engines`, `cost` and `ledger show` take `--json` (#1686).

One parseable document on stdout; a refusal goes to stderr with the exit code the text form has.
The text forms are untouched (their own tests are in test_operational_commands.py).
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
import typer
from typer.testing import CliRunner

from tests.cli.test_operational_commands import _seed_cost_project, _seed_engines_project
from vibey.bootstrap import DatabaseNotConfigured, build_app
from vibey.cli import main as cli_main
from vibey.cli.cost import COST_PRESENTER, CostCommand
from vibey.cli.engines import ENGINES_PRESENTER, EnginesCommand
from vibey.cli.interfaces.cost_interface import CostCommandInterface, CostPresenterInterface
from vibey.cli.interfaces.engines_interface import (
    EnginesCommandInterface,
    EnginesPresenterInterface,
)
from vibey.cli.interfaces.project_target_interface import ProjectTargetInterface
from vibey.cli.main import app
from vibey.cli.project_target import ProjectTarget
from vibey.domain.ledger import EventKind

runner = CliRunner(env={"_TYPER_FORCE_DISABLE_TERMINAL": "1"})

ENGINE_KEYS = {
    "engine_id",
    "installed",
    "version",
    "conformance_ok",
    "circuit",
    "capacity_state",
    "consecutive_fail",
    "cost_usd_cycle",
    "selected_count",
}


def test_the_new_classes_honour_their_interfaces() -> None:
    assert isinstance(ENGINES_PRESENTER, EnginesPresenterInterface)
    assert isinstance(EnginesCommand(), EnginesCommandInterface)
    assert isinstance(COST_PRESENTER, CostPresenterInterface)
    assert isinstance(CostCommand(), CostCommandInterface)
    assert isinstance(ProjectTarget(), ProjectTargetInterface)


# ------------------------------------------------------------------------------- engines


def test_engines_json_is_one_document_with_the_documented_keys(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_engines_project(tmp_path))
    result = runner.invoke(app, ["engines", str(project_id), "--json"])
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    document = json.loads(result.stdout)
    assert set(document) == {"project_id", "engines"}
    assert document["project_id"] == str(project_id)
    (engine,) = document["engines"]
    assert set(engine) == ENGINE_KEYS
    assert engine["engine_id"] == "claudeloop" and engine["circuit"] == "closed"
    assert engine["version"] == "1.0.0" and engine["cost_usd_cycle"] == 2.0
    assert engine["selected_count"] == 5 and engine["capacity_state"] is None


def test_engines_json_carries_exactly_what_status_json_carries_under_circuits(
    tmp_path: Path,
) -> None:
    project_id = asyncio.run(_seed_engines_project(tmp_path))
    engines = json.loads(runner.invoke(app, ["engines", str(project_id), "--json"]).stdout)
    status = runner.invoke(app, ["status", str(project_id), "--json"])
    assert status.exit_code == 0, status.output
    assert engines["engines"] == json.loads(status.stdout)["circuits"]


def test_engines_json_without_an_id_uses_the_newest_project(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_engines_project(tmp_path))
    document = json.loads(runner.invoke(app, ["engines", "--json"]).stdout)
    assert document["project_id"] == str(project_id)


def test_a_project_with_no_engines_recorded_is_an_empty_list_not_a_failure(
    tmp_path: Path,
) -> None:
    async def bare() -> str:
        async with build_app() as resources:
            project = await resources.projects.create("bare", tmp_path, max_cycles=3, config={})
            return str(project.project_id)

    project_id = asyncio.run(bare())
    result = runner.invoke(app, ["engines", project_id, "--json"])
    assert result.exit_code == 0
    assert json.loads(result.stdout) == {"project_id": project_id, "engines": []}
    text = runner.invoke(app, ["engines", project_id])
    assert text.exit_code == 0 and "no engines recorded for project" in text.stdout


@asynccontextmanager
async def _no_projects() -> AsyncIterator[SimpleNamespace]:
    """An app whose database holds no project, whatever else this worker's tests left in it."""

    async def none(*_: object) -> None:
        return None

    yield SimpleNamespace(projects=SimpleNamespace(get_latest=none, get=none))


@pytest.mark.parametrize("command", [EnginesCommand, CostCommand])
def test_with_no_project_the_message_stays_on_stdout_in_text_and_moves_to_stderr_in_json(
    command: type, capsys: pytest.CaptureFixture[str]
) -> None:
    with pytest.raises(typer.Exit) as text:
        asyncio.run(command(open_app=_no_projects).run(None, as_json=False))
    out = capsys.readouterr()
    assert text.value.exit_code == 1
    assert "no projects found" in out.out and out.err == ""
    with pytest.raises(typer.Exit) as as_json:
        asyncio.run(command(open_app=_no_projects).run(None, as_json=True))
    out = capsys.readouterr()
    assert as_json.value.exit_code == 1
    assert out.out == "" and "no projects found" in out.err


# --------------------------------------------------------------------------------- cost


def test_cost_json_is_the_budget_document_plus_the_per_engine_spend(tmp_path: Path) -> None:
    project_id = asyncio.run(
        _seed_cost_project(tmp_path, {"max_cycle_dollars": 10.0, "max_cycle_turns": 50})
    )
    result = runner.invoke(app, ["cost", str(project_id), "--json"])
    assert result.exit_code == 0, result.output
    assert result.stderr == ""
    document = json.loads(result.stdout)
    assert set(document) == {
        "project_id",
        "name",
        "cycle",
        "caps",
        "spend",
        "exhausted",
        "engines",
    }
    assert document["project_id"] == str(project_id) and document["name"] == "ops-cost-proj"
    assert document["caps"] == {"max_cycle_dollars": 10.0, "max_cycle_turns": 50}
    assert document["spend"] == {"dollars": 3.25, "turns": 2}
    assert document["exhausted"] is False
    # Named for what it is: BUILD spend across all cycles, not this cycle's.
    assert document["engines"] == [
        {"engine_id": "claudeloop", "cost_usd_all_cycles": 0.0, "selected_count": 4}
    ]


def test_cost_json_agrees_with_budget_show_json_where_they_overlap(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_cost_project(tmp_path, {"max_cycle_dollars": 3.0}))
    cost = json.loads(runner.invoke(app, ["cost", str(project_id), "--json"]).stdout)
    budget = json.loads(runner.invoke(app, ["budget", "show", str(project_id), "--json"]).stdout)
    for key in ("project_id", "name", "cycle", "caps", "spend", "exhausted"):
        assert cost[key] == budget[key], key
    assert cost["exhausted"] is True and "history" not in cost


def test_cost_json_without_an_id_uses_the_newest_project(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_cost_project(tmp_path))
    assert json.loads(runner.invoke(app, ["cost", "--json"]).stdout)["project_id"] == str(
        project_id
    )


def test_cost_for_an_unknown_project_keeps_exit_1_and_moves_to_stderr_under_json() -> None:
    unknown = uuid4()
    text = runner.invoke(app, ["cost", str(unknown)])
    assert text.exit_code == 1 and f"unknown project {unknown}" in text.stdout
    as_json = runner.invoke(app, ["cost", str(unknown), "--json"])
    assert as_json.exit_code == 1
    assert as_json.stdout == "" and f"unknown project {unknown}" in as_json.stderr


# ------------------------------------------------------------------------- ledger show


def test_ledger_show_json_is_every_field_of_every_event(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_cost_project(tmp_path))
    result = runner.invoke(app, ["ledger", "show", str(project_id), "--json"])
    assert result.exit_code == 0, result.output
    document = json.loads(result.stdout)
    assert set(document) == {"project_id", "events"}
    assert document["project_id"] == str(project_id)
    kinds = [event["kind"] for event in document["events"]]
    assert EventKind.TURN_COMPLETED.value in kinds
    assert {"seq", "kind", "phase", "produced_at", "digest", "payload"} <= set(
        document["events"][0]
    )
    seqs = [event["seq"] for event in document["events"]]
    assert seqs == sorted(seqs)
    # --limit and the text form behave as before.
    limited = json.loads(
        runner.invoke(app, ["ledger", "show", str(project_id), "--json", "-n", "1"]).stdout
    )
    assert len(limited["events"]) == 1 and limited["events"][0]["seq"] == seqs[-1]
    assert "#" in runner.invoke(app, ["ledger", "show", str(project_id)]).stdout


def test_ledger_show_json_with_no_project_is_a_stderr_message_and_exit_1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_main, "build_app", _no_projects)
    result = runner.invoke(app, ["ledger", "show", "--json"])
    assert result.exit_code == 1
    assert result.stdout == "" and "no projects found" in result.stderr
    text = runner.invoke(app, ["ledger", "show"])
    assert text.exit_code == 1 and "no projects found" in text.stdout


@pytest.mark.parametrize("command", ["engines", "cost"])
def test_the_help_of_the_new_flags_names_them(command: str) -> None:
    assert "--json" in runner.invoke(app, [command, "--help"]).stdout


# ------------------------------------------------------------------------------ guard()


@pytest.mark.parametrize("command", ["engines", "cost"])
def test_without_a_database_engines_and_cost_say_so_with_a_code_and_exit_3(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VIBEY_PG_URL")
    for args in ([command], [command, "--json"]):
        result = runner.invoke(app, args)
        assert result.exit_code == 3, args
        assert "VIBEY_PG_URL is not set" in result.stderr, args
        assert result.stdout == "", args
        assert "vibey explain E" in result.stderr, args


@pytest.mark.parametrize("command", ["engines", "cost"])
def test_traceback_keeps_the_raw_python_error_reachable(
    command: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("VIBEY_PG_URL")
    result = runner.invoke(app, [command, "--traceback"])
    assert isinstance(result.exception, DatabaseNotConfigured)
    assert result.exit_code == 1 and "vibey explain" not in result.output


def test_traceback_changes_nothing_when_there_is_no_error(tmp_path: Path) -> None:
    project_id = asyncio.run(_seed_engines_project(tmp_path))
    plain = runner.invoke(app, ["engines", str(project_id), "--json"])
    raw = runner.invoke(app, ["engines", str(project_id), "--json", "--traceback"])
    assert raw.exit_code == 0 and raw.stdout == plain.stdout
