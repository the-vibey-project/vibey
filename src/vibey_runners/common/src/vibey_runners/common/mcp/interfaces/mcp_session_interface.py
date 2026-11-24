# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP session with one server (SP-LOOPS Phase 5, Task 3; R6, R15)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_tool import McpTool


@runtime_checkable
class McpSessionInterface(Protocol):
    @property
    def alive(self) -> bool:
        """Whether the session started and has not died or been closed."""
        ...

    async def start(self) -> None:
        """`initialize` offering the latest protocol version, check the answer against the
        supported ones, then `notifications/initialized`. Raises `McpUnavailable` on any
        failure, the session then dead."""
        ...

    async def list_tools(self) -> tuple[McpTool, ...]:
        """The server's tools, following `nextCursor` up to the session's `max_tools`, cached
        until the server says its list changed. Raises `McpUnavailable` or `McpToolError`."""
        ...

    async def call(self, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        """Call one tool. Raises `McpToolError` for a JSON-RPC error answer (the session stays
        alive) and `McpUnavailable` when the session dies."""
        ...

    async def close(self, grace_seconds: float) -> None:
        """End the session and close its transport with `grace_seconds`. Idempotent."""
        ...
