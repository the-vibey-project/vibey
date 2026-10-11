# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The runner `git` and `gh` go through: what it hands them, and what it never does."""

import asyncio
import sys
from pathlib import Path

import pytest

from vibey.infrastructure.publish.command_runner import ProgramRunner


async def test_a_program_runs_and_what_it_printed_comes_back(tmp_path: Path) -> None:
    result = await ProgramRunner().run(
        (sys.executable, "-c", "import os,sys; print(os.getcwd()); print('e', file=sys.stderr)"),
        cwd=tmp_path,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == str(tmp_path.resolve()) and result.stderr.strip() == "e"


async def test_a_failing_program_returns_its_exit_code() -> None:
    result = await ProgramRunner().run((sys.executable, "-c", "raise SystemExit(5)"))

    assert result.returncode == 5


async def test_a_program_that_is_not_installed_is_exit_127_not_an_exception() -> None:
    result = await ProgramRunner().run(("vibey-no-such-program-xyz",))

    assert result.returncode == 127 and "command not found" in result.stderr


async def test_a_program_that_runs_out_of_time_is_stopped_and_reported_as_124() -> None:
    result = await ProgramRunner(timeout=0.3).run(
        (sys.executable, "-c", "import time; time.sleep(30)")
    )

    assert result.returncode == 124 and "timed out after 0.3s" in result.stderr


async def test_cancelling_a_run_stops_the_program() -> None:
    task = asyncio.create_task(
        ProgramRunner().run((sys.executable, "-c", "import time; time.sleep(30)"))
    )
    await asyncio.sleep(0.3)

    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task


async def test_the_program_sees_the_agent_socket_and_no_credential_or_vibey_variable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name, value in {
        "SSH_AUTH_SOCK": "/tmp/agent.sock",
        "GH_TOKEN": "t0ken",
        "GITHUB_TOKEN": "t0ken",
        "VIBEY_PG_URL": "postgresql://secret",
        "PGPASSWORD": "pw",
        "AWS_SECRET_ACCESS_KEY": "k",
    }.items():
        monkeypatch.setenv(name, value)
    code = (
        "import os, json; print(json.dumps({k: os.environ.get(k) for k in "
        "['SSH_AUTH_SOCK','GH_TOKEN','GITHUB_TOKEN','VIBEY_PG_URL','PGPASSWORD',"
        "'AWS_SECRET_ACCESS_KEY','GIT_TERMINAL_PROMPT','GH_PROMPT_DISABLED']}))"
    )

    result = await ProgramRunner().run((sys.executable, "-c", code))

    import json

    seen = json.loads(result.stdout)
    assert seen["SSH_AUTH_SOCK"] == "/tmp/agent.sock"
    assert seen["GIT_TERMINAL_PROMPT"] == "0" and seen["GH_PROMPT_DISABLED"] == "1"
    for name in ("GH_TOKEN", "GITHUB_TOKEN", "VIBEY_PG_URL", "PGPASSWORD", "AWS_SECRET_ACCESS_KEY"):
        assert seen[name] is None, name
