# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The scrubbed launcher: a local MCP server gets only the variables the person allowed (R7).

No process is started: `execve` and `which` are recording fakes, and the fake `execve` raises
`Execed` in place of replacing the process, as the real one never returns.
"""

from __future__ import annotations

import io
import runpy
import sys
import warnings
from collections.abc import Mapping, Sequence
from typing import NoReturn

import pytest

from vibey_runners.common.capabilities import scrubbed_exec
from vibey_runners.common.capabilities.interfaces.scrubbed_exec_interface import (
    ScrubbedExecInterface,
)
from vibey_runners.common.capabilities.scrubbed_exec import LAUNCHER_MODULE, ScrubbedExec


class Execed(Exception):
    """What the fake `execve` raises where the real one would replace the process."""


class RecordingExec:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], dict[str, str]]] = []

    def __call__(self, path: str, argv: Sequence[str], env: Mapping[str, str]) -> NoReturn:
        self.calls.append((path, list(argv), dict(env)))
        raise Execed


class RecordingWhich:
    def __init__(self, found: dict[str, str]) -> None:
        self.found = found
        self.calls: list[tuple[str, str | None]] = []

    def __call__(self, cmd: str, mode: int = 0, path: str | None = None) -> str | None:
        self.calls.append((cmd, path))
        return self.found.get(cmd)


def _launcher(
    found: dict[str, str] | None = None,
) -> tuple[ScrubbedExec, RecordingExec, RecordingWhich, io.StringIO]:
    execve = RecordingExec()
    which = RecordingWhich({"server": "/opt/bin/server"} if found is None else found)
    err = io.StringIO()
    return ScrubbedExec(execve=execve, which=which, err=err), execve, which, err


def test_values_never_reach_argv_and_only_allowed_names_reach_the_child() -> None:
    launcher, execve, _, err = _launcher()
    environ = {"HOME": "/h", "SENTINEL_URL": "s3ntinel", "ANTHROPIC_API_KEY": "k"}
    with pytest.raises(Execed):
        launcher.run(
            ["--allow", "HOME", "--allow", "SENTINEL_URL", "--", "server", "--port", "1"],
            environ,
        )
    assert isinstance(launcher, ScrubbedExecInterface)
    [(path, argv, env)] = execve.calls
    assert path == "/opt/bin/server"
    assert argv == ["server", "--port", "1"]
    assert env == {"HOME": "/h", "SENTINEL_URL": "s3ntinel"}
    assert all("s3ntinel" not in element for element in [path, *argv])
    assert err.getvalue() == ""


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("ANTHROPIC_API_KEY", "k"),
        ("VIBEY_HUB_TOKEN", "s3cr3t"),
        ("vibey_agent_token", "s3cr3t"),
        ("DB_PASSWORD", "s3cr3t"),
    ],
)
def test_a_secret_named_allow_is_refused_with_78_naming_only_the_variable(
    name: str, value: str
) -> None:
    launcher, execve, which, err = _launcher()
    environ = {"HOME": "/h", name: value}
    assert launcher.run(["--allow", "HOME", "--allow", name, "--", "server"], environ) == 78
    assert execve.calls == []
    assert which.calls == []
    assert name in err.getvalue()
    assert value not in err.getvalue().replace(name, "")
    assert "/h" not in err.getvalue()


def test_an_allowed_name_absent_from_the_environment_is_skipped() -> None:
    launcher, execve, _, _ = _launcher()
    with pytest.raises(Execed):
        launcher.run(["--allow", "HOME", "--allow", "MISSING", "--", "server"], {"HOME": "/h"})
    [(_, _, env)] = execve.calls
    assert env == {"HOME": "/h"}


def test_no_allow_gives_the_child_an_empty_environment() -> None:
    launcher, execve, _, _ = _launcher()
    with pytest.raises(Execed):
        launcher.run(["--", "server"], {"HOME": "/h", "PATH": "/opt/bin"})
    [(_, argv, env)] = execve.calls
    assert argv == ["server"]
    assert env == {}


def test_the_command_is_resolved_with_the_inherited_path_before_scrubbing() -> None:
    launcher, execve, which, _ = _launcher()
    with pytest.raises(Execed):
        launcher.run(["--allow", "HOME", "--", "server"], {"HOME": "/h", "PATH": "/opt/bin"})
    assert which.calls == [("server", "/opt/bin")]
    [(path, _, env)] = execve.calls
    assert path == "/opt/bin/server"
    assert "PATH" not in env


def test_an_inherited_environment_without_path_resolves_with_none() -> None:
    launcher, _, which, _ = _launcher()
    with pytest.raises(Execed):
        launcher.run(["--", "server"], {})
    assert which.calls == [("server", None)]


@pytest.mark.parametrize(
    "argv",
    [
        [],
        ["server"],
        ["--allow", "HOME", "server"],
        ["--allow", "HOME", "--"],
        ["--"],
        ["--allow"],
        ["--env", "HOME", "--", "server"],
    ],
)
def test_a_missing_separator_is_2_and_an_unknown_command_is_127(argv: list[str]) -> None:
    launcher, execve, which, err = _launcher()
    assert launcher.run(argv, {"HOME": "/h"}) == 2
    assert execve.calls == []
    assert which.calls == []
    assert "usage" in err.getvalue()
    assert "/h" not in err.getvalue()

    launcher, execve, which, err = _launcher(found={})
    assert launcher.run(["--allow", "HOME", "--", "nowhere"], {"HOME": "/h", "PATH": "/p"}) == 127
    assert execve.calls == []
    assert which.calls == [("nowhere", "/p")]
    assert "nowhere" in err.getvalue()
    assert "/h" not in err.getvalue()


def test_the_launcher_module_name_is_importable_by_python_dash_m() -> None:
    assert scrubbed_exec.__name__ == LAUNCHER_MODULE


def test_main_runs_the_launcher_on_the_process_argv(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["scrubbed_exec", "--allow", "HOME"])
    with pytest.raises(SystemExit) as caught:
        scrubbed_exec.main()
    assert caught.value.code == 2
    assert "usage" in capsys.readouterr().err


def test_python_dash_m_reaches_main(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["scrubbed_exec"])
    with warnings.catch_warnings(), pytest.raises(SystemExit) as caught:
        warnings.simplefilter("ignore", RuntimeWarning)
        runpy.run_module(LAUNCHER_MODULE, run_name="__main__")
    assert caught.value.code == 2
    assert "usage" in capsys.readouterr().err
