# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One bootstrap lock per user: `<state_dir>/acp-bootstrap.lock` (SP-ACP, ADR-0101).

Every `vibey acp` that changes this computer holds it: the connect and PostgreSQL steps take it
without waiting (`acquire`, Task 7's rule: a second window leaves the step to the first), and
loading or restarting the user-level services waits for it within a bound (`hold`), so two
editor windows that both find the hub down restart it once, the second finding it up when its
turn comes.

It is the hub's own `ServeLock` with another file name (dogfood, ADR-0017): an exclusive
`flock`, released by the kernel when its holder dies, the file opened without following a link.
`hold` polls a non-blocking `flock` on the event loop rather than blocking a thread on it: a
cancelled wait then leaves no thread behind still waiting to take the lock.

Declared by `application/acp/interfaces/bootstrap_lock_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from contextlib import AbstractAsyncContextManager
from pathlib import Path
from typing import Final

from vibey.infrastructure.hub.serve_lock import ACP_BOOTSTRAP_LOCK_FILE, ServeLock

POLL_SECONDS: Final = 0.25
"""How often a waiting `hold` tries the lock again."""


class BootstrapLock:
    """Declared by `BootstrapLockInterface`."""

    def __init__(self, state_dir: Path, *, poll_seconds: float = POLL_SECONDS) -> None:
        self._state_dir = state_dir
        self._path = state_dir / ACP_BOOTSTRAP_LOCK_FILE
        self._poll = poll_seconds
        self._held = ServeLock(state_dir, lock_file=ACP_BOOTSTRAP_LOCK_FILE)

    def acquire(self) -> bool:
        return self._held.acquire()

    def release(self) -> None:
        self._held.release()

    def hold(self, timeout: float) -> AbstractAsyncContextManager[bool]:
        return self._holding(timeout)

    @contextlib.asynccontextmanager
    async def _holding(self, timeout: float) -> AsyncIterator[bool]:
        lock = ServeLock(self._state_dir, lock_file=ACP_BOOTSTRAP_LOCK_FILE)
        held = await self._take(lock, timeout)
        try:
            yield held
        finally:
            if held:
                lock.release()

    async def _take(self, lock: ServeLock, timeout: float) -> bool:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout
        while True:
            try:
                if lock.acquire():
                    return True
            except OSError:
                return False
            left = deadline - loop.time()
            if left <= 0:
                return False
            await asyncio.sleep(min(self._poll, left))
