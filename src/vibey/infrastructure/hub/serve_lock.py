# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One hub per user (#1186): the lock a running `vibey serve` holds.

Every krypton UI reaches the hub on this computer, so two hubs would split the paired
devices, the token's meaning and the port. The hub takes an exclusive `flock` on
`<state_dir>/serve.lock` before it opens anything and keeps it until it exits. A lock held
by a process that has died is released by the kernel, so a crash never leaves a stale lock
behind (a stale `serving.json` is a different file and is reported as stale). The holder
writes its process id into the file for the message a second hub prints; the lock itself
is the flock, not the pid.

Two narrow windows, closed as far as a single file allows (SP-ACP Task 11b):

- **A clean exit leaves no pid behind.** `release` empties the file before it lets go, so the
  next hub, between its `flock` and its own write, reads as "held, no pid yet" (0), never as
  the hub that left. A hub that *crashed* cannot empty it: until the next holder has written,
  its pid stays in the file. Closing that last window needs a pid published apart from the
  lock (a new file renamed into place while already locked), a change of this lock's on-disk
  protocol, so it is left open: it needs a crash, a restart, the dead pid reused and a `vibey
  hub stop` landing in the microseconds between a `flock` and a `write`.
- **A probe never costs a starting hub its lock.** `held_by` holds a shared lock for an
  instant; a hub whose exclusive attempt lands in that instant would conclude another hub runs.
  `acquire` therefore tries again `contention_retries` times, `contention_pause` apart: a real
  holder keeps the lock for its whole life, a probe for microseconds. A lock nobody probes
  (`vibey acp`'s bootstrap lock, polled from an event loop) takes `contention_retries=0`.

Declared by `interfaces/serve_lock_interface.py` (ADR-0016).
"""

import fcntl
import os
import time
from collections.abc import Callable
from pathlib import Path
from typing import Final

LOCK_FILE: Final = "serve.lock"
ACP_BOOTSTRAP_LOCK_FILE: Final = "acp-bootstrap.lock"
"""The same lock, held by a `vibey acp` while it changes this computer (connects clients,
installs PostgreSQL), so a second editor window leaves that to the first (SP-ACP)."""
CONTENTION_RETRIES: Final = 2
"""How many more times `acquire` tries after a refusal, in case a probe held it for an instant."""
CONTENTION_PAUSE_SECONDS: Final = 0.01
"""The pause between those tries: far longer than a probe holds its shared lock."""


class ServeLock:
    """The single-instance lock of the hub under `state_dir`, or of another single-holder job
    named by `lock_file`."""

    def __init__(
        self,
        state_dir: Path,
        *,
        lock_file: str = LOCK_FILE,
        contention_retries: int = CONTENTION_RETRIES,
        contention_pause: float = CONTENTION_PAUSE_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._path = state_dir / lock_file
        self._state_dir = state_dir
        self._fd: int | None = None
        self._retries = contention_retries
        self._pause = contention_pause
        self._sleep = sleep

    def acquire(self) -> bool:
        """True when this process now holds the lock; False when another process does --
        still refused after `contention_retries` more tries, so a probe's instant is never taken
        for a holder. The state directory is made owner-only like the token's, and the file is
        opened without following a symlink."""
        self._state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        fd = os.open(self._path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        tries = self._retries
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if tries <= 0:
                    os.close(fd)
                    return False
                tries -= 1
                self._sleep(self._pause)
        # Held: whatever the file says is the last holder's, until this write replaces it.
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
        """Lets go of the lock, its pid emptied first so no later reader takes the next holder
        for this one; a no-op when this process does not hold it."""
        if self._fd is not None:
            os.ftruncate(self._fd, 0)
            os.close(self._fd)
            self._fd = None
