# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for `vibey mcp`: the stdio MCP command (ADR-0100)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class McpCommandInterface(Protocol):
    def run(self) -> None:
        """Serve the MCP JSON-RPC 2.0 loop over standard input and output."""
        ...
