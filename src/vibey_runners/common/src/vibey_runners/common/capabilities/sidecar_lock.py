# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An exclusive file lock beside a file, held while it is read, changed and written (SP-LOOPS
Task 7 review findings 1, 7 and 10).

The lock is `flock` on a sidecar file, `.<name>.flock` beside the file it guards (0600, its folder
0700, opened with `O_NOFOLLOW` so a planted symlink is refused). `flock` locks belong to an open
file description, so two processes -- or two descriptors in one process -- exclude each other, and
closing the descriptor releases the lock even when the holder dies. Waiting is bounded: the lock
is tried without blocking, again every `poll_seconds`, until `timeout_seconds` have passed by the
injected clock, and then `LockError` names the file. A holder stopped with Ctrl-Z therefore stalls
no one forever. Holding is re-entrant within one instance for the same path (a counter, not a
second descriptor, which would wait on itself); an instance is meant for one thread. POSIX only
(`fcntl`), like the rest of the family today (Windows is backlog #1097). Declared by
`interfaces/sidecar_lock_interface.py::SidecarLockInterface`.
"""

from __future__ import annotations

import fcntl
import os
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.lock_error import LockError

WAIT_SECONDS: Final = 30.0
"""How long `held` waits for another holder before it gives up."""
POLL_SECONDS: Final = 0.05
_SIDECAR: Final = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW | os.O_CLOEXEC


class SidecarLock:
    """Declared by `interfaces/sidecar_lock_interface.py::SidecarLockInterface`."""

    def __init__(
        self,
        *,
        flock: Callable[[int, int], None] = fcntl.flock,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        timeout_seconds: float = WAIT_SECONDS,
        poll_seconds: float = POLL_SECONDS,
    ) -> None:
        self._flock = flock
        self._clock = clock
        self._sleep = sleep
        self._timeout = timeout_seconds
        self._poll = poll_seconds
        self._held: dict[str, int] = {}

    def sidecar(self, path: Path) -> Path:
        return path.with_name(f".{path.name}.flock")

    @contextmanager
    def held(self, path: Path) -> Iterator[None]:
        key = os.path.abspath(path)
        if key in self._held:
            self._held[key] += 1
            try:
                yield
            finally:
                self._held[key] -= 1
            return
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self.sidecar(path), _SIDECAR, 0o600)
        try:
            self._acquire(descriptor, path)
            self._held[key] = 1
            try:
                yield
            finally:
                del self._held[key]
        finally:
            os.close(descriptor)  # closing the descriptor releases the flock

    def _acquire(self, descriptor: int, path: Path) -> None:
        deadline = self._clock() + self._timeout
        while True:
            try:
                self._flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                return
            except BlockingIOError:
                if self._clock() >= deadline:
                    raise LockError(
                        f"{path} is being changed by another vibey; waited {self._timeout:g} "
                        "seconds for it"
                    ) from None
                self._sleep(self._poll)
