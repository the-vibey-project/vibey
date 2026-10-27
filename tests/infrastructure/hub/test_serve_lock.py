# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One hub per user (#1186): the lock a running `vibey serve` holds."""

import os
from pathlib import Path

from vibey.infrastructure.hub.interfaces.serve_lock_interface import ServeLockInterface
from vibey.infrastructure.hub.serve_lock import LOCK_FILE, ServeLock


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
    ServeLock(tmp_path).release()
