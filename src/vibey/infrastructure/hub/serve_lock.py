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
ACP_BOOTSTRAP_LOCK_FILE: Final = "acp-bootstrap.lock"
"""The same lock, held by a `vibey acp` while it changes this computer (connects clients,
installs PostgreSQL), so a second editor window leaves that to the first (SP-ACP)."""


class ServeLock:
    """The single-instance lock of the hub under `state_dir`, or of another single-holder job
    named by `lock_file`."""

    def __init__(self, state_dir: Path, *, lock_file: str = LOCK_FILE) -> None:
        self._path = state_dir / lock_file
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

    def held_by(self) -> int | None:
        """Whether a process holds the lock now, asked of the lock itself (never of a pid that
        may have been reused): None when no process holds it (or it was never made), else the
        process id the holder wrote -- 0 when it has not written one yet.

        The probe takes a shared, non-blocking flock on its own open file description, which
        fails only while an exclusive holder has it; it never writes, and it is let go at once.
        The one implementation `vibey hub` and `vibey acp`'s service units share (SP-ACP 11a)."""
        try:
            fd = os.open(self._path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return None  # no lock file: no hub has ever run here
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_SH | fcntl.LOCK_NB)
            except BlockingIOError:
                text = os.read(fd, 32).decode("ascii", errors="replace").strip()
                return int(text) if text.isdigit() else 0
            fcntl.flock(fd, fcntl.LOCK_UN)
            return None
        finally:
            os.close(fd)

    def release(self) -> None:
        """Lets go of the lock; a no-op when this process does not hold it."""
        if self._fd is not None:
            os.close(self._fd)
            self._fd = None
