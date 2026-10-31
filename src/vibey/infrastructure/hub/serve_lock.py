# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One hub per user (#1186): the lock a running `vibey serve` holds.

Every krypton UI reaches the hub on this computer, so two hubs would split the paired
devices, the token's meaning and the port. The hub takes an exclusive `flock` on
`<state_dir>/serve.lock` before it opens anything and keeps it until it exits. A lock held
by a process that has died is released by the kernel, so a crash never leaves a stale lock
behind (a stale `serving.json` is a different file and is reported as stale). The holder
writes its process id into the file for the message a second hub prints; the lock itself
is the flock, not the pid.

Declared by `interfaces/serve_lock_interface.py` (ADR-0016).
"""

import fcntl
import os
from pathlib import Path
from typing import Final

LOCK_FILE: Final = "serve.lock"


class ServeLock:
    """The single-instance lock of the hub under `state_dir`."""

    def __init__(self, state_dir: Path) -> None:
        self._path = state_dir / LOCK_FILE
        self._state_dir = state_dir
        self._fd: int | None = None

    def acquire(self) -> bool:
        """True when this process now holds the lock; False when another process does.
        The state directory is made owner-only like the token's, and the file is opened
        without following a symlink."""
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            os.close(fd)
            return False
        os.ftruncate(fd, 0)
        os.write(fd, str(os.getpid()).encode())
        self._fd = fd
        return True

    def holder(self) -> int | None:
        """The process id the current holder wrote, or None when the file is absent or
        holds no number. Read without taking the lock."""
        try:
            text = self._path.read_text().strip()
        except (FileNotFoundError, UnicodeDecodeError):
            return None
        return int(text) if text.isdigit() else None

    def release(self) -> None:
        """Lets go of the lock; a no-op when this process does not hold it."""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
