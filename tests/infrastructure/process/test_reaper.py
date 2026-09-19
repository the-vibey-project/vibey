# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ProcessReaper on its own: real processes, and the two findings it exists for (#283).

The kill reaches the whole group the process leads. The reap after it is bounded,
because on CPython 3.12 `process.wait()` does not return while a descendant that
escaped the group still holds the process's pipes, though the process itself is
dead."""

import asyncio
import math
import os
import signal
import sys
from pathlib import Path

import pytest
from structlog.testing import capture_logs

from tests.infrastructure.process.escapes import (
    ESCAPE,
    alive,
    background_script,
    dead_within,
    read_pids,
    release,
)
from vibey.infrastructure.process import DEFAULT_KILL_GRACE_SECONDS, ProcessReaper
from vibey.infrastructure.process.interfaces import ProcessReaperInterface


async def _spawn(*argv: str) -> asyncio.subprocess.Process:
    return await asyncio.create_subprocess_exec(
        *argv,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        start_new_session=True,
    )


async def test_the_kill_reaches_the_whole_group_and_the_reap_completes(tmp_path: Path) -> None:
    """Killing only the spawned `sh` would leave its background `sleep` alive,
    holding the output pipes, and the reap would then wait on it."""
    pidfile = tmp_path / "background.pid"
    process = await _spawn("/bin/sh", "-c", background_script(pidfile))
    (background,) = await read_pids(pidfile)

    with capture_logs() as logs:
        reaped = await ProcessReaper(grace_seconds=5).kill_and_reap(process)

    assert reaped is True
    assert process.returncode == -signal.SIGKILL
    assert await dead_within(background, seconds=5)
    assert logs == []


async def test_an_escaped_child_holding_the_pipes_bounds_the_reap_and_logs_it(
    tmp_path: Path,
) -> None:
    """The escaped `sleep` is outside the group, so no kill of ours reaches it, and
    it keeps the process's stdout open. The reap gives up after the grace and says
    which process it left, with the caller's context, instead of hanging."""
    pidfile = tmp_path / "escape.pids"
    process = await _spawn(sys.executable, "-c", ESCAPE, str(pidfile), "linger")
    escaped, spawned = await read_pids(pidfile)
    reaper = ProcessReaper(
        grace_seconds=0.2,
        event="probe_not_reaped",
        context={"engine": "fakeloop", "pid": "cannot override"},
    )
    loop = asyncio.get_running_loop()
    try:
        started = loop.time()
        with capture_logs() as logs:
            reaped = await reaper.kill_and_reap(process)

        assert reaped is False
        assert loop.time() - started < 5
        (warning,) = logs
        assert warning["event"] == "probe_not_reaped"
        assert warning["log_level"] == "warning"
        assert warning["pid"] == spawned
        assert warning["kill_grace_seconds"] == 0.2
        assert warning["engine"] == "fakeloop"
        # The process itself is dead: only the reap was abandoned.
        assert await dead_within(spawned, seconds=5)
        assert alive(escaped)
    finally:
        await release(escaped)


async def test_a_group_that_is_already_gone_is_not_an_error(tmp_path: Path) -> None:
    """The process exited and was reaped, so its group is empty and killpg fails with
    ESRCH. There is nothing to kill, and the reap returns at once."""
    process = await _spawn("/bin/sh", "-c", "exit 3")
    await process.wait()

    with capture_logs() as logs:
        reaped = await ProcessReaper(grace_seconds=5).kill_and_reap(process)

    assert reaped is True
    assert process.returncode == 3
    assert logs == []


@pytest.mark.parametrize(
    "error",
    [
        ProcessLookupError(3, "No such process"),
        # macOS answers killpg on a group whose only member is an unreaped zombie
        # with EPERM, not ESRCH. There is no portable way to hold a process in that
        # state, so the error is injected.
        PermissionError(1, "Operation not permitted"),
    ],
    ids=["ESRCH", "EPERM"],
)
async def test_esrch_and_eperm_from_the_kill_are_tolerated_and_the_reap_still_runs(
    monkeypatch: pytest.MonkeyPatch, error: OSError
) -> None:
    killed: list[tuple[int, int]] = []

    def refusing_killpg(pgid: int, sig: int) -> None:
        killed.append((pgid, sig))
        raise error

    process = await _spawn("/bin/sh", "-c", "sleep 0.1")
    monkeypatch.setattr(os, "killpg", refusing_killpg)

    reaped = await ProcessReaper(grace_seconds=5).kill_and_reap(process)

    assert killed == [(process.pid, signal.SIGKILL)]
    # The kill was refused, so the process ran to its own end, and was reaped.
    assert reaped is True
    assert process.returncode == 0


@pytest.mark.parametrize("grace", [0, -1.0, math.nan, math.inf])
def test_a_grace_that_is_not_a_bound_is_refused(grace: float) -> None:
    with pytest.raises(ValueError, match="kill grace must be a finite number"):
        ProcessReaper(grace_seconds=grace)


def test_the_not_reaped_event_must_be_named() -> None:
    with pytest.raises(ValueError, match="event name must not be empty"):
        ProcessReaper(event="")


def test_the_reaper_satisfies_its_interface_and_defaults_to_five_seconds() -> None:
    reaper = ProcessReaper()

    assert isinstance(reaper, ProcessReaperInterface)
    assert DEFAULT_KILL_GRACE_SECONDS == 5.0
    assert reaper.grace_seconds == 5.0
    assert ProcessReaper(grace_seconds=2).grace_seconds == 2.0
