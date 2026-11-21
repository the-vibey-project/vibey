# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The lock that keeps two `vibey acp` processes (two editor windows) from changing this
computer at once (SP-ACP).

Implemented by `infrastructure/hub/serve_lock.py::ServeLock` on `<state_dir>/acp-bootstrap.lock`.
Interfaces declare; they never consume.
"""

from __future__ import annotations

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
