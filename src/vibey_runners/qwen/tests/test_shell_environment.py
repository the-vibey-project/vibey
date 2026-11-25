# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ShellEnvironment: a model-chosen shell command sees what it was allowed, nothing else.

The shell tool used to pass qwenloop's whole environment minus any name containing KEY
or TOKEN, so `VIBEY_PG_URL` -- vibey's queue and ledger DSN -- libpq's `PGPASSWORD` and
any `*_SECRET` reached commands a model chose. It is an allow-list now, consistent with
vibey's own engine environment: the system basics only, and never vibey's or libpq's."""

import sys
from pathlib import Path

import pytest

from qwenloop.infrastructure.interfaces import ShellEnvironmentInterface
from qwenloop.infrastructure.tools import SandboxTools, ShellEnvironment

_WORKER = {
    "PATH": "/usr/bin:/bin",
    "HOME": "/home/worker",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8",
    "TMPDIR": "/tmp",  # nosec B108 - a value, never a path this test opens
    "VIBEY_PG_URL": "postgresql://vibey:secret@db/vibey",
    "VIBEY_SECRETS_TOKEN": "t",
    "PGPASSWORD": "secret",
    "DATABASE_URL": "postgresql://app:secret@db/app",
    "AWS_SECRET_ACCESS_KEY": "aws",
    "GH_TOKEN": "ghp",
    "QWENLOOP_API_KEY": "k",
    "SOMETHING_ELSE": "x",
}


def test_only_the_system_basics_reach_a_shell_command() -> None:
    assert ShellEnvironment(_WORKER).build() == {
        "PATH": "/usr/bin:/bin",
        "HOME": "/home/worker",
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "TMPDIR": "/tmp",  # nosec B108 - a value, never a path this test opens
    }


def test_a_declared_name_passes_but_never_a_forbidden_one() -> None:
    assert ShellEnvironment(_WORKER, extra=("SOMETHING_ELSE",)).build()["SOMETHING_ELSE"] == "x"
    for forbidden in ("VIBEY_PG_URL", "PGPASSWORD", "DATABASE_URL", "GH_TOKEN", "APP_SECRET"):
        with pytest.raises(ValueError, match="can never be passed"):
            ShellEnvironment(_WORKER, extra=(forbidden,))


def test_without_a_source_the_live_environment_is_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://secret")
    monkeypatch.setenv("LANG", "C.UTF-8")

    env = ShellEnvironment().build()

    assert "VIBEY_PG_URL" not in env
    assert env["LANG"] == "C.UTF-8"


async def test_the_shell_tool_runs_with_the_allow_listed_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://secret")
    monkeypatch.setenv("PGPASSWORD", "secret")
    tools = SandboxTools(tmp_path)

    result = await tools.execute(
        "shell",
        {"argv": [sys.executable, "-c", "import os; print(sorted(os.environ))"]},
    )

    assert result["exit_code"] == 0, result
    names = str(result["output"])
    assert "VIBEY_PG_URL" not in names
    assert "PGPASSWORD" not in names
    assert "QWENLOOP_NETWORK" in names  # the marker still lands when the network is off


def test_the_class_satisfies_its_declared_interface() -> None:
    assert isinstance(ShellEnvironment({}), ShellEnvironmentInterface)


def test_exactly_the_two_web_names_of_vibeys_pass_and_every_other_vibey_or_token_name_is_kept_out() -> (
    None
):
    """SP-LOOPS Phase 6: a session's `vibey search` needs the hub's loopback address and the path
    of the session's own token file; neither is a secret (the token stays in its 0600 file).
    Those two names pass; `VIBEY_WEB_STATE`, every other `VIBEY_*` name and every `*TOKEN*` name
    is still stripped, and nothing can declare one of them back in."""
    source = {
        **_WORKER,
        "VIBEY_HUB_URL": "http://127.0.0.1:28100",
        "VIBEY_WEB_TOKEN_FILE": "/runs/r/web-token",
        "VIBEY_WEB_STATE": "none",
        "VIBEY_AGENT_TOKEN": "agent-secret",
        "VIBEY_HUB_TOKEN": "host-secret",
        "WEBSEARCH_PROVIDER": "searxng",
        "WEBSEARCH_COMMAND": "/v/vibey",
    }
    env = ShellEnvironment(source).build()

    assert {name for name in env if name.startswith("VIBEY_")} == {
        "VIBEY_HUB_URL",
        "VIBEY_WEB_TOKEN_FILE",
    }
    assert frozenset({"VIBEY_HUB_URL", "VIBEY_WEB_TOKEN_FILE"}) == ShellEnvironment.WEB_NAMES
    for kept_out in ("VIBEY_PG_URL", "VIBEY_AGENT_TOKEN", "VIBEY_HUB_TOKEN", "VIBEY_WEB_STATE"):
        assert kept_out not in env
    assert not [name for name in env if "TOKEN" in name and name != "VIBEY_WEB_TOKEN_FILE"]
    assert not [name for name in env if name.startswith("WEBSEARCH_")]
    for forbidden in ("VIBEY_PG_URL", "VIBEY_AGENT_TOKEN", "VIBEY_WEB_STATE"):
        with pytest.raises(ValueError, match="can never be passed"):
            ShellEnvironment(source, extra=(forbidden,))
