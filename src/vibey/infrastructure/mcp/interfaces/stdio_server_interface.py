# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the line-delimited JSON-RPC 2.0 MCP stdio server (ADR-0100)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol, TextIO, runtime_checkable


@runtime_checkable
class McpStdioServerInterface(Protocol):
    def handle(self, message: Mapping[str, Any]) -> dict[str, Any] | None:
        """Handle one parsed JSON-RPC 2.0 message and return the response, or None for a notification."""
        ...

    def handle_line(self, line: str) -> str | None:
        """Parse and handle one newline-delimited JSON-RPC line, returning the reply JSON or None."""
        ...

    def serve(self, stdin: TextIO, stdout: TextIO) -> None:
        """Run the line-delimited stdio loop until EOF."""
        ...
