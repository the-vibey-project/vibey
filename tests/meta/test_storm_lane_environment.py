# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A storm lane's commands run in the lane's own environment, never one inherited from outside.

The measured failure (QwenStorm 3.0.0, 2026-09-23): 25 runs in 16 lanes ran pytest under the
operator's MAIN checkout venv, and one `pip install`ed pytest and hypothesis into it. The
model's own test feedback was measuring a different tree, and a lane mutated an environment
outside its workspace. The chain was `storm-queue.sh` -> `qwenlane.py` -> qwenloop's shell
tool, each handing the next the environment it was started with, which carried the
operator's `VIRTUAL_ENV` and that venv's `bin/` at the front of `PATH`.

These tests build that environment for real -- a foreign venv on `PATH` and in
`VIRTUAL_ENV` -- and assert the lane's command sees its own `.venv` anyway, and that a lane
whose python would resolve elsewhere refuses to start rather than running quietly.

Collected by the repository suite for the same reason `test_storm_check_parser.py` is: a
regression test nothing runs lets the bug come back green.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest import mock

import pytest

TOOL = Path(__file__).resolve().parents[2] / "docs/plans/qwenstorm-3.0.0/tools/lane_environment.py"
_SPEC = importlib.util.spec_from_file_location("lane_environment", TOOL)
assert _SPEC and _SPEC.loader, f"the storm's lane environment is missing: {TOOL}"
lane_environment = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(lane_environment)

LaneEnvironment = lane_environment.LaneEnvironment
ForeignEnvironment = lane_environment.ForeignEnvironment

BIN = "Scripts" if os.name == "nt" else "bin"
PRINT_PREFIX = ["python", "-c", "import sys; print(sys.prefix)"]


def make_venv(where: Path) -> Path:
    """A real, minimal virtual environment -- a `pyvenv.cfg` and a working `python`."""
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(where)],
        check=True,
        capture_output=True,
    )
    return where


@pytest.fixture
def foreign(tmp_path: Path) -> Path:
    """Somebody else's venv: the operator's main checkout, in the incident."""
    return make_venv(tmp_path / "main-checkout" / ".venv-vibey-2.0.0")


@pytest.fixture
def lane(tmp_path: Path) -> Path:
    """A lane workspace with its own `.venv`, as `lane-setup.sh` leaves it."""
    root = tmp_path / "lanes" / "a-lane"
    root.mkdir(parents=True)
    make_venv(root / ".venv")
    return root


def inherited(foreign: Path, **extra: str) -> dict[str, str]:
    """The environment the storm runner had: the foreign venv activated in front of PATH."""
    return {
        "HOME": os.environ.get("HOME", "/"),
        "PATH": os.pathsep.join([str(foreign / BIN), "/usr/bin", "/bin"]),
        "VIRTUAL_ENV": str(foreign),
        "VIRTUAL_ENV_PROMPT": "vibey-2.0.0",
        **extra,
    }


# --- the environment a lane is given --------------------------------------------------------


def test_the_lane_venv_replaces_the_inherited_one(lane: Path, foreign: Path) -> None:
    env = LaneEnvironment(lane).build(inherited(foreign))
    assert env["VIRTUAL_ENV"] == str(lane / ".venv")
    entries = env["PATH"].split(os.pathsep)
    assert entries[0] == str(lane / ".venv" / BIN)
    assert str(foreign / BIN) not in entries, "the foreign venv's bin/ is still on PATH"
    assert entries[1:] == ["/usr/bin", "/bin"], "ordinary PATH entries must survive in order"
    assert "VIRTUAL_ENV_PROMPT" not in env, "it labels the venv VIRTUAL_ENV used to name"


def test_any_python_environment_outside_the_lane_leaves_path(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    """Derived from what the directory IS, not from a list of known offenders (12.h)."""
    other = make_venv(tmp_path / "somewhere" / "else")
    conda = tmp_path / "miniconda" / "envs" / "ml"
    (conda / "conda-meta").mkdir(parents=True)
    (conda / BIN).mkdir()
    base = inherited(foreign)
    base["PATH"] = os.pathsep.join([str(other / BIN), str(conda / BIN), base["PATH"]])
    entries = LaneEnvironment(lane).build(base)["PATH"].split(os.pathsep)
    for outside in (other, conda, foreign):
        assert str(outside / BIN) not in entries


def test_an_activated_venv_leaves_path_even_when_its_directory_is_gone(
    tmp_path: Path, lane: Path
) -> None:
    """A deleted venv cannot be recognised by its files; its activation still names it."""
    gone = tmp_path / "deleted-venv"
    env = LaneEnvironment(lane).build(
        {"PATH": os.pathsep.join([str(gone / BIN), "/usr/bin"]), "VIRTUAL_ENV": str(gone)}
    )
    assert str(gone / BIN) not in env["PATH"].split(os.pathsep)


def test_interpreter_variables_pointing_outside_the_lane_are_removed(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    outside = tmp_path / "outside"
    env = LaneEnvironment(lane).build(
        inherited(
            foreign,
            PYTHONHOME=str(outside),
            PYTHONUSERBASE=str(outside),
            UV_PROJECT_ENVIRONMENT=str(foreign),
            UV_PYTHON=str(foreign / BIN / "python"),
            CONDA_PREFIX=str(outside),
            CONDA_DEFAULT_ENV="base",
            CONDA_SHLVL="1",
        )
    )
    for name in (
        "PYTHONHOME",
        "PYTHONUSERBASE",
        "UV_PROJECT_ENVIRONMENT",
        "UV_PYTHON",
        "CONDA_PREFIX",
        "CONDA_DEFAULT_ENV",
        "CONDA_SHLVL",
    ):
        assert name not in env, f"{name} still reaches the lane"


def test_pythonpath_keeps_only_the_entries_inside_the_lane(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    inside = lane / "src"
    env = LaneEnvironment(lane).build(
        inherited(foreign, PYTHONPATH=os.pathsep.join([str(tmp_path / "x"), str(inside)]))
    )
    assert env["PYTHONPATH"] == str(inside)
    env = LaneEnvironment(lane).build(inherited(foreign, PYTHONPATH=str(tmp_path / "x")))
    assert "PYTHONPATH" not in env


def test_what_does_not_choose_an_interpreter_is_left_alone(lane: Path, foreign: Path) -> None:
    env = LaneEnvironment(lane).build(
        inherited(foreign, UV_PYTHON="3.12", QWENLOOP_CONFIG="/storm/qwen-storm.toml")
    )
    assert env["UV_PYTHON"] == "3.12", "a version request points nowhere"
    assert env["QWENLOOP_CONFIG"] == "/storm/qwen-storm.toml"
    assert env["HOME"] == os.environ.get("HOME", "/")


# --- what a lane's command actually sees ------------------------------------------------------


def test_a_lane_command_runs_its_own_python_despite_a_foreign_venv(
    lane: Path, foreign: Path
) -> None:
    """The incident, end to end: `python` from a lane resolves to the lane's venv."""
    base = inherited(foreign)
    before = subprocess.run(
        PRINT_PREFIX, cwd=lane, env=base, capture_output=True, text=True, check=True
    )
    assert Path(before.stdout.strip()).resolve() == foreign.resolve(), "the fixture must leak"
    after = subprocess.run(
        PRINT_PREFIX,
        cwd=lane,
        env=LaneEnvironment(lane).build(base),
        capture_output=True,
        text=True,
        check=True,
    )
    assert Path(after.stdout.strip()).resolve() == (lane / ".venv").resolve()


def test_qwenloops_shell_tool_sees_the_lane_venv_once_entered(lane: Path, foreign: Path) -> None:
    """The real seam: the shell tool hands every command this process's environment."""
    from qwenloop.infrastructure.tools import SandboxTools

    with mock.patch.dict(os.environ, inherited(foreign), clear=True):
        LaneEnvironment(lane).enter()
        result = asyncio.run(SandboxTools(lane).execute("shell", {"argv": PRINT_PREFIX}))
    assert result["exit_code"] == 0, result
    assert Path(str(result["output"]).strip()).resolve() == (lane / ".venv").resolve()


# --- the guard: a lane whose python resolves elsewhere does not start --------------------------


def test_a_lane_without_its_own_venv_refuses_loudly(tmp_path: Path, foreign: Path) -> None:
    bare = tmp_path / "lanes" / "no-venv"
    bare.mkdir(parents=True)
    with pytest.raises(ForeignEnvironment, match="no .venv of its own"):
        LaneEnvironment(bare).enter(inherited(foreign))


def test_a_path_that_resolves_python_elsewhere_is_refused(lane: Path, foreign: Path) -> None:
    env = LaneEnvironment(lane).build(inherited(foreign))
    env["PATH"] = os.pathsep.join([str(foreign / BIN), env["PATH"]])
    with pytest.raises(ForeignEnvironment, match="resolves outside the lane"):
        LaneEnvironment(lane).verify(env)


@pytest.mark.skipif(os.name == "nt", reason="a POSIX shell script stands in for python")
def test_a_lane_python_that_runs_another_interpreter_is_refused(lane: Path, foreign: Path) -> None:
    """Resolving the name is not enough: the interpreter it runs must be the lane's too."""
    impostor = lane / ".venv" / BIN / "python"
    impostor.unlink()
    impostor.write_text(f'#!/bin/sh\nexec "{foreign / BIN / "python"}" "$@"\n')
    impostor.chmod(0o755)
    with pytest.raises(ForeignEnvironment, match="sys.prefix"):
        LaneEnvironment(lane).enter(inherited(foreign))


def test_entering_replaces_the_given_mapping_wholesale(lane: Path, foreign: Path) -> None:
    environ = inherited(foreign, PYTHONHOME="/elsewhere")
    LaneEnvironment(lane).enter(environ)
    assert environ["VIRTUAL_ENV"] == str(lane / ".venv")
    assert "PYTHONHOME" not in environ


def test_the_class_honours_the_interface_declared_beside_it(lane: Path) -> None:
    declared = TOOL.parent / "interfaces" / "lane_environment_interface.py"
    spec = importlib.util.spec_from_file_location("lane_environment_interface", declared)
    assert spec and spec.loader, f"the declaration is missing: {declared}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert isinstance(LaneEnvironment(lane), module.LaneEnvironmentInterface)


# --- qwenlane: the lane driver enters the lane's environment before the model runs -------------


def load_qwenlane() -> object:
    """`qwenlane.py` by path, with its directory on sys.path as running it would put it."""
    driver = TOOL.parent / "qwenlane.py"
    if str(driver.parent) not in sys.path:
        sys.path.insert(0, str(driver.parent))
    spec = importlib.util.spec_from_file_location("qwenlane", driver)
    assert spec and spec.loader, f"the storm's lane driver is missing: {driver}"
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def drive(monkeypatch: pytest.MonkeyPatch, lane: Path, foreign: Path, seen: list[str]) -> object:
    """Run qwenlane's main() on `lane` from a foreign venv, the model replaced by one command."""
    from types import SimpleNamespace

    from qwenloop.domain.model import RunStatus
    from qwenloop.infrastructure.tools import SandboxTools

    qwenlane = load_qwenlane()

    async def one_command(_server, _profile, cwd, *_args, **_kwargs):
        result = await SandboxTools(cwd).execute("shell", {"argv": PRINT_PREFIX})
        seen.append(str(result.get("output", result)).strip())
        return SimpleNamespace(status=RunStatus.FAILED, turns=1)

    monkeypatch.setattr(qwenlane, "_run_plan", one_command)
    monkeypatch.setattr(
        qwenlane, "_load_config", lambda: SimpleNamespace(max_turns=1, startup_timeout_seconds=1)
    )
    monkeypatch.setattr(qwenlane, "_server_for", lambda _config: (None, None))
    monkeypatch.setattr(qwenlane, "_tracked_repository_context", lambda _lane: "")
    body = lane / "issue.md"
    body.write_text("an issue\n", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["qwenlane.py", str(lane), "1", "a title", str(body), "--max-attempts", "1"]
    )
    subprocess.run(["git", "init", "-q", str(lane)], check=True)
    return qwenlane


def test_qwenlane_runs_the_models_commands_in_the_lane_venv(
    monkeypatch: pytest.MonkeyPatch, lane: Path, foreign: Path
) -> None:
    seen: list[str] = []
    qwenlane = drive(monkeypatch, lane, foreign, seen)
    with mock.patch.dict(os.environ, inherited(foreign), clear=True):
        qwenlane.main()
    assert len(seen) == 1, seen
    assert Path(seen[0]).resolve() == (lane / ".venv").resolve()


def test_qwenlane_refuses_a_lane_without_its_own_venv_before_the_model_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, foreign: Path
) -> None:
    bare = tmp_path / "lanes" / "no-venv"
    bare.mkdir(parents=True)
    seen: list[str] = []
    qwenlane = drive(monkeypatch, bare, foreign, seen)
    with (
        mock.patch.dict(os.environ, inherited(foreign), clear=True),
        pytest.raises(SystemExit, match="refused"),
    ):
        qwenlane.main()
    assert seen == [], "the model ran in a lane with no environment of its own"
    result = json.loads((bare / ".qwenstorm" / "result.json").read_text(encoding="utf-8"))
    assert result["completed"] is False
    assert "no .venv of its own" in result["environment_refused"]
