# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Kill a spawned process's whole group, then reap it within a bound (#283).

This is the one implementation (ADR-0017) of the kill path that #212 built for gate
commands. It is used everywhere vibey kills a child it spawned: the gate runner,
the loop-process adapter's preflight probes, and the skills-context compiler.

Two things about killing a child are easy to get wrong.

**The kill has to reach the whole group.** A command runs through `sh -c`, or starts
a test server or a background `sleep`. Killing only the process vibey spawned leaves
those descendants alive, still holding its output pipes. So every call site spawns
with `start_new_session=True`, which makes the child lead a group of its own, and
the kill is `os.killpg(pid, SIGKILL)`.

**The reap has to be bounded.** On CPython 3.12, a `process.wait()` that starts
before the process exits resolves only once every pipe has closed too. Some
descendant may have escaped into a session of its own (a daemon, or anything that
calls `setsid`) and kept the child's stdout. Then `wait()` blocks for as long as that
descendant lives, though the child itself died milliseconds after SIGKILL. The #212
lane measured this on 3.12.13. An unbounded wait there just moves the hang from the
command to the reap. So the wait gets a grace period, and when it runs out the
reaper logs one structured warning and returns.
"""

import asyncio
import contextlib
import math
import os
import signal
from collections.abc import Mapping

import structlog

logger = structlog.get_logger(__name__)

DEFAULT_KILL_GRACE_SECONDS = 5.0
"""How long to wait for a killed process to be reaped before giving up on it.
SIGKILL cannot be caught, so the process itself is gone in milliseconds. The grace
only runs out when something outside its process group still holds its output
pipes. Every call site can override it: `gates.kill_grace_seconds`,
`skills_context.kill_grace_seconds`, `LoopProcessAdapter.kill_grace_seconds`."""


class ProcessReaper:
    """SIGKILLs the process group a spawned process leads, and reaps it within a bound.

    Declared by `interfaces/reaper_interface.py`. `event` names the structured
    warning logged when the reap gives up, so an operator can tell which call site
    left a process behind. `context` adds fixed fields to that line, such as the
    engine a probe belonged to. It cannot override `pid`, `returncode` or
    `kill_grace_seconds`.
    """

    def __init__(
        self,
        *,
        grace_seconds: float = DEFAULT_KILL_GRACE_SECONDS,
        event: str = "process_not_reaped",
        context: Mapping[str, object] | None = None,
    ) -> None:
        # Zero, a negative, NaN or infinity is not a bound. Zero or less gives up
        # before the kill has landed, and NaN or infinity never gives up at all.
        if not math.isfinite(grace_seconds) or grace_seconds <= 0:
            raise ValueError("kill grace must be a finite number of seconds greater than zero")
        if not event:
            raise ValueError("the not-reaped event name must not be empty")
        self._grace_seconds = float(grace_seconds)
        self._event = event
        self._context = dict(context or {})

    @property
    def grace_seconds(self) -> float:
        return self._grace_seconds

    async def kill_and_reap(self, process: asyncio.subprocess.Process) -> bool:
        # ProcessLookupError (ESRCH): nothing is left in the group. The process
        # exited on its own, and anything still holding its pipes left the group
        # first. PermissionError (EPERM): macOS refuses killpg on a group whose only
        # member is a zombie, which the process is between exiting and being reaped.
        # Either way there is nothing left to kill, and the reap below still runs.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            os.killpg(process.pid, signal.SIGKILL)
        try:
            await asyncio.wait_for(process.wait(), timeout=self._grace_seconds)
        except TimeoutError:
            # The event loop's child watcher still reaps the process itself. The
            # escaped descendant is outside any group vibey started, so vibey cannot
            # kill it and does not wait on it either.
            fields = {
                **self._context,
                "pid": process.pid,
                "returncode": process.returncode,
                "kill_grace_seconds": self._grace_seconds,
            }
            logger.warning(self._event, **fields)
            return False
        return True
