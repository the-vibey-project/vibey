# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP sessions of one run, one per server (SP-LOOPS Phase 5, Task 3; R5, R6, R13)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.mcp_server_spec import McpTrust
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_tool import McpTool


@runtime_checkable
class McpSessionPoolInterface(Protocol):
    @property
    def names(self) -> tuple[str, ...]:
        """The configured servers, in their configured order."""
        ...

    def trust_of(self, name: str) -> McpTrust:
        """A server's trust level. Raises `McpUnavailable` for an unknown server."""
        ...

    async def tools(self, name: str) -> tuple[McpTool, ...]:
        """A server's tools, starting its session on first use."""
        ...

    async def call(self, name: str, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        """Call one tool, starting the server's session on first use. A remote server's call
        spends one of its run's calls first. Raises `McpUnavailable` or `McpToolError`."""
        ...

    def remote_calls_left(self, name: str) -> int | None:
        """The `tools/call` requests a remote server has left this run; None for a local one."""
        ...

    async def aclose(self) -> None:
        """Close every live session. Never raises, and is idempotent; nothing starts after."""
        ...
