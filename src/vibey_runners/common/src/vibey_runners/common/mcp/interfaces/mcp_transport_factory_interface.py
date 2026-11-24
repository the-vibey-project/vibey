# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which transport reaches a configured MCP server (SP-LOOPS Phase 5, R13, R14)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface


@runtime_checkable
class McpTransportFactoryInterface(Protocol):
    def for_spec(self, server: McpServerSpec) -> McpTransportInterface:
        """A fresh, unopened transport: stdio through the scrubbed launcher for a `local`
        server, streamable HTTP for a `remote` one. Raises `ValueError` for a `local` server
        with no command or a `remote` one with no URL."""
        ...
