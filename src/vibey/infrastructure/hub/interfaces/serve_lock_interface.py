# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind the hub's single-instance lock.

Mirrors `vibey/infrastructure/hub/serve_lock.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ServeLockInterface(Protocol):
    """The exclusive lock a running hub holds for as long as it runs."""

    def acquire(self) -> bool:
        """True when this process now holds the lock; False when another one does."""
        ...

    def holder(self) -> int | None:
        """The holder's process id as it wrote it, or None."""
        ...

    def release(self) -> None:
        """Lets go of the lock if this process holds it."""
        ...
