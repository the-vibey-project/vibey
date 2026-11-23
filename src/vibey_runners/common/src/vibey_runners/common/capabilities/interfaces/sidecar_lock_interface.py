# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam over holding a file lock beside a file while it is read, changed and written
(SP-LOOPS Task 7 review)."""

from __future__ import annotations

from contextlib import AbstractContextManager
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class SidecarLockInterface(Protocol):
    def held(self, path: Path) -> AbstractContextManager[None]:
        """Holds an exclusive lock on `.<name>.flock` beside `path` (made 0600, its folder
        0700, never opened through a symlink) for the `with` block. Re-entrant within one
        instance for the same path. Waits at most the instance's timeout for another holder,
        then raises `LockError` naming `path`; `OSError` when the sidecar cannot be made."""
        ...

    def sidecar(self, path: Path) -> Path:
        """The sidecar file `held` locks for `path`."""
        ...
