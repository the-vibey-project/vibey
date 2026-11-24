# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP session with one server, over the family's JSON-RPC peer (SP-LOOPS Phase 5, R5, R6,
R15).

`start` opens the transport, runs the peer's reader as a task the session owns, sends
`initialize` offering `LATEST_PROTOCOL`, accepts any version in `SUPPORTED_PROTOCOLS` the server
answers with, then sends `notifications/initialized`. Every request is bounded by
`timeout_seconds`.

A server that answers a request with a JSON-RPC error raises `McpToolError` and the session
carries on. Anything else that goes wrong kills the session: the transport cannot open, the
version is unknown, `initialize` is refused, the stream ends, a request times out, or a write
fails. A dead session closes its transport at once, with no grace (it has stopped being a
conversation), and raises `McpUnavailable` naming the server and the method. Requests to a
dead session are refused without a write.

The server may ask the client things too: `ping` is answered `{}`, anything else
`METHOD_NOT_FOUND`. `notifications/tools/list_changed` drops the cached tool list. Messages name
methods, never parameters. Declared by
`interfaces/mcp_session_interface.py::McpSessionInterface`.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from typing import Any

from vibey_runners.common.jsonrpc.codec import CODEC
from vibey_runners.common.jsonrpc.errors import METHOD_NOT_FOUND, PeerClosed, RpcError
from vibey_runners.common.jsonrpc.peer import JsonRpcPeer
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpToolError, McpUnavailable
from vibey_runners.common.mcp.mcp_tool import McpTool
from vibey_runners.common.mcp.protocol import LATEST_PROTOCOL, SUPPORTED_PROTOCOLS

_LIST_CHANGED = "notifications/tools/list_changed"


class McpSession:
    """Declared by `interfaces/mcp_session_interface.py::McpSessionInterface`."""

    def __init__(
        self,
        transport: McpTransportInterface,
        *,
        client_name: str,
        client_version: str,
        timeout_seconds: float,
        max_tools: int = 1024,
    ) -> None:
        self._transport = transport
        self._client_info = {"name": client_name, "version": client_version}
        self._timeout = timeout_seconds
        self._max_tools = max_tools
        self._peer: JsonRpcPeer | None = None
        self._runner: asyncio.Task[None] | None = None
        self._alive = False
        self._tools: tuple[McpTool, ...] | None = None

    @property
    def alive(self) -> bool:
        return self._alive

    async def start(self) -> None:
        try:
            reader, write_line = await self._transport.open()
        except Exception as exc:
            # Whatever the transport raises, the server is unreachable; only its type and
            # message travel, and a transport's own messages hold no environment value.
            raise McpUnavailable(
                f"{self._transport.describe()} could not start: {type(exc).__name__}: {exc}"
            ) from exc
        self._peer = JsonRpcPeer(
            reader,
            write_line,
            on_request=self._on_request,
            on_notification=self._on_notification,
            codec=CODEC,
            id_prefix="vibey-mcp",
        )
        self._runner = asyncio.create_task(self._peer.run())
        self._alive = True
        params = {
            "protocolVersion": LATEST_PROTOCOL,
            "capabilities": {},
            "clientInfo": dict(self._client_info),
        }
        try:
            result = await self._request("initialize", params)
        except McpToolError as exc:
            raise await self._die(f"refused initialize: {exc}") from exc
        version = result.get("protocolVersion")
        if version not in SUPPORTED_PROTOCOLS:
            raise await self._die(
                f"answered protocol version {version!r}; this client speaks "
                f"{', '.join(SUPPORTED_PROTOCOLS)}"
            )
        try:
            await self._peer.notify("notifications/initialized", {})
        except OSError as exc:
            raise await self._die(f"could not be written to: {type(exc).__name__}") from exc

    async def list_tools(self) -> tuple[McpTool, ...]:
        if self._tools is not None:
            return self._tools
        tools: list[McpTool] = []
        cursor: str | None = None
        for _page in range(self._max_tools):
            result = await self._request("tools/list", {} if cursor is None else {"cursor": cursor})
            listed = result.get("tools")
            for raw in listed if isinstance(listed, list) else []:
                if len(tools) < self._max_tools and isinstance(raw, Mapping):
                    tool = self._tool(raw)
                    if tool is not None:
                        tools.append(tool)
            following = result.get("nextCursor")
            if len(tools) >= self._max_tools or not isinstance(following, str) or not following:
                break
            cursor = following
        self._tools = tuple(tools)
        return self._tools

    async def call(self, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        result = await self._request("tools/call", {"name": tool, "arguments": dict(arguments)})
        content = result.get("content")
        texts = [
            str(part.get("text", ""))
            for part in (content if isinstance(content, list) else [])
            if isinstance(part, Mapping) and part.get("type") == "text"
        ]
        return McpCallResult("\n".join(texts), result.get("isError") is True)

    async def close(self, grace_seconds: float) -> None:
        self._alive = False
        await self._teardown(grace_seconds)

    # -- internals ------------------------------------------------------------------------

    @staticmethod
    def _tool(raw: Mapping[str, Any]) -> McpTool | None:
        name = raw.get("name")
        if not isinstance(name, str):
            return None
        description = raw.get("description")
        schema = raw.get("inputSchema")
        return McpTool(
            name,
            description if isinstance(description, str) else "",
            dict(schema) if isinstance(schema, Mapping) else {},
        )

    async def _request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        peer = self._peer
        if not self._alive or peer is None:
            raise McpUnavailable(f"{self._transport.describe()} is not running")
        try:
            return await peer.request(method, params, timeout=self._timeout)
        except RpcError as exc:
            raise McpToolError(
                f"{self._transport.describe()} answered {method} with error "
                f"{exc.code}: {exc.message}"
            ) from exc
        except PeerClosed as exc:
            raise await self._die(f"closed its stream during {method}") from exc
        except TimeoutError as exc:
            raise await self._die(f"did not answer {method} within {self._timeout:g}s") from exc
        except OSError as exc:
            raise await self._die(f"could not be written to: {type(exc).__name__}") from exc

    async def _die(self, reason: str) -> McpUnavailable:
        """End the session at once and say why, naming the server as it ended."""
        self._alive = False
        await self._teardown(0.0)
        return McpUnavailable(f"{self._transport.describe()} {reason}")

    async def _teardown(self, grace_seconds: float) -> None:
        runner, self._runner = self._runner, None
        self._peer = None
        await self._transport.close(grace_seconds)
        if runner is not None:
            runner.cancel()
            await asyncio.gather(runner, return_exceptions=True)

    async def _on_request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        if method == "ping":
            return {}
        raise RpcError(METHOD_NOT_FOUND, f"Method not found: {method}")

    async def _on_notification(self, method: str, params: Mapping[str, Any]) -> None:
        if method == _LIST_CHANGED:
            self._tools = None
