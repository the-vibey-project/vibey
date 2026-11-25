# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey mcp`: the stdio MCP server a frontier chat client launches (ADR-0100).

A thin stdio JSON-RPC 2.0 wrapper over the hub API (`/api/v1`). It authenticates as the scoped
agent principal (`<state_dir>/agent.token`), never the host token, so the hub enforces the
configured `[hub] agent_scopes` ceiling (`view`, `answer`, `run` by default; never `spend`,
`bump` or `workflows`).

**`--scope web`** (SP-LOOPS Phase 6, Task 6; R3) is the server a claudeloop run's `vibey-web`
connector starts, not a chat client's: it serves exactly `vibey_search` and `vibey_fetch`
(`WEB_TOOL_CATALOG`), as the engine session's own web-only principal, never the agent's. It reads
the hub's address from `VIBEY_HUB_URL` and the session's token file from `--token-file`, which
stands for `VIBEY_WEB_TOKEN_FILE` (the worker gives both the same path); the token is read from
that file on every call. A process with no web grant is served the two tools and told why on
each call; nothing is sent.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Annotated, Final, Self, TextIO

import typer

from vibey.cli.interfaces.mcp_interface import McpCommandInterface
from vibey.domain.host_tools import SESSION_WEB_INSTRUCTIONS, WEB_TOOL_CATALOG
from vibey.domain.session_web_state import TOKEN_FILE_VARIABLE
from vibey.infrastructure.mcp.interfaces.stdio_server_interface import McpStdioServerInterface
from vibey.infrastructure.mcp.session_web_gateway import SessionHubFactory, SessionWebGateway
from vibey.infrastructure.mcp.stdio_server import MCP_STDIO_SERVER, McpStdioServer
from vibey.infrastructure.web.interfaces.session_web_access_interface import (
    SessionWebAccessInterface,
)
from vibey.infrastructure.web.session import SessionWebAccess
from vibey.infrastructure.web.session_hub_client import SessionHubClient

SESSION_HUB: SessionHubFactory = SessionHubClient.for_access
"""How `--scope web` reaches the hub from a session's access; the tests stand a stub hub in."""


class McpScope(StrEnum):
    """What `vibey mcp` serves other than the agent's tools."""

    WEB = "web"
    """Only `vibey_search` and `vibey_fetch`, as an engine session's own web-only principal."""


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
        access: SessionWebAccessInterface | None = None,
    ) -> None:
        self._server = server
        self._stdin = stdin
        self._stdout = stdout
        self._access = access

    @classmethod
    def web(
        cls,
        environ: Mapping[str, str],
        token_file: Path | None,
        *,
        hub: SessionHubFactory | None = None,
        stdin: TextIO | None = None,
        stdout: TextIO | None = None,
    ) -> Self:
        """The web-only server for the session `environ` describes; `token_file`, when given,
        stands for `VIBEY_WEB_TOKEN_FILE`."""
        if token_file is not None:
            environ = {**environ, TOKEN_FILE_VARIABLE: str(token_file)}
        access = SessionWebAccess.from_environment(environ)
        gateway = SessionWebGateway(access, hub=hub if hub is not None else SESSION_HUB)
        server = McpStdioServer(
            gateway=gateway, tools=WEB_TOOL_CATALOG, instructions=SESSION_WEB_INSTRUCTIONS
        )
        return cls(server=server, stdin=stdin, stdout=stdout, access=access)

    @property
    def access(self) -> SessionWebAccessInterface | None:
        """The session's web access, for `--scope web`; None for the agent's server."""
        return self._access

    def run(self) -> None:
        in_stream = self._stdin if self._stdin is not None else sys.stdin
        out_stream = self._stdout if self._stdout is not None else sys.stdout
        self._server.serve(in_stream, out_stream)


MCP_COMMAND: Final[McpCommandInterface] = McpCommand()


def mcp(
    scope: Annotated[
        McpScope | None,
        typer.Option(
            "--scope",
            help="web: serve only vibey_search and vibey_fetch, as an engine session's own "
            "web-only principal (VIBEY_HUB_URL and its token file); for a claudeloop run's "
            "vibey-web connector, never a chat client",
        ),
    ] = None,
    token_file: Annotated[
        Path | None,
        typer.Option(
            "--token-file",
            help="With --scope web: the session's token file (stands for VIBEY_WEB_TOKEN_FILE)",
        ),
    ] = None,
) -> None:
    """Serve the Model Context Protocol (MCP) over stdio as the scoped agent principal."""
    # Module-level function because Typer builds the command from a plain function signature.
    if scope is None:
        if token_file is not None:
            raise typer.BadParameter("--token-file is only for --scope web")
        MCP_COMMAND.run()
        return
    McpCommand.web(os.environ, token_file).run()
