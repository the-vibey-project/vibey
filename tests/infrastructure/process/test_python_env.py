# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""OrchestratorPythonEnv: which directories are vibey's own Python environment (#283).

On a system interpreter, sys.prefix is `/usr`. Treating it as a venv stripped
/usr/bin from every engine session. The gate runner already guarded against that
(#212); the engine spawn did not, until both asked this one class."""

import sys

import pytest

from vibey.infrastructure.engines.loop_process_adapter import isolate_python_env
from vibey.infrastructure.process import OrchestratorPythonEnv
from vibey.infrastructure.process.interfaces import OrchestratorPythonEnvInterface

_SYSTEM_PATH = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"


def test_an_interpreter_running_from_a_venv_is_vibeys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "prefix", "/repo/.venv")
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    python_env = OrchestratorPythonEnv({"VIRTUAL_ENV": "/activated/.venv"})

    assert python_env.interpreter_venv() == "/repo/.venv"
    assert python_env.venv_prefixes() == ("/activated/.venv", "/repo/.venv")


def test_a_system_interpreter_is_not_a_venv_and_keeps_the_system_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")

    python_env = OrchestratorPythonEnv({})

    assert python_env.interpreter_venv() is None
    assert python_env.venv_prefixes() == (None, None)
    stripped = isolate_python_env({"PATH": _SYSTEM_PATH}, venv_prefixes=python_env.venv_prefixes())
    assert stripped["PATH"] == _SYSTEM_PATH


def test_without_an_explicit_environment_it_reads_the_live_one_on_every_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    python_env = OrchestratorPythonEnv()
    assert python_env.venv_prefixes() == (None, None)

    monkeypatch.setenv("VIRTUAL_ENV", "/later/.venv")

    assert python_env.venv_prefixes() == ("/later/.venv", None)


def test_it_satisfies_its_interface() -> None:
    assert isinstance(OrchestratorPythonEnv(), OrchestratorPythonEnvInterface)
