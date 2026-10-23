# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey watch` piped or redirected: one plain snapshot, no screen takeover (#1665).

Piped, it used to emit the alternate-screen, mouse-tracking and colour sequences (colour even
with NO_COLOR set) and never exit, so a script or an agent that ran it hung on a screen it
could not read. These tests hold it to the TUI rule: degrade to plain output when piped.
"""

import os
from pathlib import Path

import asyncpg
import pytest
from typer.testing import CliRunner

from vibey.bootstrap import database_url
from vibey.cli import main as cli_main
from vibey.cli.main import _on_a_terminal as real_on_a_terminal
from vibey.cli.main import app

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
def _no_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_main, "_on_a_terminal", lambda: False)


def test_watch_prints_the_status_snapshot_and_exits_when_not_a_terminal(tmp_path: Path) -> None:
    created = runner.invoke(app, ["new", "widget", "--repo", str(tmp_path), "--ignore-sabbath"])
    assert created.exit_code == 0, created.output

    result = runner.invoke(app, ["watch"])

    assert result.exit_code == 0, result.output
    assert "not a terminal" in result.output
    assert "Project: widget" in result.output
    assert "Queue Depth:" in result.output
    # Nothing a terminal would interpret: no escape sequence at all.
    assert "\x1b" not in result.output


def test_watch_with_no_project_says_what_to_do_when_not_a_terminal() -> None:
    result = runner.invoke(app, ["watch"])

    assert result.exit_code == 1
    assert "no projects found; create one with `vibey new` first" in result.output


def test_replay_needs_a_terminal_and_is_a_usage_error_without_one() -> None:
    result = runner.invoke(app, ["watch", "--replay"])

    assert result.exit_code == cli_main.EXIT_USAGE
    assert "--replay" in result.output
    assert "terminal" in result.output


def test_a_person_is_at_the_terminal_only_when_input_and_output_both_are_one(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Stream:
        def __init__(self, tty: bool) -> None:
            self._tty = tty

        def isatty(self) -> bool:
            return self._tty

    for stdin, stdout, expected in [(True, True, True), (True, False, False), (False, True, False)]:
        monkeypatch.setattr("sys.stdin", Stream(stdin))
        monkeypatch.setattr("sys.stdout", Stream(stdout))
        assert real_on_a_terminal() is expected
