# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory fakes for qwenloop's declared seams, shared by the tests (no outside service)."""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.mcp.interfaces.mcp_transport_factory_interface import (
    McpTransportFactoryInterface,
)
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface

from qwenloop.application.interfaces import OllamaProbeInterface


class FakeOllamaModelProbe:
    """What an Ollama would say a model can do: as told, counting asks."""

    def __init__(self, reported: frozenset[str] | None = None) -> None:
        self.reported = reported
        self.asked: list[tuple[str, str]] = []

    def capabilities(self, base_url: str, model: str) -> frozenset[str] | None:
        self.asked.append((base_url, model))
        return self.reported


class FakeOllamaProbe:
    """An in-memory stand-in for the local-Ollama probe: answers as told, counts asks."""

    def __init__(self, available: bool = False) -> None:
        self.answer = available
        self.asked = 0

    def available(self) -> bool:
        self.asked += 1
        return self.answer


class MemoryMcpServer:
    """An MCP server held in memory behind the transport seam: it answers what the client writes
    from inside the writer, so no socket, process or sleep is involved. It lists `echo` and
    answers each call with the call's arguments as JSON."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.reader: asyncio.StreamReader | None = None
        self.calls = 0
        self.opened = 0

    async def open(self) -> tuple[asyncio.StreamReader, Callable[[str], Awaitable[None]]]:
        self.opened += 1
        self.reader = asyncio.StreamReader()
        return self.reader, self.write_line

    async def write_line(self, line: str) -> None:
        message = json.loads(line)
        if "id" not in message:
            return
        params = message.get("params") or {}
        result: dict[str, Any]
        if message["method"] == "initialize":
            result = {"protocolVersion": params["protocolVersion"]}
        elif message["method"] == "tools/list":
            result = {"tools": [{"name": "echo", "description": "Echo.", "inputSchema": {}}]}
        else:
            self.calls += 1
            text = json.dumps(params.get("arguments"), sort_keys=True)
            result = {"content": [{"type": "text", "text": text}]}
        reply = {"jsonrpc": "2.0", "id": message["id"], "result": result}
        assert self.reader is not None
        self.reader.feed_data((json.dumps(reply) + "\n").encode())

    async def close(self, grace_seconds: float) -> None:
        del grace_seconds
        if self.reader is not None and not self.reader.at_eof():
            self.reader.feed_eof()

    def describe(self) -> str:
        return f"MCP server {self.name!r} (https example.test)"


class MemoryTransports:
    """A transport factory whose every server is one `MemoryMcpServer` per name."""

    def __init__(self) -> None:
        self.servers: dict[str, MemoryMcpServer] = {}

    def for_spec(self, server: McpServerSpec) -> MemoryMcpServer:
        if server.trust == "remote" and server.url is None:
            raise ValueError(f"MCP server {server.name!r} is remote but has no URL")
        return self.servers.setdefault(server.name, MemoryMcpServer(server.name))


assert isinstance(FakeOllamaProbe(), OllamaProbeInterface)
assert isinstance(MemoryMcpServer("x"), McpTransportInterface)
assert isinstance(MemoryTransports(), McpTransportFactoryInterface)
