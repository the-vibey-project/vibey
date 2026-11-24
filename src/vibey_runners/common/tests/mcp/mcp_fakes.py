# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory doubles for the MCP client's tests: a transport that is a scripted server, and a
session the pool can be handed.

`MemoryTransport` answers what the client writes by calling `handler(message, transport)` inside
`write_line`, so a reply is fed to the reader before the client awaits it. No process, no
network, no sleep.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from typing import Any

from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpUnavailable
from vibey_runners.common.mcp.mcp_tool import McpTool

Handler = Callable[[dict[str, Any], "MemoryTransport"], None]


def standard(message: dict[str, Any], server: MemoryTransport) -> None:
    """A well-behaved server: agrees to the offered version, lists `echo`, echoes calls."""
    method = message.get("method")
    if "id" not in message or method is None:
        return
    params = message.get("params") or {}
    if method == "initialize":
        server.reply(message, {"protocolVersion": params["protocolVersion"], "capabilities": {}})
    elif method == "tools/list":
        server.reply(
            message,
            {
                "tools": [
                    {"name": "echo", "description": "Echo.", "inputSchema": {"type": "object"}}
                ]
            },
        )
    elif method == "tools/call":
        text = json.dumps(params.get("arguments"), sort_keys=True)
        server.reply(message, {"content": [{"type": "text", "text": text}]})


class MemoryTransport:
    """A scripted MCP server behind the transport seam."""

    def __init__(
        self,
        handler: Handler = standard,
        *,
        name: str = "mem",
        refuse_open: Exception | None = None,
        refuse_write: Exception | None = None,
    ) -> None:
        self.handler = handler
        self.name = name
        self.refuse_open = refuse_open
        self.refuse_write = refuse_write
        self.reader = asyncio.StreamReader()
        self.sent: list[dict[str, Any]] = []
        self.opened = 0
        self.closed: list[float] = []

    async def open(self) -> tuple[asyncio.StreamReader, Callable[[str], Any]]:
        if self.refuse_open is not None:
            raise self.refuse_open
        self.opened += 1
        return self.reader, self.write_line

    async def write_line(self, line: str) -> None:
        if self.refuse_write is not None:
            raise self.refuse_write
        assert line.endswith("\n")
        message = json.loads(line)
        self.sent.append(message)
        self.handler(message, self)

    async def close(self, grace_seconds: float) -> None:
        self.closed.append(grace_seconds)
        if not self.reader.at_eof():
            self.reader.feed_eof()

    def describe(self) -> str:
        return f"MCP server {self.name!r} (memory)"

    # -- what a script uses --------------------------------------------------------------

    def send(self, message: Mapping[str, Any]) -> None:
        self.reader.feed_data((json.dumps({"jsonrpc": "2.0", **message}) + "\n").encode())

    def reply(self, request: Mapping[str, Any], result: Mapping[str, Any]) -> None:
        self.send({"id": request["id"], "result": dict(result)})

    def fail(self, request: Mapping[str, Any], code: int, text: str) -> None:
        self.send({"id": request["id"], "error": {"code": code, "message": text}})

    def methods(self) -> list[str]:
        return [str(message.get("method")) for message in self.sent if "method" in message]


def initialize_with(version: object) -> Handler:
    """A server that answers `initialize` with `version` and is otherwise `standard`."""

    def handler(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "initialize":
            server.reply(message, {"protocolVersion": version})
        else:
            standard(message, server)

    return handler


class FakeSession:
    """A session the pool can be handed: scripted start, list and call outcomes."""

    def __init__(
        self,
        *,
        start_error: str | None = None,
        call_errors: list[Exception] | None = None,
        close_error: Exception | None = None,
    ) -> None:
        self.start_error = start_error
        self.call_errors = list(call_errors or [])
        self.close_error = close_error
        self.started = 0
        self.calls: list[tuple[str, dict[str, object]]] = []
        self.closed: list[float] = []
        self._alive = False

    @property
    def alive(self) -> bool:
        return self._alive

    async def start(self) -> None:
        self.started += 1
        if self.start_error is not None:
            raise McpUnavailable(self.start_error)
        self._alive = True

    async def list_tools(self) -> tuple[McpTool, ...]:
        self._maybe_fail()
        return (McpTool("echo", "Echo.", {"type": "object"}),)

    async def call(self, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        self.calls.append((tool, dict(arguments)))
        self._maybe_fail()
        return McpCallResult(f"{tool} done", False)

    async def close(self, grace_seconds: float) -> None:
        self.closed.append(grace_seconds)
        self._alive = False
        if self.close_error is not None:
            raise self.close_error

    def _maybe_fail(self) -> None:
        if self.call_errors:
            error = self.call_errors.pop(0)
            if isinstance(error, McpUnavailable):
                self._alive = False
            raise error
