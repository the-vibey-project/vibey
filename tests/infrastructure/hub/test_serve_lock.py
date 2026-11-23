# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One hub per user (#1186): the lock a running `vibey serve` holds."""

import os
from pathlib import Path

from vibey.infrastructure.hub.interfaces.serve_lock_interface import ServeLockInterface
from vibey.infrastructure.hub.serve_lock import ACP_BOOTSTRAP_LOCK_FILE, LOCK_FILE, ServeLock


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
