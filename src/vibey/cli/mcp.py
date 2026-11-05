# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey mcp`: the stdio MCP server a frontier chat client launches (ADR-0100).

A thin stdio JSON-RPC 2.0 wrapper over the hub API (`/api/v1`). It authenticates as the scoped
agent principal (`<state_dir>/agent.token`), never the host token, so the hub enforces the
configured `[hub] agent_scopes` ceiling (`view`, `answer`, `run` by default; never `spend`,
`bump` or `workflows`).
"""

from __future__ import annotations

import sys
from typing import Final, TextIO

from vibey.cli.interfaces.mcp_interface import McpCommandInterface
from vibey.infrastructure.mcp.interfaces.stdio_server_interface import McpStdioServerInterface
from vibey.infrastructure.mcp.stdio_server import MCP_STDIO_SERVER


class McpCommand:
    """Runs the stdio MCP server over standard input and standard output.

    Declared by `interfaces/mcp_interface.py::McpCommandInterface`.
    """

    def __init__(
        self,
        *,
        server: McpStdioServerInterface = MCP_STDIO_SERVER,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> None:
        self._server = server
        self._stdin = stdin
        self._stdout = stdout

    def run(self) -> None:
        in_stream = self._stdin if self._stdin is not None else sys.stdin
        out_stream = self._stdout if self._stdout is not None else sys.stdout
        self._server.serve(in_stream, out_stream)


MCP_COMMAND: Final[McpCommandInterface] = McpCommand()


def mcp() -> None:
    """Serve the Model Context Protocol (MCP) over stdio as the scoped agent principal."""
    # Module-level function because Typer builds the command from a plain function signature.
    MCP_COMMAND.run()
