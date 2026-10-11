# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey worker --autonomous` and `--auto-record-research-gaps`."""

import os

import pytest
from typer.testing import CliRunner

from vibey.cli import main as cli_main
from vibey.infrastructure.config_loader import DESIGN_RESEARCH_ON_UNAVAILABLE_ENV


@pytest.mark.parametrize("flag", ["--autonomous", "--auto-record-research-gaps"])
def test_the_switches_act_on_one_project_so_all_projects_refuses_them(
    flag: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(DESIGN_RESEARCH_ON_UNAVAILABLE_ENV, "")  # undone after the test

    result = CliRunner().invoke(cli_main.app, ["worker", flag, "--all-projects"])

    assert result.exit_code == cli_main.EXIT_USAGE
    assert "use --project, not --all-projects" in result.output


@pytest.mark.parametrize("flag", ["--autonomous", "--auto-record-research-gaps"])
def test_the_switch_makes_research_record_a_gap_for_this_worker(
    flag: str, monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv(DESIGN_RESEARCH_ON_UNAVAILABLE_ENV, "gate")
    # A spec file that is not there is the next usage error after the switch is applied, so
    # this reaches the switch's effect without starting a worker.
    result = CliRunner().invoke(
        cli_main.app,
        ["worker", flag, "--auto-accept-design", "--accept-spec-json", str(tmp_path / "no.json")],
    )

    assert result.exit_code == cli_main.EXIT_USAGE
    assert "recorded as not researched, never a gate" in result.output
    assert os.environ[DESIGN_RESEARCH_ON_UNAVAILABLE_ENV] == "record_gap"  # beats "gate"
