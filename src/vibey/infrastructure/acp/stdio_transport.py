# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey acp`'s stdio: stdout carries ACP frames and nothing else (SP-ACP, review focus 1).

The ACP transport says the agent must not write anything to stdout that is not a valid ACP
message. vibey reuses code that prints (doctor checks, `typer.echo`) and starts children that
inherit fd 1, so policing writers cannot hold that line. `guard` moves the line instead: it
keeps a private duplicate of the real stdout for protocol frames, then points fd 1 itself at
stderr, so a stray `print`, a `typer.echo` and an inheriting child all land on stderr.

Frames are written with `os.write` in a worker thread until every byte is out. A frame whose
write is cancelled is still written whole before the cancel propagates: half a line would
corrupt the stream, and the peer's write lock is released as soon as the cancel is raised.
Declared by `interfaces/stdio_transport_interface.py`.
"""

from __future__ import annotations

import asyncio
import os
import stat
import sys
import threading
from typing import Final

READ_CHUNK_BYTES: Final = 65_536
"""How much the thread reader asks for at a time when stdin is not a pipe."""


class StdioTransport:
    """Declared by `interfaces/stdio_transport_interface.py::StdioTransportInterface`."""

    def __init__(self, *, stdin_fd: int = 0, stdout_fd: int = 1, stderr_fd: int = 2) -> None:
        self._stdin_fd = stdin_fd
        self._stdout_fd = stdout_fd
        self._stderr_fd = stderr_fd
        self._private_fd: int | None = None

    def guard(self) -> int:
        private = os.dup(self._stdout_fd)  # not inheritable: a child never sees the protocol
        os.dup2(self._stderr_fd, self._stdout_fd)
        sys.stdout = sys.stderr
        self._private_fd = private
        return private

    async def reader(self, limit: int) -> asyncio.StreamReader:
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader(limit=limit, loop=loop)
        if self._is_stream():
            pipe = os.fdopen(self._stdin_fd, "rb", buffering=0, closefd=False)
            await loop.connect_read_pipe(lambda: asyncio.StreamReaderProtocol(reader), pipe)
        else:
            # A regular file (or anything else the loop cannot watch): read it in a daemon
            # thread, so a read that never returns cannot hold the interpreter open at exit.
            threading.Thread(
                target=self._pump, args=(loop, reader), name="vibey-acp-stdin", daemon=True
            ).start()
        return reader

    async def write_line(self, line: str) -> None:
        pending = asyncio.ensure_future(self._write_all(line.encode("utf-8")))
        interrupted = False
        while not pending.done():
            try:
                await asyncio.shield(pending)
            except asyncio.CancelledError:
                interrupted = True
        if interrupted:
            raise asyncio.CancelledError
        pending.result()

    async def _write_all(self, data: bytes) -> None:
        fd = self._private_fd if self._private_fd is not None else self._stdout_fd
        view = memoryview(data)
        while view:
            written = await asyncio.to_thread(os.write, fd, view)
            view = view[written:]

    def _is_stream(self) -> bool:
        """Whether stdin is something the event loop can watch: a pipe, a socket or a tty."""
        try:
            mode = os.fstat(self._stdin_fd).st_mode
        except OSError:
            return False
        return stat.S_ISFIFO(mode) or stat.S_ISSOCK(mode) or stat.S_ISCHR(mode)

    def _pump(self, loop: asyncio.AbstractEventLoop, reader: asyncio.StreamReader) -> None:
        while True:
            try:
                chunk = os.read(self._stdin_fd, READ_CHUNK_BYTES)
            except OSError:
                chunk = b""  # an unreadable stdin ends the stream instead of hanging it
            if not chunk:
                loop.call_soon_threadsafe(reader.feed_eof)
                return
            loop.call_soon_threadsafe(reader.feed_data, chunk)
