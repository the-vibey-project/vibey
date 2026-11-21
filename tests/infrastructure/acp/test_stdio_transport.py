# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`StdioTransport`: stdout carries protocol frames only, whatever else in the process writes.

The guard is proven twice: in a real subprocess against fds 0, 1 and 2 (the only place it can
be proven whole), and in-process on pipes standing in for them, so its branches are measured.
Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import textwrap
import threading
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from vibey.infrastructure.acp.interfaces.stdio_transport_interface import (
    StdioTransportInterface,
)
from vibey.infrastructure.acp.stdio_transport import StdioTransport

REPO = Path(__file__).resolve().parents[3]


class _Fds:
    """The fds a test opens; teardown closes the ones the test did not close itself.

    Closing by number twice is unsafe (the number can be reused in between), so every close
    goes through `close`, which forgets the number."""

    def __init__(self) -> None:
        self.open: set[int] = set()

    def pipe(self) -> tuple[int, int]:
        read_end, write_end = os.pipe()
        self.open |= {read_end, write_end}
        return read_end, write_end

    def add(self, fd: int) -> int:
        self.open.add(fd)
        return fd

    def close(self, *numbers: int) -> None:
        for fd in numbers:
            self.open.discard(fd)
            os.close(fd)


@pytest.fixture
def fds() -> Iterator[_Fds]:
    held = _Fds()
    yield held
    for fd in list(held.open):
        held.close(fd)


def _drain(fd: int) -> bytes:
    chunks = []
    while chunk := os.read(fd, 65536):
        chunks.append(chunk)
    return b"".join(chunks)


def test_the_transport_satisfies_its_interface() -> None:
    assert isinstance(StdioTransport(), StdioTransportInterface)


def test_guard_moves_fd1_to_stderr_and_returns_a_private_stdout() -> None:
    script = textwrap.dedent(
        """
        import os, subprocess, sys
        from vibey.infrastructure.acp.stdio_transport import StdioTransport

        private = StdioTransport().guard()
        print("print-noise")
        sys.stdout.flush()
        os.write(1, b"fd1-noise\\n")
        subprocess.run(["echo", "child-noise"], check=True)
        os.write(private, b"protocol\\n")
        """
    )

    done = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPO,
        capture_output=True,
        check=False,
        timeout=60,
    )

    assert done.returncode == 0, done.stderr.decode()
    assert done.stdout == b"protocol\n"
    for noise in (b"print-noise", b"fd1-noise", b"child-noise"):
        assert noise in done.stderr


def test_guard_in_process_points_the_stdout_fd_at_stderr(
    fds: _Fds, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_read, out_write = fds.pipe()
    err_read, err_write = fds.pipe()
    monkeypatch.setattr(sys, "stdout", sys.stdout)  # restored after the test
    transport = StdioTransport(stdin_fd=0, stdout_fd=out_write, stderr_fd=err_write)

    private = transport.guard()
    fds.add(private)
    os.write(out_write, b"noise")
    os.write(private, b"frame\n")
    inheritable = os.get_inheritable(private)
    fds.close(out_write, err_write, private)

    assert sys.stdout is sys.stderr
    assert private not in (out_write, err_write)
    assert not inheritable
    assert _drain(out_read) == b"frame\n"
    assert _drain(err_read) == b"noise"


async def test_write_line_writes_to_the_private_fd_after_guard(
    fds: _Fds, monkeypatch: pytest.MonkeyPatch
) -> None:
    out_read, out_write = fds.pipe()
    _, err_write = fds.pipe()
    monkeypatch.setattr(sys, "stdout", sys.stdout)
    transport = StdioTransport(stdout_fd=out_write, stderr_fd=err_write)
    private = transport.guard()
    fds.add(private)

    await transport.write_line('{"jsonrpc": "2.0", "method": "x"}\n')
    fds.close(private, out_write)

    assert _drain(out_read) == b'{"jsonrpc": "2.0", "method": "x"}\n'


async def test_write_line_without_guard_writes_to_the_stdout_fd(fds: _Fds) -> None:
    out_read, out_write = fds.pipe()
    transport = StdioTransport(stdout_fd=out_write)

    await transport.write_line("é\n")
    fds.close(out_write)

    assert _drain(out_read) == "é\n".encode()


async def test_a_frame_larger_than_the_pipe_buffer_arrives_whole(fds: _Fds) -> None:
    out_read, out_write = fds.pipe()
    line = "x" * (1 << 20) + "\n"
    received: list[bytes] = []
    reader = threading.Thread(target=lambda: received.append(_drain(out_read)))
    reader.start()

    await StdioTransport(stdout_fd=out_write).write_line(line)
    fds.close(out_write)
    reader.join(30)

    assert received == [line.encode()]


async def test_a_cancelled_write_still_finishes_its_frame_then_raises(fds: _Fds) -> None:
    out_read, out_write = fds.pipe()
    line = "y" * (1 << 20) + "\n"
    write = asyncio.create_task(StdioTransport(stdout_fd=out_write).write_line(line))
    await asyncio.sleep(0.05)  # the writer thread is now blocked on a full pipe

    write.cancel()
    await asyncio.sleep(0)
    write.cancel()  # a second cancel is absorbed the same way
    received = await asyncio.to_thread(os.read, out_read, len(line))
    rest = await asyncio.to_thread(_read_exactly, out_read, len(line) - len(received))

    with pytest.raises(asyncio.CancelledError):
        await write
    assert received + rest == line.encode()


def _read_exactly(fd: int, size: int) -> bytes:
    chunks = []
    while size > 0:
        chunk = os.read(fd, size)
        chunks.append(chunk)
        size -= len(chunk)
    return b"".join(chunks)


async def test_a_failed_write_raises_its_error(fds: _Fds) -> None:
    out_read, out_write = fds.pipe()
    fds.close(out_read)

    with pytest.raises(BrokenPipeError):
        await StdioTransport(stdout_fd=out_write).write_line("x\n")


async def test_reader_reads_lines_from_a_pipe(fds: _Fds) -> None:
    in_read, in_write = fds.pipe()
    os.write(in_write, b'{"a": 1}\n{"b": 2}\n')
    fds.close(in_write)

    reader = await StdioTransport(stdin_fd=in_read).reader(limit=1024)

    assert await reader.readline() == b'{"a": 1}\n'
    assert await reader.readline() == b'{"b": 2}\n'
    assert await reader.readline() == b""
    assert reader.at_eof()


async def test_reader_falls_back_to_a_thread_for_a_regular_file(tmp_path: Path, fds: _Fds) -> None:
    source = tmp_path / "input.jsonl"
    source.write_bytes(b'{"a": 1}\n' * 3)
    fd = fds.add(os.open(source, os.O_RDONLY))

    reader = await StdioTransport(stdin_fd=fd).reader(limit=1024)

    assert await asyncio.wait_for(reader.read(), 10) == b'{"a": 1}\n' * 3
    assert reader.at_eof()


async def test_an_unreadable_stdin_is_an_eof_not_a_hang(tmp_path: Path, fds: _Fds) -> None:
    fd = fds.add(os.open(tmp_path, os.O_RDONLY))  # a directory: fstat works, read fails

    reader = await StdioTransport(stdin_fd=fd).reader(limit=1024)

    assert await asyncio.wait_for(reader.read(), 10) == b""


async def test_a_closed_stdin_is_an_eof_not_a_hang() -> None:
    # Nothing in this process holds fd 10000, so fstat fails and the thread reader, whose
    # first read fails too, ends the stream at once.
    reader = await StdioTransport(stdin_fd=10_000).reader(limit=1024)

    assert await asyncio.wait_for(reader.read(), 10) == b""


async def test_dev_null_stdin_reaches_eof(fds: _Fds) -> None:
    # A character device cannot be polled (kqueue says EINVAL), so it must not go to the
    # event loop, where its EOF would never be seen (review A-2).
    fd = fds.add(os.open(os.devnull, os.O_RDONLY))

    reader = await StdioTransport(stdin_fd=fd).reader(limit=1024)

    assert await asyncio.wait_for(reader.read(), 10) == b""


async def test_a_nonblocking_full_pipe_still_gets_the_whole_frame(fds: _Fds) -> None:
    # A non-blocking stdout fills, `os.write` raises EAGAIN mid-frame; the writer must wait
    # for room and carry on, never leave half a frame (review B-6).
    out_read, out_write = fds.pipe()
    os.set_blocking(out_write, False)
    line = "z" * (1 << 20) + "\n"
    received: list[bytes] = []

    def slow_drain() -> None:
        chunks = []
        while chunk := os.read(out_read, 4096):
            chunks.append(chunk)
            time.sleep(0.0005)
        received.append(b"".join(chunks))

    reader = threading.Thread(target=slow_drain)
    reader.start()
    await StdioTransport(stdout_fd=out_write).write_line(line)
    fds.close(out_write)
    reader.join(60)

    assert received == [line.encode()]
