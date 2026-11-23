# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A bounded, re-entrant file lock beside a file (SP-LOOPS Task 7 review findings 1, 7, 10).

Exclusion is shown without threads or timers: `flock` locks belong to an open file description,
so a second descriptor on the same sidecar, asked with `LOCK_NB`, is refused while the lock is
held and granted once it is released."""

from __future__ import annotations

import fcntl
import os
import stat
from pathlib import Path

import pytest

from vibey_runners.common.capabilities.interfaces.sidecar_lock_interface import (
    SidecarLockInterface,
)
from vibey_runners.common.capabilities.lock_error import LockError
from vibey_runners.common.capabilities.sidecar_lock import SidecarLock


def _free(sidecar: Path) -> bool:
    """Whether a second open file description can take the lock right now."""
    descriptor = os.open(sidecar, os.O_RDWR)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    finally:
        os.close(descriptor)
    return True


def test_the_lock_satisfies_its_interface() -> None:
    assert isinstance(SidecarLock(), SidecarLockInterface)


def test_held_excludes_another_descriptor_and_releases_after(tmp_path: Path) -> None:
    path = tmp_path / "folder" / "lock.json"
    lock = SidecarLock()
    sidecar = lock.sidecar(path)
    assert sidecar == tmp_path / "folder" / ".lock.json.flock"
    with lock.held(path):
        assert not _free(sidecar)
        with lock.held(path):  # re-entrant: no second descriptor waits on the first
            assert not _free(sidecar)
        assert not _free(sidecar)
    assert _free(sidecar)
    assert stat.S_IMODE(sidecar.stat().st_mode) == 0o600
    assert stat.S_IMODE(sidecar.parent.stat().st_mode) == 0o700


def test_an_exception_inside_releases_the_lock(tmp_path: Path) -> None:
    path = tmp_path / "x"
    lock = SidecarLock()
    with pytest.raises(RuntimeError), lock.held(path):
        raise RuntimeError("boom")
    assert _free(lock.sidecar(path))
    with lock.held(path):  # and the instance holds it afresh afterwards
        assert not _free(lock.sidecar(path))


def test_a_held_lock_is_waited_for_then_refused_by_the_clock(tmp_path: Path) -> None:
    path = tmp_path / "x"
    other = SidecarLock()
    now = [0.0]
    slept: list[float] = []

    def sleep(seconds: float) -> None:
        slept.append(seconds)
        now[0] += seconds

    waiting = SidecarLock(clock=lambda: now[0], sleep=sleep, timeout_seconds=0.2, poll_seconds=0.05)
    with other.held(path), pytest.raises(LockError, match="being changed by another vibey"):
        waiting.held(path).__enter__()
    assert slept == [0.05, 0.05, 0.05, 0.05]


def test_a_lock_freed_while_waiting_is_taken(tmp_path: Path) -> None:
    path = tmp_path / "x"
    tries: list[int] = []

    def flock(descriptor: int, operation: int) -> None:
        assert operation == fcntl.LOCK_EX | fcntl.LOCK_NB
        tries.append(descriptor)
        if len(tries) < 3:
            raise BlockingIOError(11, "Resource temporarily unavailable")

    with SidecarLock(flock=flock, sleep=lambda seconds: None).held(path):
        pass
    assert len(tries) == 3


def test_a_sidecar_that_is_a_symlink_is_refused(tmp_path: Path) -> None:
    path = tmp_path / "x"
    target = tmp_path / "elsewhere"
    target.write_text("keep", encoding="utf-8")
    SidecarLock().sidecar(path).symlink_to(target)
    with pytest.raises(OSError):
        SidecarLock().held(path).__enter__()
    assert target.read_text(encoding="utf-8") == "keep"
