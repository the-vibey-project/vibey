# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey worker --local-max-turns`: a bad value is a usage error before anything starts."""

import os

import pytest
from typer.testing import CliRunner

from vibey.cli import main as cli_main
from vibey.infrastructure.engines.local_engines import LOCAL_MAX_TURNS_ENV


def test_a_value_that_is_not_a_number_or_unlimited_exits_with_a_usage_error() -> None:
    result = CliRunner().invoke(cli_main.app, ["worker", "--local-max-turns", "lots"])

    assert result.exit_code == cli_main.EXIT_USAGE
    assert "--local-max-turns: must be a whole number of turns or 'unlimited'" in result.output


def test_a_good_value_is_announced_and_handed_to_the_local_engines(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(LOCAL_MAX_TURNS_ENV, "")  # so the test's own change is undone
    # `--accept-spec-json` without an acceptance is the next usage error after the flag
    # is applied, so this reaches the flag's success path without starting a worker.
    result = CliRunner().invoke(
        cli_main.app, ["worker", "--local-max-turns", " unlimited ", "--accept-spec-json", "s.json"]
    )

    assert result.exit_code == cli_main.EXIT_USAGE
    assert "local engines: turn limit unlimited per session" in result.output
    assert os.environ[LOCAL_MAX_TURNS_ENV] == "unlimited"
