# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Finding and stopping this user's `vibey worker` processes, and what they started.

A worker that was killed, or whose terminal closed, can leave its jobs leased, and a worker that
is still alive holds its leases by heartbeat: resetting the leases under it would run a job twice.
`vibey recover --stop-workers` therefore stops every worker first, then resets, and refuses to
reset while any survives.

What counts as a worker is a command line: a `vibey` executable (or `python -m vibey...`) with
`worker` after it. It is matched in this user's processes only, never this process or any of its
ancestors, and the plan is shown before anything is signalled. A wrapper such as `caffeinate` or
`uv run` carries the same words, so it is stopped with what it wrapped.
"""

import os
import shlex
import signal
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import PurePath
from typing import Final

DEFAULT_GRACE_SECONDS: Final[float] = 10.0
_POLL_SECONDS: Final[float] = 0.2


@dataclass(frozen=True, slots=True)
class ProcessInfo:
    """One row of the process table."""

    pid: int
    ppid: int
    uid: int
    state: str
    argv: tuple[str, ...]

    @property
    def command(self) -> str:
        return " ".join(self.argv)

    @property
    def alive(self) -> bool:
        """A zombie is already dead and only waits to be reaped by its parent."""
        return not self.state.startswith("Z")


@dataclass(frozen=True, slots=True)
class StopPlan:
    """Every process `stop` would signal: the workers, then what they started."""

    workers: tuple[ProcessInfo, ...]
    descendants: tuple[ProcessInfo, ...]

    @property
    def targets(self) -> tuple[ProcessInfo, ...]:
        return (*self.workers, *self.descendants)


@dataclass(frozen=True, slots=True)
class StopReport:
    """What a stop did: who left on SIGTERM, who needed SIGKILL, and who is still there."""

    terminated: tuple[int, ...]
    killed: tuple[int, ...]
    survivors: tuple[int, ...]


class PsProcessTable:
    """The process table through `ps`, which macOS and Linux both have."""

    def __init__(
        self, *, run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run
    ) -> None:
        self._run = run

    def snapshot(self) -> Sequence[ProcessInfo]:
        result = self._run(
            ["ps", "-axo", "pid=,ppid=,uid=,stat=,command="],  # nosec B603 B607 - fixed argv
            capture_output=True,
            text=True,
            check=False,
        )
        return [row for row in map(_parse_row, result.stdout.splitlines()) if row is not None]


def _parse_row(line: str) -> ProcessInfo | None:
    parts = line.split(None, 4)
    if len(parts) < 5:
        return None
    try:
        pid, ppid, uid = int(parts[0]), int(parts[1]), int(parts[2])
    except ValueError:
        return None
    try:
        argv = tuple(shlex.split(parts[4]))
    except ValueError:
        argv = tuple(parts[4].split())
    return ProcessInfo(pid=pid, ppid=ppid, uid=uid, state=parts[3], argv=argv)


def is_vibey_worker(argv: Sequence[str]) -> bool:
    """A `vibey` command line whose command is `worker`: the executable (or `-m vibey...`) and
    then, somewhere after it, the word `worker` on its own."""
    for index, token in enumerate(argv):
        launches_vibey = PurePath(token).name == "vibey" or (
            index > 0 and argv[index - 1] == "-m" and token.split(".")[0] == "vibey"
        )
        if launches_vibey and "worker" in argv[index + 1 :]:
            return True
    return False


def _ancestors(table: Sequence[ProcessInfo], pid: int) -> set[int]:
    by_pid = {row.pid: row for row in table}
    seen: set[int] = set()
    while pid in by_pid and pid not in seen:
        seen.add(pid)
        pid = by_pid[pid].ppid
    return seen


def _descendants(
    table: Sequence[ProcessInfo], roots: set[int], excluded: set[int]
) -> list[ProcessInfo]:
    found: list[ProcessInfo] = []
    known = set(roots)
    grew = True
    while grew:
        grew = False
        for row in table:
            if row.ppid in known and row.pid not in known and row.pid not in excluded:
                known.add(row.pid)
                found.append(row)
                grew = True
    return found


class WorkerStopper:
    """Declared by `interfaces/worker_processes_interface.py::WorkerStopperInterface`."""

    def __init__(
        self,
        *,
        table: PsProcessTable | None = None,
        kill: Callable[[int, int], None] = os.kill,
        sleep: Callable[[float], None] = time.sleep,
        clock: Callable[[], float] = time.monotonic,
        uid: int | None = None,
        pid: int | None = None,
    ) -> None:
        self._table = table if table is not None else PsProcessTable()
        self._kill = kill
        self._sleep = sleep
        self._clock = clock
        self._uid = os.getuid() if uid is None else uid
        self._pid = os.getpid() if pid is None else pid

    def plan(self) -> StopPlan:
        rows = list(self._table.snapshot())
        protected = _ancestors(rows, self._pid)
        workers = tuple(
            row
            for row in rows
            if row.uid == self._uid
            and row.alive
            and row.pid not in protected
            and is_vibey_worker(row.argv)
        )
        children = tuple(
            row
            for row in _descendants(rows, {w.pid for w in workers}, protected)
            if row.uid == self._uid and row.alive
        )
        return StopPlan(workers=workers, descendants=children)

    def stop(self, plan: StopPlan, *, grace_seconds: float = DEFAULT_GRACE_SECONDS) -> StopReport:
        wanted = [row.pid for row in plan.targets]
        for pid in reversed(wanted):  # what a worker started first, then the worker itself
            self._signal(pid, signal.SIGTERM)
        deadline = self._clock() + max(grace_seconds, 0.0)
        remaining = self._still_running(wanted)
        while remaining and self._clock() < deadline:
            self._sleep(_POLL_SECONDS)
            remaining = self._still_running(wanted)
        terminated = tuple(pid for pid in wanted if pid not in remaining)
        for pid in remaining:
            self._signal(pid, signal.SIGKILL)
        if remaining:
            self._sleep(_POLL_SECONDS)
        survivors = self._still_running(list(remaining))
        killed = tuple(pid for pid in remaining if pid not in survivors)
        return StopReport(terminated=terminated, killed=killed, survivors=tuple(survivors))

    def _still_running(self, pids: Sequence[int]) -> list[int]:
        alive = {row.pid for row in self._table.snapshot() if row.alive}
        return [pid for pid in pids if pid in alive]

    def _signal(self, pid: int, sig: signal.Signals) -> None:
        try:
            self._kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            # Already gone, or not ours to signal: either way the next look at the process
            # table says whether it is still running, and a survivor stops the recovery.
            return
