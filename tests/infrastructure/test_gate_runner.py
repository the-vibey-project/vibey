# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""SubprocessGateRunner: real subprocesses, and the findings they pin.

greeter4 live finding: a gate command whose binary does not exist is a
FAILING GATE (127, so the repair loop can tell the engine to fix its own
command), never an exception that escapes to become a retried-then-dead vibey
failure.

#212: a gate runs outside vibey's own Python environment, is bounded by a
timeout that fails it as 124 instead of holding the job's lease forever, and
dies with its whole process group -- on timeout and on cancellation alike --
without the reap itself becoming the next unbounded wait."""

import asyncio
import contextlib
import math
import os
import shlex
import signal
import sys
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from vibey.application.interfaces import GateRunner
from vibey.infrastructure.build.gate_runner import SubprocessGateRunner
from vibey.infrastructure.build.interfaces import ConfigurableGateRunnerInterface

# Prints only the variables under test, one per line -- never the whole
# environment, which would put the worker's credentials into a failure diff.
_ENV_PROBE = (
    "/bin/sh",
    "-c",
    'printf "%s\\n" "${VIRTUAL_ENV-unset}" "${VIRTUAL_ENV_PROMPT-unset}" '
    '"${PYTHONHOME-unset}" "${PYTHONPATH-unset}" "${GIT_DIR-unset}" "$PATH"',
)

# Starts `sleep 30` in a session of its own -- outside the gate's process
# group, where no group kill reaches it -- still holding the gate's stdout and
# stderr, records both pids, then either exits or lingers.
_ESCAPE = (
    "import os, subprocess, sys, time\n"
    "child = subprocess.Popen(['sleep', '30'], start_new_session=True)\n"
    "with open(sys.argv[1] + '.tmp', 'w') as handle:\n"
    "    handle.write(f'{child.pid} {os.getpid()}')\n"
    "os.replace(sys.argv[1] + '.tmp', sys.argv[1])\n"
    "if sys.argv[2] == 'linger':\n"
    "    time.sleep(30)\n"
)


def _alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def _read_pids(path: Path) -> list[int]:
    """Written to a temp name and renamed, so a read never sees half a line."""
    for _ in range(1000):
        if path.exists():
            return [int(part) for part in path.read_text().split()]
        await asyncio.sleep(0.01)
    raise AssertionError(f"the gate never wrote {path}")


async def _dead_within(pid: int, *, seconds: float) -> bool:
    """An orphan is reaped by init or launchd, not by us, so give it a moment."""
    for _ in range(int(seconds / 0.01)):
        if not _alive(pid):
            return True
        await asyncio.sleep(0.01)
    return False


async def _release(pid: int) -> None:
    """Kill an escaped child and let the loop see the gate's pipes close."""
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
    await asyncio.sleep(0.1)


def _written_then_renamed(pidfile: Path) -> str:
    quoted, temp = shlex.quote(str(pidfile)), shlex.quote(f"{pidfile}.tmp")
    return f"> {temp}; mv {temp} {quoted}"


async def test_runs_a_real_command_and_captures_output(tmp_path: Path) -> None:
    result = await SubprocessGateRunner().run(("sh", "-c", "echo ok"), cwd=tmp_path)

    assert result.returncode == 0
    assert result.stdout.strip() == "ok"


async def test_a_failing_command_reports_its_exit_code(tmp_path: Path) -> None:
    result = await SubprocessGateRunner().run(("sh", "-c", "echo no >&2; exit 3"), cwd=tmp_path)

    assert result.returncode == 3
    assert "no" in result.stderr


async def test_a_missing_binary_is_a_failing_gate_not_an_exception(tmp_path: Path) -> None:
    result = await SubprocessGateRunner().run(
        ("definitely-not-a-real-binary-xyz", "--version"), cwd=tmp_path
    )

    assert result.returncode == 127
    assert "could not start" in result.stderr


async def test_undecodable_output_is_replaced_not_raised(tmp_path: Path) -> None:
    """A test suite printing one latin-1 byte used to raise UnicodeDecodeError
    out of the runner: an infrastructure failure where a gate result was due."""
    result = await SubprocessGateRunner().run(
        ("/bin/sh", "-c", "printf 'caf\\351'; printf '\\377' >&2"), cwd=tmp_path
    )

    assert result.returncode == 0
    assert result.stdout == "caf�"
    assert result.stderr == "�"


async def test_a_gate_reads_end_of_file_from_stdin(tmp_path: Path) -> None:
    """stdin is /dev/null: a command that prompts gets EOF at once instead of
    waiting on whatever stdin the worker was started with."""
    result = await SubprocessGateRunner(timeout_seconds=10).run(
        ("/bin/sh", "-c", 'read answer; echo "read exited $?"'), cwd=tmp_path
    )

    assert result.stdout.strip() == "read exited 1"


@pytest.fixture
def vibey_python(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> tuple[Path, Path]:
    """The worker's environment as `uv run vibey worker` leaves it: an active
    venv with its bin first on PATH, a running interpreter that is itself a
    venv, and a GIT_* variable leaked in from a hook."""
    venv = tmp_path / "activated-venv"
    interpreter = tmp_path / "interpreter-venv"
    monkeypatch.setenv("VIRTUAL_ENV", str(venv))
    monkeypatch.setenv("VIRTUAL_ENV_PROMPT", "(vibey)")
    monkeypatch.setenv("PYTHONHOME", str(tmp_path / "python-home"))
    monkeypatch.setenv("PYTHONPATH", str(tmp_path / "python-path"))
    monkeypatch.setenv("GIT_DIR", str(tmp_path / "hook-git-dir"))
    monkeypatch.setenv(
        "PATH",
        os.pathsep.join([str(venv / "bin"), str(interpreter / "bin"), "/usr/bin", "/bin"]),
    )
    monkeypatch.setattr(sys, "prefix", str(interpreter))
    monkeypatch.setattr(sys, "base_prefix", str(tmp_path / "base-python"))
    return venv, interpreter


async def test_the_gate_does_not_see_vibeys_python_environment(
    vibey_python: tuple[Path, Path], tmp_path: Path
) -> None:
    """The greeter-campaign leak: with VIRTUAL_ENV set and vibey's venv first on
    PATH, a gate's bare `pip install -e .` landed inside vibey's own venv and
    its bare `python` or `pytest` ran vibey's interpreter."""
    result = await SubprocessGateRunner().run(_ENV_PROBE, cwd=tmp_path)

    virtual_env, prompt, home, path, git_dir, search_path = result.stdout.splitlines()
    assert (virtual_env, prompt, home, path, git_dir) == ("unset",) * 5
    assert search_path.split(os.pathsep) == ["/usr/bin", "/bin"]


async def test_isolation_can_be_turned_off_but_git_variables_never_pass(
    vibey_python: tuple[Path, Path], tmp_path: Path
) -> None:
    venv, interpreter = vibey_python
    runner = SubprocessGateRunner.from_config({"gates": {"isolate_python_env": False}})

    result = await runner.run(_ENV_PROBE, cwd=tmp_path)

    virtual_env, prompt, home, path, git_dir, search_path = result.stdout.splitlines()
    assert virtual_env == str(venv)
    assert prompt == "(vibey)"
    assert home == str(tmp_path / "python-home")
    assert path == str(tmp_path / "python-path")
    assert git_dir == "unset"
    assert search_path.split(os.pathsep)[:2] == [str(venv / "bin"), str(interpreter / "bin")]


async def test_a_system_interpreter_prefix_does_not_strip_the_system_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Outside a venv, sys.prefix is `/usr`; treating it as a venv would strip
    /usr/bin and /usr/local/bin, and with them git, sh and most gate tools."""
    system_path = os.pathsep.join(["/usr/local/bin", "/usr/bin", "/bin"])
    monkeypatch.delenv("VIRTUAL_ENV", raising=False)
    monkeypatch.setattr(sys, "prefix", "/usr")
    monkeypatch.setattr(sys, "base_prefix", "/usr")
    monkeypatch.setenv("PATH", system_path)

    result = await SubprocessGateRunner().run(_ENV_PROBE, cwd=tmp_path)

    assert result.stdout.splitlines()[-1] == system_path


async def test_a_hung_gate_is_killed_and_fails_as_124(tmp_path: Path) -> None:
    """A failing gate for the repair loop -- not an exception, and not a wait
    that holds the job's lease for as long as the command cares to hang."""
    loop = asyncio.get_running_loop()
    started = loop.time()

    result = await SubprocessGateRunner(timeout_seconds=0.2).run(("sleep", "30"), cwd=tmp_path)

    assert loop.time() - started < 10
    assert result.returncode == 124
    assert result.stdout == ""
    assert result.stderr == "gate command timed out after 0.2s and was killed: sleep 30"


async def test_a_timeout_kills_the_gates_whole_process_group(tmp_path: Path) -> None:
    """Killing only the process vibey spawned would leave the background
    `sleep` alive, holding the output pipes open."""
    pidfile = tmp_path / "background.pid"
    script = f"sleep 30 & echo $! {_written_then_renamed(pidfile)}; wait"

    with capture_logs() as logs:
        result = await SubprocessGateRunner(timeout_seconds=1).run(
            ("/bin/sh", "-c", script), cwd=tmp_path
        )

    assert result.returncode == 124
    (background,) = await _read_pids(pidfile)
    assert await _dead_within(background, seconds=5)
    assert not [entry for entry in logs if entry["event"] == "gate_process_not_reaped"]


async def test_cancellation_kills_and_reaps_the_gate_then_reraises(tmp_path: Path) -> None:
    """Ctrl-C on the worker or event-loop shutdown cancels the handler; the
    gate it was running must not outlive it."""
    pidfile = tmp_path / "gate.pid"
    script = f"echo $$ {_written_then_renamed(pidfile)}; exec sleep 30"
    task = asyncio.create_task(SubprocessGateRunner().run(("/bin/sh", "-c", script), cwd=tmp_path))
    (gate,) = await _read_pids(pidfile)

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Reaped, not merely signalled: the runner waited before re-raising.
    assert not _alive(gate)


async def test_cancelling_after_the_gate_exited_does_not_wait_on_its_escaped_child(
    tmp_path: Path,
) -> None:
    """The gate has already exited and its group is empty, so killpg finds no
    one, while a child that left the group keeps the pipes open and
    communicate() never returns. The kill tolerates the empty group, and the
    reap does not wait on the pipes."""
    pidfile = tmp_path / "escape.pids"
    task = asyncio.create_task(
        SubprocessGateRunner().run(
            (sys.executable, "-c", _ESCAPE, str(pidfile), "exit"), cwd=tmp_path
        )
    )
    escaped, gate = await _read_pids(pidfile)
    try:
        assert await _dead_within(gate, seconds=10)

        with capture_logs() as logs:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        assert not [entry for entry in logs if entry["event"] == "gate_process_not_reaped"]
    finally:
        await _release(escaped)


async def test_the_reap_is_bounded_when_an_escaped_child_holds_the_pipes(tmp_path: Path) -> None:
    """Measured on CPython 3.12: after the kill, `process.wait()` does not
    return while a child that escaped the group holds stdout, though the gate
    itself is dead. Waiting on it unbounded would move the hang from the gate
    to the reap, so the runner gives up after the kill grace and says so."""
    pidfile = tmp_path / "escape.pids"
    runner = SubprocessGateRunner(kill_grace_seconds=0.2)
    task = asyncio.create_task(
        runner.run((sys.executable, "-c", _ESCAPE, str(pidfile), "linger"), cwd=tmp_path)
    )
    escaped, gate = await _read_pids(pidfile)
    try:
        with capture_logs() as logs:
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        (warning,) = [entry for entry in logs if entry["event"] == "gate_process_not_reaped"]
        assert warning["pid"] == gate
        assert warning["log_level"] == "warning"
        assert await _dead_within(gate, seconds=5)
    finally:
        await _release(escaped)


def test_the_runner_satisfies_its_declared_interfaces() -> None:
    """ADR-0016: `from_config` is a construction contract declared in
    `infrastructure/build/interfaces/`; `run` is the application's GateRunner
    port."""
    runner = SubprocessGateRunner.from_config({})

    assert isinstance(runner, ConfigurableGateRunnerInterface)
    assert isinstance(runner, GateRunner)


@pytest.mark.parametrize("config", [{}, {"review": {}}, {"gates": {}}])
def test_from_config_without_gates_keys_keeps_the_defaults(config: dict[str, object]) -> None:
    runner = SubprocessGateRunner.from_config(config)

    assert runner._timeout_seconds == 1800.0
    assert runner._kill_grace_seconds == 5.0
    assert runner._isolate_python_env is True


def test_from_config_reads_every_key() -> None:
    runner = SubprocessGateRunner.from_config(
        {"gates": {"timeout_seconds": 90, "kill_grace_seconds": 0.5, "isolate_python_env": False}}
    )

    assert runner._timeout_seconds == 90.0
    assert runner._kill_grace_seconds == 0.5
    assert runner._isolate_python_env is False


async def test_a_configured_timeout_is_the_one_that_fires(tmp_path: Path) -> None:
    runner = SubprocessGateRunner.from_config({"gates": {"timeout_seconds": 0.25}})

    result = await runner.run(("sleep", "30"), cwd=tmp_path)

    assert result.returncode == 124
    assert "timed out after 0.25s" in result.stderr


@pytest.mark.parametrize(
    ("gates", "message"),
    [
        (["timeout_seconds"], "gates project config must be an object"),
        ("fast", "gates project config must be an object"),
        ({"isolate_python_env": "false"}, "gates.isolate_python_env must be a boolean"),
        ({"isolate_python_env": 0}, "gates.isolate_python_env must be a boolean"),
        ({"isolate_python_env": None}, "gates.isolate_python_env must be a boolean"),
        ({"timeout_seconds": "600"}, "gates.timeout_seconds must be a number of seconds"),
        ({"timeout_seconds": True}, "gates.timeout_seconds must be a number of seconds"),
        ({"timeout_seconds": None}, "gates.timeout_seconds must be a number of seconds"),
        ({"timeout_seconds": 0}, "gates.timeout_seconds must be a finite number"),
        ({"timeout_seconds": -5}, "gates.timeout_seconds must be a finite number"),
        ({"timeout_seconds": math.inf}, "gates.timeout_seconds must be a finite number"),
        ({"timeout_seconds": math.nan}, "gates.timeout_seconds must be a finite number"),
        ({"kill_grace_seconds": False}, "gates.kill_grace_seconds must be a number of seconds"),
        ({"kill_grace_seconds": 0.0}, "gates.kill_grace_seconds must be a finite number"),
    ],
)
def test_from_config_rejects_a_malformed_gates_object(gates: object, message: str) -> None:
    """Raised when the worker is built, not discovered later as a gate that
    never times out -- or one that times out every command at once."""
    with pytest.raises(ValueError, match=message):
        SubprocessGateRunner.from_config({"gates": gates})


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"timeout_seconds": 0}, "timeout_seconds must be a finite number"),
        ({"timeout_seconds": -1.0}, "timeout_seconds must be a finite number"),
        ({"timeout_seconds": math.inf}, "timeout_seconds must be a finite number"),
        ({"kill_grace_seconds": 0}, "kill_grace_seconds must be a finite number"),
        ({"kill_grace_seconds": math.nan}, "kill_grace_seconds must be a finite number"),
    ],
)
def test_the_constructor_rejects_a_bound_that_is_not_one(
    kwargs: dict[str, float], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SubprocessGateRunner(**kwargs)


# ── a gate's environment is allow-listed too ──────────────────────────────────────
#
# A gate command is decomposer-produced argv running engine-written code (a test file,
# a build script) in the worktree. It used to inherit the worker's whole environment
# minus GIT_*, so the queue and ledger DSN was one `os.environ` read away from code a
# model wrote.

_SECRET_PROBE = (
    "/bin/sh",
    "-c",
    'printf "%s\\n" "${VIBEY_PG_URL-unset}" "${PGPASSWORD-unset}" "${GH_TOKEN-unset}" '
    '"${AWS_SECRET_ACCESS_KEY-unset}" "${PROJECT_TEST_DSN-unset}" "${HOME-unset}"',
)


def _worker_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VIBEY_PG_URL", "postgresql://vibey:secret@db/vibey")
    monkeypatch.setenv("PGPASSWORD", "secret")
    monkeypatch.setenv("GH_TOKEN", "ghp_secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("PROJECT_TEST_DSN", "postgresql://tests@localhost/tests")
    monkeypatch.setenv("HOME", "/home/worker")


async def test_a_gate_never_sees_the_queue_dsn_or_a_credential(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _worker_secrets(monkeypatch)

    result = await SubprocessGateRunner().run(_SECRET_PROBE, cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert result.stdout.splitlines() == ["unset"] * 5 + ["/home/worker"]


async def test_a_gate_is_given_what_the_project_declares_and_still_not_the_dsn(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _worker_secrets(monkeypatch)
    runner = SubprocessGateRunner.from_config({"gates": {"env_allow": ["PROJECT_TEST_*"]}})

    result = await runner.run(_SECRET_PROBE, cwd=tmp_path)

    assert result.stdout.splitlines() == ["unset"] * 4 + [
        "postgresql://tests@localhost/tests",
        "/home/worker",
    ]


def test_from_config_reads_the_gate_allow_list() -> None:
    runner = SubprocessGateRunner.from_config({"gates": {"env_allow": ["JAVA_HOME", "GRADLE_*"]}})

    assert runner.allow_list.admits("JAVA_HOME")
    assert runner.allow_list.admits("GRADLE_USER_HOME")
    assert runner.allow_list.admits("PATH")
    assert not runner.allow_list.admits("VIBEY_PG_URL")


@pytest.mark.parametrize(
    ("gates", "message"),
    [
        ({"env_allow": "JAVA_HOME"}, "gates.env_allow must be a list of strings"),
        ({"env_allow": ["VIBEY_PG_URL"]}, "gates.env_allow.*can never be passed"),
        ({"env_allow": ["PG*"]}, "can never be passed"),
        ({"env_allow": ["GIT_DIR"]}, "can never be passed"),
    ],
)
def test_from_config_refuses_a_gate_allow_list_that_names_vibeys_own(
    gates: object, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        SubprocessGateRunner.from_config({"gates": gates})
