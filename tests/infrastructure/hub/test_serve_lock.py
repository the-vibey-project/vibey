# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One hub per user (#1186): the lock a running `vibey serve` holds."""

import fcntl
import os
from pathlib import Path

import pytest

from vibey.infrastructure.hub.interfaces.serve_lock_interface import ServeLockInterface
from vibey.infrastructure.hub.serve_lock import (
    ACP_BOOTSTRAP_LOCK_FILE,
    CONTENTION_PAUSE_SECONDS,
    LOCK_FILE,
    ServeLock,
)


def test_the_lock_meets_its_declared_seam(tmp_path: Path) -> None:
    assert isinstance(ServeLock(tmp_path), ServeLockInterface)


def test_a_second_holder_is_refused_until_the_first_lets_go(tmp_path: Path) -> None:
    first, second = ServeLock(tmp_path / "state"), ServeLock(tmp_path / "state")
    assert first.acquire() is True
    assert second.acquire() is False
    first.release()
    assert second.acquire() is True
    second.release()


def test_the_holder_writes_its_process_id_for_the_message_a_second_hub_prints(
    tmp_path: Path,
) -> None:
    lock = ServeLock(tmp_path)
    assert lock.holder() is None
    assert lock.acquire() is True
    assert lock.holder() == os.getpid()
    assert (tmp_path / LOCK_FILE).stat().st_mode & 0o077 == 0
    lock.release()


def test_a_lock_file_that_names_no_process_has_no_holder(tmp_path: Path) -> None:
    lock = ServeLock(tmp_path)
    (tmp_path / LOCK_FILE).write_text("not a number")
    assert lock.holder() is None
    (tmp_path / LOCK_FILE).write_bytes(b"\xff\xfe")
    assert lock.holder() is None


def test_releasing_without_holding_is_a_no_op(tmp_path: Path) -> None:
    lock = ServeLock(tmp_path)

    assert lock.release() is None
    assert lock.holder() is None
    assert not (tmp_path / LOCK_FILE).exists()


def test_another_job_takes_its_own_lock_beside_the_hubs(tmp_path: Path) -> None:
    hub = ServeLock(tmp_path)
    first = ServeLock(tmp_path, lock_file=ACP_BOOTSTRAP_LOCK_FILE)
    second = ServeLock(tmp_path, lock_file=ACP_BOOTSTRAP_LOCK_FILE)

    assert hub.acquire() is True
    assert first.acquire() is True  # a different file: the hub's lock does not hold it
    assert second.acquire() is False
    first.release()
    assert second.acquire() is True
    assert (tmp_path / ACP_BOOTSTRAP_LOCK_FILE).exists()
    second.release()
    hub.release()


def test_held_by_asks_the_lock_itself(tmp_path: Path) -> None:
    """SP-ACP Task 11a: liveness is the flock, never a pid. A real flock in this process: the
    probe's shared lock on another open file description conflicts with it."""
    state = tmp_path / "state"
    probe = ServeLock(state)
    assert probe.held_by() is None  # never made: no hub has run here
    hub = ServeLock(state)
    assert hub.acquire() is True
    assert probe.held_by() == os.getpid()
    os.truncate(state / LOCK_FILE, 0)  # held, before its holder has written a pid
    assert probe.held_by() == 0
    hub.release()
    assert probe.held_by() is None  # the file is there, nobody holds it
    assert hub.acquire() is True  # the probe never kept a lock of its own
    hub.release()


def test_held_by_never_follows_a_link(tmp_path: Path) -> None:
    state = tmp_path / "state"
    state.mkdir()
    elsewhere = tmp_path / "elsewhere.lock"
    elsewhere.write_text("4242")
    (state / LOCK_FILE).symlink_to(elsewhere)
    assert ServeLock(state).held_by() is None


def test_a_released_lock_leaves_no_process_id_behind(tmp_path: Path) -> None:
    """SP-ACP Task 11b (review 2 N2-1): a hub that exits cleanly empties the file before it lets
    go, so the next holder, in the instant between its flock and its own write, can never be
    read as the hub that left (a stale record naming that pid would otherwise match it)."""
    state = tmp_path / "state"
    hub = ServeLock(state)
    assert hub.acquire() is True
    hub.release()
    assert (state / LOCK_FILE).read_bytes() == b""
    assert hub.holder() is None
    next_hub = ServeLock(state)
    taken = os.open(state / LOCK_FILE, os.O_RDWR)
    try:
        fcntl.flock(taken, fcntl.LOCK_EX | fcntl.LOCK_NB)  # held, nothing written yet
        assert next_hub.held_by() == 0  # "starting", never the departed hub's pid
    finally:
        os.close(taken)


def test_a_probe_in_the_instant_a_hub_starts_never_costs_it_the_lock(tmp_path: Path) -> None:
    """SP-ACP Task 11b (review 2 N2-2): `held_by` holds a shared lock for an instant. A hub whose
    exclusive attempt lands in that instant tries again after a pause instead of concluding
    another hub runs. The probe here is a real shared flock on its own descriptor, let go by the
    pause the lock takes -- no thread, no real sleep."""
    state = tmp_path / "state"
    state.mkdir(mode=0o700)
    probe = os.open(state / LOCK_FILE, os.O_RDWR | os.O_CREAT, 0o600)
    fcntl.flock(probe, fcntl.LOCK_SH | fcntl.LOCK_NB)
    pauses: list[float] = []

    def pause(seconds: float) -> None:
        pauses.append(seconds)
        fcntl.flock(probe, fcntl.LOCK_UN)  # the probe lets go, as it does at once

    hub = ServeLock(state, sleep=pause)
    try:
        assert hub.acquire() is True
        assert pauses == [CONTENTION_PAUSE_SECONDS]
        assert hub.holder() == os.getpid()
    finally:
        hub.release()
        os.close(probe)


def test_a_real_holder_still_refuses_after_the_retries(tmp_path: Path) -> None:
    state = tmp_path / "state"
    pauses: list[float] = []
    first = ServeLock(state)
    second = ServeLock(state, sleep=pauses.append, contention_retries=3, contention_pause=0.5)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
        assert pauses == [0.5, 0.5, 0.5]
    finally:
        first.release()


def test_a_lock_that_is_never_probed_can_refuse_at_once(tmp_path: Path) -> None:
    """The bootstrap lock polls on its own, from an event loop: it takes no pause."""
    state = tmp_path / "state"
    pauses: list[float] = []
    first = ServeLock(state)
    second = ServeLock(state, sleep=pauses.append, contention_retries=0)
    assert first.acquire() is True
    try:
        assert second.acquire() is False
        assert pauses == []
    finally:
        first.release()


def test_a_release_whose_truncate_fails_still_lets_the_lock_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Task 11b review N-4: emptying the pid is best kept, but it must never keep the lock held.
    The module's own `os` is stood in for (never the process's), raising on `ftruncate` only."""
    from vibey.infrastructure.hub import serve_lock as module

    class _Os:
        def __getattr__(self, name: str) -> object:
            return getattr(os, name)

        @staticmethod
        def ftruncate(fd: int, length: int) -> None:
            raise OSError(5, "Input/output error")

    state = tmp_path / "state"
    hub = ServeLock(state)
    assert hub.acquire() is True
    monkeypatch.setattr(module, "os", _Os())
    with pytest.raises(OSError, match="Input/output"):
        hub.release()
    monkeypatch.setattr(module, "os", os)
    assert hub.held_by() is None  # the flock went with the descriptor
    assert hub._fd is None
    next_hub = ServeLock(state)
    assert next_hub.acquire() is True
    next_hub.release()
