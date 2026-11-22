# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The lock that keeps two `vibey acp` processes (two editor windows) from changing this
computer at once (SP-ACP).

Implemented by `infrastructure/acp/bootstrap_lock.py::BootstrapLock` on
`<state_dir>/acp-bootstrap.lock`, over the hub's own `ServeLock` (ADR-0101: one bootstrap lock per
user). Interfaces declare; they never consume.
"""

from __future__ import annotations

from contextlib import AbstractAsyncContextManager
from typing import Protocol, runtime_checkable


@runtime_checkable
class BootstrapLockInterface(Protocol):
    def acquire(self) -> bool:
        """True when this process now holds the lock; False when another one does. Never waits.
        May raise `OSError` when the lock file cannot be opened."""
        ...

    def release(self) -> None:
        """Let go of the lock; a no-op when this process does not hold it."""
        ...

    def hold(self, timeout: float) -> AbstractAsyncContextManager[bool]:
        """Wait up to `timeout` seconds for the lock without blocking the loop, and hold it for
        the block. Yields True when held, False when another holder kept it past the bound or
        the lock file could not be opened; never raises for either. Each hold has a descriptor
        of its own, so it excludes `acquire` and every other hold, in this process too."""
        ...
