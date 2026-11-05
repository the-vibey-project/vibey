# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Hand-rolled line-delimited JSON-RPC 2.0 MCP server over the hub API (ADR-0100).

Adds zero external MCP SDK dependency: the stdio transport is newline-delimited JSON-RPC 2.0 with
four request methods (`initialize`, `ping`, `tools/list`, `tools/call`) and notifications
(`notifications/initialized`, `notifications/cancelled`). Every tool call goes through
`HostToolsInterface.build_call` and `HubGatewayInterface.call` using the scoped agent principal.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Any, Final, TextIO
from uuid import uuid4

from vibey import __version__
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import (
    HOST_INSTRUCTIONS,
    HOST_TOOL_CATALOG,
    MAX_RESPONSE_CHARS,
    HostToolError,
)
from vibey.domain.interfaces.host_tools_interface import HostToolsInterface
from vibey.infrastructure.mcp.hub_gateway import HUB_GATEWAY
from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface
from vibey.infrastructure.mcp.interfaces.stdio_server_interface import McpStdioServerInterface

SUPPORTED_PROTOCOLS: Final[tuple[str, ...]] = (
    "2024-11-05",
    "2025-03-26",
    "2025-06-18",
    "2025-11-25",
)
LATEST_PROTOCOL: Final = SUPPORTED_PROTOCOLS[-1]

PARSE_ERROR: Final = -32700
INVALID_REQUEST: Final = -32600
METHOD_NOT_FOUND: Final = -32601
INVALID_PARAMS: Final = -32602


class McpStdioServer:
    """Line-delimited JSON-RPC 2.0 MCP server backed by `HubGatewayInterface`.

    Declared by `interfaces/stdio_server_interface.py::McpStdioServerInterface`.
    """

    def __init__(
        self,
        *,
        gateway: HubGatewayInterface = HUB_GATEWAY,
        tools: HostToolsInterface = HOST_TOOL_CATALOG,
        instructions: str = HOST_INSTRUCTIONS,
        request_id_factory: Callable[[], str] = lambda: f"mcp-{uuid4()}",
        max_response_chars: int = MAX_RESPONSE_CHARS,
    ) -> None:
        self._gateway = gateway
        self._tools = tools
        self._instructions = instructions
        self._request_id_factory = request_id_factory
        self._max_response_chars = max_response_chars

    def serve(self, stdin: TextIO, stdout: TextIO) -> None:
        """Read newline-delimited JSON-RPC messages from `stdin` and write replies to `stdout`."""
        for raw_line in stdin:
            reply = self.handle_line(raw_line)
            if reply is not None:
                stdout.write(reply + "\n")
                stdout.flush()

    def handle_line(self, line: str) -> str | None:
        stripped = line.strip()
        if not stripped:
            return None
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            return json.dumps(self._error(None, PARSE_ERROR, f"Parse error: {exc.msg}"))
        if not isinstance(parsed, Mapping):
            return json.dumps(
                self._error(None, INVALID_REQUEST, "Invalid Request: expected JSON object")
            )
        response = self.handle(parsed)
        return json.dumps(response) if response is not None else None

    def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        has_id = "id" in message
        msg_id = message.get("id")
        if message.get("jsonrpc") != "2.0" or not isinstance(message.get("method"), str):
            return self._error(
                msg_id if has_id else None,
                INVALID_REQUEST,
                "Invalid Request: jsonrpc='2.0' and string method are required",
            )
        method: str = message["method"]
        params = message.get("params")

        # Notifications carry no `id` and never receive a reply.
        if not has_id:
            return None

        if params is not None and not isinstance(params, Mapping):
            return self._error(msg_id, INVALID_PARAMS, "Invalid params: expected JSON object")
        params_map: Mapping[str, Any] = params if isinstance(params, Mapping) else {}

        if method == "initialize":
            return self._ok(msg_id, self._initialize(params_map))
        if method == "ping":
            return self._ok(msg_id, {})
        if method == "tools/list":
            scopes = self._gateway.agent_scopes()
            return self._ok(msg_id, {"tools": self._tools.mcp_definitions(scopes)})
        if method == "tools/call":
            return self._call_tool(msg_id, params_map)
        return self._error(msg_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def _initialize(self, params: Mapping[str, Any]) -> dict[str, Any]:
        requested = params.get("protocolVersion")
        negotiated = (
            requested
            if isinstance(requested, str) and requested in SUPPORTED_PROTOCOLS
            else LATEST_PROTOCOL
        )
        return {
            "protocolVersion": negotiated,
            "capabilities": {
                "tools": {"listChanged": False},
            },
            "serverInfo": {
                "name": "vibey",
                "title": "vibey hub MCP server",
                "version": __version__,
            },
            "instructions": self._instructions,
        }

    def _call_tool(self, msg_id: Any, params: Mapping[str, Any]) -> dict[str, Any]:
        name = params.get("name")
        if not isinstance(name, str) or not name.strip():
            return self._error(
                msg_id, INVALID_PARAMS, "Invalid params: tools/call requires string 'name'"
            )
        arguments = params.get("arguments")
        if arguments is not None and not isinstance(arguments, Mapping):
            return self._error(
                msg_id, INVALID_PARAMS, "Invalid params: 'arguments' must be a JSON object"
            )
        scopes = self._gateway.agent_scopes()
        tool = self._tools.by_name(name)
        if tool is not None and tool.scope not in scopes:
            return self._tool_result(
                msg_id,
                f"refused: tool {name!r} requires scope {tool.scope.value!r}, which is not "
                "granted to the agent principal on this hub",
                is_error=True,
            )
        try:
            call = self._tools.build_call(
                name,
                arguments,
                request_id=self._request_id_factory(),
            )
        except HostToolError as exc:
            return self._tool_result(msg_id, str(exc), is_error=True)

        try:
            response = self._gateway.call(call)
        except VibeyError as exc:
            return self._tool_result(msg_id, str(exc), is_error=True)

        if not response.ok:
            return self._tool_result(
                msg_id,
                f"hub refused ({response.status_code}): {response.text}",
                is_error=True,
            )
        return self._tool_result(msg_id, response.text, is_error=False)

    def _tool_result(self, msg_id: Any, text: str, *, is_error: bool) -> dict[str, Any]:
        bounded = self._tools.truncate(text, limit=self._max_response_chars)
        return self._ok(
            msg_id,
            {
                "content": [{"type": "text", "text": bounded}],
                "isError": is_error,
            },
        )

    @staticmethod
    def _ok(msg_id: Any, result: Mapping[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": msg_id, "result": dict(result)}

    @staticmethod
    def _error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": code, "message": message},
        }


MCP_STDIO_SERVER: Final[McpStdioServerInterface] = McpStdioServer()
