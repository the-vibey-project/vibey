# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`BootstrapLock`: one `<state_dir>/acp-bootstrap.lock` per user, waited for within a bound
(ADR-0101). Every holder opens its own descriptor, so two holders in one process exclude each
other as two processes do. Module-level test functions (ADR-0016)."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from pathlib import Path

from vibey.application.acp.interfaces.bootstrap_lock_interface import BootstrapLockInterface
from vibey.infrastructure.acp.bootstrap_lock import BootstrapLock


def test_the_lock_is_its_interface(tmp_path: Path) -> None:
    lock = BootstrapLock(tmp_path)
    assert isinstance(lock, BootstrapLockInterface)
    assert lock._path == tmp_path / "acp-bootstrap.lock"


async def test_a_free_lock_is_held_at_once_and_let_go_after(tmp_path: Path) -> None:
    lock = BootstrapLock(tmp_path / "state")
    async with lock.hold(1.0) as held:
        assert held is True
        assert BootstrapLock(tmp_path / "state").acquire() is False
    other = BootstrapLock(tmp_path / "state")
    assert other.acquire() is True
    other.release()
    assert (tmp_path / "state").stat().st_mode & 0o777 == 0o700


async def test_second_holder_waits_then_times_out_false(tmp_path: Path) -> None:
    first = BootstrapLock(tmp_path, poll_seconds=0.01)
    second = BootstrapLock(tmp_path, poll_seconds=0.01)
    async with first.hold(1.0) as held:
        assert held
        loop = asyncio.get_running_loop()
        started = loop.time()
        async with second.hold(0.1) as waited:
            assert waited is False
        assert loop.time() - started >= 0.1


async def test_second_holder_gets_it_once_the_first_lets_go(tmp_path: Path) -> None:
    order: list[str] = []
    first = BootstrapLock(tmp_path, poll_seconds=0.01)
    second = BootstrapLock(tmp_path, poll_seconds=0.01)

    async def one() -> None:
        async with first.hold(1.0) as held:
            assert held
            order.append("first in")
            await asyncio.sleep(0.1)
            order.append("first out")

    async def two() -> None:
        await asyncio.sleep(0.02)
        async with second.hold(5.0) as held:
            assert held
            order.append("second in")

    await asyncio.gather(one(), two())
    assert order == ["first in", "first out", "second in"]


async def test_one_instance_held_twice_at_once_still_excludes_itself(tmp_path: Path) -> None:
    lock = BootstrapLock(tmp_path, poll_seconds=0.01)
    async with lock.hold(1.0) as outer, lock.hold(0.05) as inner:
        assert (outer, inner) == (True, False)


async def test_another_process_holding_it_is_waited_for(tmp_path: Path) -> None:
    holder = subprocess.Popen(  # noqa: S603 - a fixed argv: this interpreter and a literal
        [
            sys.executable,
            "-c",
            "import fcntl,os,sys,time\n"
            f"fd=os.open({str(tmp_path / 'acp-bootstrap.lock')!r},os.O_RDWR|os.O_CREAT,0o600)\n"
            "fcntl.flock(fd,fcntl.LOCK_EX)\nprint('held',flush=True)\ntime.sleep(30)\n",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None
        assert holder.stdout.readline().strip() == "held"
        async with BootstrapLock(tmp_path, poll_seconds=0.01).hold(0.1) as held:
            assert held is False
        holder.kill()
        holder.wait()
        async with BootstrapLock(tmp_path, poll_seconds=0.01).hold(1.0) as held:
            assert held is True
    finally:
        holder.kill()
        holder.wait()


async def test_a_lock_file_that_cannot_be_opened_is_false_never_raised(tmp_path: Path) -> None:
    (tmp_path / "acp-bootstrap.lock").symlink_to(tmp_path / "elsewhere")
    async with BootstrapLock(tmp_path, poll_seconds=0.01).hold(0.05) as held:
        assert held is False
    assert not (tmp_path / "elsewhere").exists()


async def test_a_cancel_while_holding_lets_the_lock_go(tmp_path: Path) -> None:
    lock = BootstrapLock(tmp_path, poll_seconds=0.01)
    entered = asyncio.Event()

    async def holding() -> None:
        async with lock.hold(1.0):
            entered.set()
            await asyncio.sleep(30)

    task = asyncio.create_task(holding())
    await entered.wait()
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    again = BootstrapLock(tmp_path)
    assert again.acquire() is True
    again.release()


async def test_a_cancel_while_waiting_holds_nothing(tmp_path: Path) -> None:
    first = BootstrapLock(tmp_path, poll_seconds=0.01)
    assert first.acquire()
    task = asyncio.create_task(_wait_in(BootstrapLock(tmp_path, poll_seconds=0.01)))
    await asyncio.sleep(0.05)
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    first.release()
    open_fds = len(os.listdir("/dev/fd"))
    again = BootstrapLock(tmp_path)
    assert again.acquire() is True
    again.release()
    assert len(os.listdir("/dev/fd")) == open_fds


async def _wait_in(lock: BootstrapLock) -> None:
    async with lock.hold(30.0):
        pass


async def test_a_release_while_another_holds_never_drops_that_hold(tmp_path: Path) -> None:
    # `acquire`/`release` (steps 2 and 4) and `hold` (services) never share a descriptor: a
    # release by one never lets go of the lock the other holds.
    lock = BootstrapLock(tmp_path, poll_seconds=0.01)
    async with lock.hold(1.0) as held:
        assert held
        assert lock.acquire() is False
        lock.release()
        assert BootstrapLock(tmp_path).acquire() is False
