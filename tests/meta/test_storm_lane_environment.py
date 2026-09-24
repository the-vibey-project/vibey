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
import shutil
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

# The storm runs on macOS; the tool refuses any non-POSIX platform outright, and these tests
# build POSIX venvs (`bin/`, shell-script stand-ins) to prove it.
pytestmark = pytest.mark.skipif(os.name != "posix", reason="the storm is POSIX-only")

BIN = "bin"
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


def system_bin(foreign: Path) -> Path:
    """A stand-in for the host's ordinary executables: only `git`, which qwenlane runs.

    Hermetic on purpose. A real /usr/bin differs by host -- Ubuntu's carries a `pip` that
    macOS's does not -- and a test whose verdict depends on which runner it lands on is
    measuring the runner, not the tool.
    """
    where = foreign.parent.parent / "system-bin"
    if not where.is_dir():
        where.mkdir()
        git = shutil.which("git")
        assert git, "git is needed to drive qwenlane"
        (where / "git").symlink_to(git)
    return where


def inherited(foreign: Path, **extra: str) -> dict[str, str]:
    """The environment the storm runner had: the foreign venv activated in front of PATH.

    Built entirely here -- nothing from the host's PATH or VIRTUAL_ENV reaches it.
    """
    return {
        "HOME": os.environ.get("HOME", "/"),
        "PATH": os.pathsep.join([str(foreign / BIN), str(system_bin(foreign))]),
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
    assert entries[1:] == [str(system_bin(foreign))], "ordinary PATH entries must survive"
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
        {"PATH": os.pathsep.join([str(gone / BIN), str(tmp_path)]), "VIRTUAL_ENV": str(gone)}
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


def drive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lane: Path, seen: Path) -> object:
    """Run qwenlane's main() on `lane`, each attempt a child that runs the model's one command.

    An attempt is a process of its own (lane_watchdog), so the command runs where the model's
    would: in that child, through qwenloop's real shell tool, with the environment the child
    inherited from main(). It writes what it saw to `seen`. Nothing calls a model.
    """
    from types import SimpleNamespace

    qwenlane = load_qwenlane()
    attempt = tmp_path / "attempt.py"
    attempt.write_text(
        "import asyncio, json, os, sys\n"
        "from pathlib import Path\n"
        "from qwenloop.infrastructure.tools import SandboxTools\n"
        "spec = json.loads(Path(sys.argv[1]).read_text())\n"
        # Popped, as run_attempt pops them: the commands it starts must not see either.
        f"fd = int(os.environ.pop({qwenlane.REPORT_FD_ENV!r}))\n"
        f"assert os.environ.pop({qwenlane.SPEC_SHA256_ENV!r}), 'the spec digest arrived'\n"
        "result = asyncio.run(\n"
        f"    SandboxTools(Path(spec['lane'])).execute('shell', {{'argv': {PRINT_PREFIX!r}}})\n"
        ")\n"
        f"Path({str(seen)!r}).write_text(str(result.get('output', result)).strip())\n"
        'os.write(fd, b\'result {"status": "failed", "turns": 1}\\n\')\n',
        encoding="utf-8",
    )
    monkeypatch.setattr(
        qwenlane, "attempt_argv", lambda spec: [sys.executable, str(attempt), str(spec)]
    )
    monkeypatch.setattr(qwenlane, "STORM", tmp_path)
    monkeypatch.setattr(
        qwenlane, "_load_config", lambda: SimpleNamespace(max_turns=1, startup_timeout_seconds=1)
    )
    monkeypatch.setattr(qwenlane, "_tracked_repository_context", lambda _lane: "")
    body = lane / "issue.md"
    body.write_text("an issue\n", encoding="utf-8")
    monkeypatch.setattr(
        sys, "argv", ["qwenlane.py", str(lane), "1", "a title", str(body), "--max-attempts", "1"]
    )
    subprocess.run(["git", "init", "-q", str(lane)], check=True)
    return qwenlane


def test_qwenlane_runs_the_models_commands_in_the_lane_venv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, lane: Path, foreign: Path
) -> None:
    seen = tmp_path / "seen.txt"
    qwenlane = drive(monkeypatch, tmp_path, lane, seen)
    with mock.patch.dict(os.environ, inherited(foreign), clear=True):
        qwenlane.main()
    assert Path(seen.read_text(encoding="utf-8")).resolve() == (lane / ".venv").resolve()
    result = json.loads((lane / ".qwenstorm" / "result.json").read_text(encoding="utf-8"))
    assert [attempt["status"] for attempt in result["attempts"]] == ["failed"]


def test_qwenlane_refuses_a_lane_without_its_own_venv_before_the_model_runs(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, foreign: Path
) -> None:
    bare = tmp_path / "lanes" / "no-venv"
    bare.mkdir(parents=True)
    seen = tmp_path / "seen.txt"
    qwenlane = drive(monkeypatch, tmp_path, bare, seen)
    with (
        mock.patch.dict(os.environ, inherited(foreign), clear=True),
        pytest.raises(SystemExit, match="refused"),
    ):
        qwenlane.main()
    assert not seen.exists(), "the model ran in a lane with no environment of its own"
    result = json.loads((bare / ".qwenstorm" / "result.json").read_text(encoding="utf-8"))
    assert result["completed"] is False
    assert "no .venv of its own" in result["environment_refused"]


# --- relative PATH entries, the other tools a lane runs, and the platform -------------------


def executable(where: Path, body: str = "#!/bin/sh\nexit 0\n") -> Path:
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_text(body)
    where.chmod(0o755)
    return where


def resolved_in_lane(lane: Path, env: dict[str, str], name: str) -> str:
    """Where `name` resolves for a command run the way the shell tool runs it: cwd=lane.

    Absolute, read from the lane: dash (Ubuntu's /bin/sh) prints a relative PATH hit as
    written, where macOS's sh prefixes the working directory.
    """
    done = subprocess.run(
        ["/bin/sh", "-c", f"command -v {name} || true"],
        cwd=lane,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    found = done.stdout.strip()
    return str(lane / found) if found else ""


def test_a_relative_path_entry_into_a_foreign_venv_is_dropped(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    """`../../other/.venv/bin` is resolved from the lane, the directory commands run in."""
    other = make_venv(tmp_path / "other" / ".venv")
    pytest_there = executable(other / BIN / "pytest")
    relative = os.path.relpath(other / BIN, lane)
    assert not os.path.isabs(relative) and relative.startswith("..")
    base = inherited(foreign)
    base["PATH"] = os.pathsep.join([relative, base["PATH"]])
    before = resolved_in_lane(lane, base, "pytest")
    assert Path(before).resolve() == pytest_there.resolve(), "the fixture must leak"
    env = LaneEnvironment(lane).build(base)
    assert relative not in env["PATH"].split(os.pathsep)
    assert all(os.path.isabs(e) for e in env["PATH"].split(os.pathsep))
    after = resolved_in_lane(lane, env, "pytest")
    assert not after or LaneEnvironment(lane).inside(Path(after).parent), after


def test_a_relative_path_entry_outside_any_venv_but_outside_the_lane_is_dropped(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    (tmp_path / "loose").mkdir()
    base = inherited(foreign)
    base["PATH"] = os.pathsep.join([os.path.relpath(tmp_path / "loose", lane), base["PATH"]])
    entries = LaneEnvironment(lane).build(base)["PATH"].split(os.pathsep)
    assert str(tmp_path / "loose") not in entries
    assert os.path.relpath(tmp_path / "loose", lane) not in entries


def test_a_relative_path_entry_inside_the_lane_is_kept_absolute(lane: Path, foreign: Path) -> None:
    base = inherited(foreign)
    base["PATH"] = os.pathsep.join(["tools", base["PATH"]])
    entries = LaneEnvironment(lane).build(base)["PATH"].split(os.pathsep)
    assert str(lane / "tools") in entries
    assert "tools" not in entries


def test_relative_interpreter_variables_are_resolved_from_the_lane(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    outside = os.path.relpath(tmp_path / "other" / "lib", lane)
    env = LaneEnvironment(lane).build(
        inherited(foreign, PYTHONPATH=os.pathsep.join([outside, "src"]))
    )
    assert env["PYTHONPATH"] == "src", "the relative entry inside the lane stays"
    env = LaneEnvironment(lane).build(
        inherited(foreign, UV_PROJECT_ENVIRONMENT=os.path.relpath(foreign, lane))
    )
    assert "UV_PROJECT_ENVIRONMENT" not in env
    env = LaneEnvironment(lane).build(inherited(foreign, UV_PROJECT_ENVIRONMENT=".venv"))
    assert env["UV_PROJECT_ENVIRONMENT"] == ".venv"


def test_verify_refuses_a_relative_entry_that_exposes_a_foreign_pytest(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    """python is shadowed by the lane venv; the tool that would still leak is checked too."""
    other = make_venv(tmp_path / "other" / ".venv")
    executable(other / BIN / "pytest")
    env = LaneEnvironment(lane).build(inherited(foreign))
    env["PATH"] = os.pathsep.join([env["PATH"], os.path.relpath(other / BIN, lane)])
    with pytest.raises(ForeignEnvironment, match="`pytest` resolves"):
        LaneEnvironment(lane).verify(env)


def test_verify_refuses_a_pip_in_a_foreign_environment(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    executable(foreign / BIN / "pip")
    env = LaneEnvironment(lane).build(inherited(foreign))
    env["PATH"] = os.pathsep.join([env["PATH"], str(foreign / BIN)])
    with pytest.raises(ForeignEnvironment, match="`pip` resolves"):
        LaneEnvironment(lane).verify(env)


def test_verify_follows_a_console_script_symlinked_out_of_a_foreign_venv(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    """pipx's shape: ~/.local/bin/pytest -> <a venv>/bin/pytest runs in that venv."""
    real = executable(foreign / BIN / "pytest")
    shims = tmp_path / "home" / ".local" / "bin"
    shims.mkdir(parents=True)
    (shims / "pytest").symlink_to(real)
    base = inherited(foreign)
    base["PATH"] = os.pathsep.join([str(shims), base["PATH"]])
    env = LaneEnvironment(lane).build(base)
    with pytest.raises(ForeignEnvironment, match="`pytest` resolves"):
        LaneEnvironment(lane).verify(env)


def test_verify_accepts_tools_in_the_lane_or_at_a_plain_system_location(
    tmp_path: Path, lane: Path, foreign: Path
) -> None:
    """The lane's own pytest, and a uv that is a native binary -- even one a uv-tool venv holds."""
    executable(lane / ".venv" / BIN / "pytest")
    system = tmp_path / "usr-local" / "bin"
    executable(system / "pip3")
    tool_venv = make_venv(tmp_path / "home" / ".local" / "share" / "uv" / "tools" / "uv")
    uv_binary = executable(tool_venv / BIN / "uv")
    shims = tmp_path / "home" / ".local" / "bin"
    shims.mkdir(parents=True)
    (shims / "uv").symlink_to(uv_binary)
    base = inherited(foreign)
    base["PATH"] = os.pathsep.join([str(shims), str(system), base["PATH"]])
    env = LaneEnvironment(lane).build(base)
    assert LaneEnvironment(lane).verify(env) == lane / ".venv" / BIN / "python"


def test_a_non_posix_platform_is_refused_outright(
    monkeypatch: pytest.MonkeyPatch, lane: Path, foreign: Path
) -> None:
    monkeypatch.setattr(LaneEnvironment, "platform", "nt")
    with pytest.raises(ForeignEnvironment, match="POSIX"):
        LaneEnvironment(lane).enter(inherited(foreign))
