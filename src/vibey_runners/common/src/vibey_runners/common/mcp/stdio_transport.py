# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A `local` MCP server as a child process speaking newline-delimited JSON-RPC on its stdio
(SP-LOOPS Phase 5, R5).

The server leads a process group of its own (`start_new_session=True`), so whatever it starts
is ended with it. Its stderr is discarded: what a server writes there is its own business and
could hold anything it was given. The argv is the runner's to choose; for a snapshot run it is
`ScrubbedLaunch(...).argv(server)`, so the environment handed here reaches the server only
through the launcher's scrub. `close` closes the server's stdin (the MCP spec's signal to
exit), gives it `grace_seconds`, then kills the whole group and reaps the leader. `describe`
names the server, the kind and, once reaped, how it ended: never the argv or the environment.
Declared by `interfaces/mcp_transport_interface.py::McpTransportInterface`.
"""

from __future__ import annotations

import asyncio
import contextlib
import os
import signal
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Final, cast

DEFAULT_LIMIT_BYTES: Final = 16_777_216
"""The longest line the reader accepts, the JSON-RPC peer's own default bound."""


class StdioTransport:
    """Declared by `interfaces/mcp_transport_interface.py::McpTransportInterface`."""

    def __init__(
        self,
        name: str,
        argv: Sequence[str],
        env: Mapping[str, str],
        cwd: Path,
        *,
        limit_bytes: int = DEFAULT_LIMIT_BYTES,
        spawn: Callable[..., Awaitable[asyncio.subprocess.Process]] = (
            asyncio.create_subprocess_exec
        ),
        killpg: Callable[[int, int], None] = os.killpg,
    ) -> None:
        if not argv:
            raise ValueError(f"MCP server {name!r} has an empty argv")
        self._name = name
        self._argv = tuple(argv)
        self._env = dict(env)
        self._cwd = cwd
        self._limit = limit_bytes
        self._spawn = spawn
        self._killpg = killpg
        self._process: asyncio.subprocess.Process | None = None
        self._stdin: asyncio.StreamWriter | None = None
        self._returncode: int | None = None

    async def open(self) -> tuple[asyncio.StreamReader, Callable[[str], Awaitable[None]]]:
        # The argv is the runner's own (the scrubbed launcher and the person's configured
        # command); no shell is involved. bandit does not flag a call through an attribute.
        process = await self._spawn(
            *self._argv,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
            env=dict(self._env),
            cwd=self._cwd,
            start_new_session=True,
            limit=self._limit,
        )
        self._process = process
        self._stdin = cast(asyncio.StreamWriter, process.stdin)
        return cast(asyncio.StreamReader, process.stdout), self._write_line

    async def _write_line(self, line: str) -> None:
        stdin = cast(asyncio.StreamWriter, self._stdin)
        stdin.write(line.encode("utf-8"))
        await stdin.drain()

    async def close(self, grace_seconds: float) -> None:
        process, self._process = self._process, None
        if process is None:
            return
        cast(asyncio.StreamWriter, self._stdin).close()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(process.wait(), grace_seconds)
        # The group outlives its leader while any member lives, so it is killed whether or not
        # the leader has already exited. One already gone (or never ours) is closed already.
        with contextlib.suppress(ProcessLookupError, PermissionError):
            self._killpg(process.pid, signal.SIGKILL)
        self._returncode = await process.wait()

    def describe(self) -> str:
        if self._returncode is None:
            return f"MCP server {self._name!r} (stdio)"
        if self._returncode < 0:
            return f"MCP server {self._name!r} (stdio, ended by signal {-self._returncode})"
        return f"MCP server {self._name!r} (stdio, exited with code {self._returncode})"
