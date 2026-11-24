# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Which transport reaches a configured MCP server (SP-LOOPS Phase 5, R13, R14).

A `local` server is a `StdioTransport` whose argv is `ScrubbedLaunch(...).argv(server)`: the
environment handed here reaches only the launcher, which keeps the server's `env_allow` names and
nothing else. A `remote` server is an `HttpTransport` on the server's https URL, which is sent no
environment at all. Each call makes a fresh, unopened transport. Declared by
`interfaces/mcp_transport_factory_interface.py::McpTransportFactoryInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from vibey_runners.common.capabilities.interfaces.scrubbed_launch_interface import (
    ScrubbedLaunchInterface,
)
from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.mcp.http_transport import HttpTransport
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface
from vibey_runners.common.mcp.stdio_transport import StdioTransport


class McpTransportFactory:
    """Declared by `interfaces/mcp_transport_factory_interface.py::McpTransportFactoryInterface`."""

    def __init__(
        self,
        launch: ScrubbedLaunchInterface,
        *,
        cwd: Path,
        environ: Mapping[str, str],
        timeout_seconds: float,
    ) -> None:
        self._launch = launch
        self._cwd = cwd
        self._environ = dict(environ)
        self._timeout = timeout_seconds

    def for_spec(self, server: McpServerSpec) -> McpTransportInterface:
        if server.trust == "local":
            return StdioTransport(server.name, self._launch.argv(server), self._environ, self._cwd)
        if server.url is None:
            raise ValueError(f"MCP server {server.name!r} is remote but has no URL")
        return HttpTransport(server.name, server.url, timeout_seconds=self._timeout)
