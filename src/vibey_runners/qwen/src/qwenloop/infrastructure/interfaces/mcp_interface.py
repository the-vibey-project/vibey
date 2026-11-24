# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reaching the MCP servers a run can use (SP-LOOPS Phase 5, R4 to R7, R13)."""

from collections.abc import Mapping
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.mcp_server_spec import McpTrust
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_tool import McpTool


@runtime_checkable
class McpGatewayInterface(Protocol):
    """Every method that reaches a server raises only `McpUnavailable` (the server cannot be
    reached, its session is dead, or it is unknown, out of restarts or out of calls) or
    `McpToolError` (it answered with an error and is still alive). Neither ends a run: the tool
    dispatcher turns both into an error the model reads."""

    @property
    def server_names(self) -> tuple[str, ...]:
        """The servers a run can call, in their configured order."""
        ...

    @property
    def unsupported(self) -> Mapping[str, str]:
        """Declared servers a run cannot call, each with why."""
        ...

    @property
    def max_tools(self) -> int:
        """The most tools read from one server's listing (`[mcp] max_tools`)."""
        ...

    def trust_of(self, server: str) -> McpTrust:
        """A server's trust level, `local` or `remote`."""
        ...

    def remote_calls_left(self, server: str) -> int | None:
        """The `tools/call` requests a remote server has left this run; None for a local one."""
        ...

    async def list_tools(self, server: str) -> tuple[McpTool, ...]:
        """One server's tools, starting its session on first use."""
        ...

    async def schema(self, server: str, tool: str) -> Mapping[str, object]:
        """One tool's input schema, whole. `McpToolError` when the server lists no such tool."""
        ...

    async def call(self, server: str, tool: str, arguments: Mapping[str, object]) -> McpCallResult:
        """The tool's text, and whether the server reported it as an error."""
        ...

    async def aclose(self) -> None:
        """Close every session the run started. Never raises, and is idempotent; nothing
        starts after it."""
        ...
