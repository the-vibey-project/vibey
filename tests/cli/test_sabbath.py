# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Sub-doctrine 8.i at the command line (ADR-0070): a write command declines with the
reason and the resume time and exits 75 -- paused, not failed."""

from datetime import UTC, datetime
from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

from vibey.cli.interfaces.sabbath_interface import SabbathCommandInterface
from vibey.cli.main import app
from vibey.cli.sabbath import EXIT_RESTING, SABBATH, SabbathCommand
from vibey.domain.sabbath import RestWindow

REST = RestWindow(
    datetime(2026, 9, 25, 23, 23, tzinfo=UTC),
    datetime(2026, 9, 26, 23, 22, tzinfo=UTC),
    True,
    "computed sundown",
)


class _Gate:
    def __init__(self, held: RestWindow | None, resolved: bool = True) -> None:
        self.held = held
        self.resolved = resolved

    def hold(self) -> RestWindow | None:
        return self.held

    def describe(self) -> list[str]:
        return ["sabbath: enabled", "location: somewhere"]

    def location_resolved(self) -> bool:
        return self.resolved


@pytest.mark.sabbath
def test_the_default_gate_reads_the_working_directory_vibey_toml(tmp_path: Path) -> None:
    (tmp_path / "vibey.toml").write_text(
        f'[sabbath]\nlatitude = 34.97\nlongitude = -82.44\nlanes_dir = "{tmp_path}/l"\n',
        encoding="utf-8",
    )
    command: SabbathCommandInterface = SabbathCommand(root=tmp_path, environ={})
    assert command.gate().location_resolved()
    assert any(line.startswith("location: configured override") for line in command.status())
    assert SabbathCommand().gate() is not None


def test_a_write_command_declines_while_resting_and_proceeds_after() -> None:
    command = SabbathCommand(lambda: _Gate(REST))
    with pytest.raises(typer.Exit) as stopped:
        command.decline_if_resting("new")
    assert stopped.value.exit_code == EXIT_RESTING == 75
    assert SabbathCommand(lambda: _Gate(None)).decline_if_resting("new") is None


def test_doctor_lines_fail_loud_for_an_unplaced_host() -> None:
    lines, ok = SabbathCommand(lambda: _Gate(None, resolved=False)).doctor_lines()
    assert not ok and "FAIL" in lines[-1] and lines[0] == "sabbath  sabbath: enabled"
    assert SabbathCommand(lambda: _Gate(None)).doctor_lines()[1]


@pytest.mark.sabbath
@pytest.mark.parametrize(
    "argv", [["new", "demo"], ["work", "00000000-0000-0000-0000-000000000001"]]
)
def test_new_and_work_say_why_and_when_they_resume(
    monkeypatch: pytest.MonkeyPatch, argv: list[str]
) -> None:
    monkeypatch.setattr(SABBATH, "_factory", lambda: _Gate(REST))
    result = CliRunner().invoke(app, argv)
    assert result.exit_code == 75
    assert "resting for the Sabbath" in result.output
    assert REST.resumes.isoformat() in result.output


def test_vibey_sabbath_prints_the_hosts_window() -> None:
    result = CliRunner().invoke(app, ["sabbath"])
    assert result.exit_code == 0 and "sabbath: enabled" in result.output
