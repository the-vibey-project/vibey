# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for reaching the MCP servers a run can use."""

from collections.abc import Mapping
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class McpGatewayInterface(Protocol):
    @property
    def server_names(self) -> tuple[str, ...]:
        """The stdio servers a run can call."""
        ...

    @property
    def unsupported(self) -> Mapping[str, str]:
        """Declared servers a run cannot call, each with why."""
        ...

    async def list_tools(self, server: str) -> list[dict[str, Any]]:
        """One server's tools: name, description and input schema."""
        ...

    async def call(self, server: str, tool: str, arguments: Mapping[str, Any]) -> tuple[str, bool]:
        """The tool's text, and whether the server reported it as an error. Raises
        `McpError` when the server cannot be reached or answers with one."""
        ...
