# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Real processes that misbehave the ways #283 is about, for the reaper and its call sites.

The same shapes as `tests/infrastructure/test_gate_runner.py`, which keeps its own
copy so #212's tests stay exactly as they were written.
"""

import asyncio
import contextlib
import os
import shlex
import signal
from pathlib import Path

ESCAPE = (
    "import os, subprocess, sys, time\n"
    "child = subprocess.Popen(['sleep', '30'], start_new_session=True)\n"
    "with open(sys.argv[1] + '.tmp', 'w') as handle:\n"
    "    handle.write(f'{child.pid} {os.getpid()}')\n"
    "os.replace(sys.argv[1] + '.tmp', sys.argv[1])\n"
    "if sys.argv[2] == 'linger':\n"
    "    time.sleep(30)\n"
)
"""Starts `sleep 30` in a session of its own, outside the caller's process group where
no group kill reaches it, still holding the caller's stdout and stderr. Records both
pids (`<escaped> <caller>`), then either exits or lingers."""


def background_script(pidfile: Path) -> str:
    """`sh -c` text that starts `sleep 30` in the background, inside its own process
    group, records its pid, then waits on it. Only a group kill reaches the sleep."""
    quoted, temp = shlex.quote(str(pidfile)), shlex.quote(f"{pidfile}.tmp")
    return f"sleep 30 & echo $! > {temp}; mv {temp} {quoted}; wait"


def alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True


async def read_pids(path: Path) -> list[int]:
    """Written to a temp name and renamed, so a read never sees half a line."""
    for _ in range(1000):
        if path.exists():
            return [int(part) for part in path.read_text().split()]
        await asyncio.sleep(0.01)
    raise AssertionError(f"the process never wrote {path}")


async def dead_within(pid: int, *, seconds: float) -> bool:
    """An orphan is reaped by init or launchd, not by us, so give it a moment."""
    for _ in range(int(seconds / 0.01)):
        if not alive(pid):
            return True
        await asyncio.sleep(0.01)
    return False


async def release(pid: int) -> None:
    """Kill an escaped child and let the loop see the caller's pipes close."""
    with contextlib.suppress(ProcessLookupError):
        os.kill(pid, signal.SIGKILL)
    await asyncio.sleep(0.1)
