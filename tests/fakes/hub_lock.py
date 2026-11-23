# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A running hub's lock, held by the test process itself: the one shared helper for tests whose
runtime record must name a hub that holds its lock (SP-ACP Task 11b).

Every reader of the record that sends a credential -- `vibey hub pair`, the MCP / ACP gateway --
believes it only while the process the record names holds `<state_dir>/serve.lock`
(`ServeLock.held_by`). A test that writes a record without that lock describes a stale record,
which is now sent nothing. `HubLockHolder.serve` writes the record and takes a real exclusive
`flock` on the lock file, from its own open file description, with the record's pid written in
it as a hub writes its own: the real probe then reports that pid, with no thread, no sleep, no
signal and no other process. Both macOS and Linux scope `flock` to the open file description, so
a probe's own `open()` in this same process conflicts with it.

The `hub_lock` fixture (`tests/conftest.py`) gives one per test and lets every lock go after it.
"""

from __future__ import annotations

import fcntl
import os
from pathlib import Path

from vibey.infrastructure.hub.local_token import LocalTokenStore, ServingRecord
from vibey.infrastructure.hub.serve_lock import LOCK_FILE


class HubLockHolder:
    """Holds hub locks for a test; `close` lets every one go."""

    def __init__(self) -> None:
        self._held: dict[Path, int] = {}

    def serve(self, state_dir: Path, record: ServingRecord) -> ServingRecord:
        """Writes `record` as the hub's runtime record and holds the lock as the hub it names."""
        LocalTokenStore(state_dir).record_serving(record)
        self.hold(state_dir, record.pid)
        return record

    def hold(self, state_dir: Path, pid: int) -> None:
        """Holds `<state_dir>/serve.lock` with `pid` written in it (0 writes nothing: a holder
        that has not written its pid yet). Holding it again only rewrites the pid."""
        fd = self._held.get(state_dir)
        if fd is None:
            state_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(state_dir / LOCK_FILE, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self._held[state_dir] = fd
        os.ftruncate(fd, 0)
        if pid:
            os.pwrite(fd, str(pid).encode(), 0)

    def drop(self, state_dir: Path) -> None:
        """Lets the lock under `state_dir` go, as a hub that died: the record stays, now stale."""
        fd = self._held.pop(state_dir, None)
        if fd is not None:
            os.close(fd)

    def close(self) -> None:
        for state_dir in list(self._held):
            self.drop(state_dir)
