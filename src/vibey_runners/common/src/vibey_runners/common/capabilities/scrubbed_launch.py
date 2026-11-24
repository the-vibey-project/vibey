# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The argv that starts a `local` MCP server through the scrubbed launcher, built once for every
runner (SP-LOOPS Phase 5, R14).

The launcher prefix is the interpreter and `LAUNCHER_ARGS` (`python -I -m
vibey_runners.common.capabilities.scrubbed_exec`), given by each runner's composition root. The
argv is that prefix, one `--allow NAME` for each name in `env_allow`, `--`, then the server's own
command: names only, so an environment value never reaches an argv. claudeloop's
`McpConfigTranslator` and the local runner's stdio transport both start a server from it. Pure:
no environment, no process. Declared by
`interfaces/scrubbed_launch_interface.py::ScrubbedLaunchInterface`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec

_ALLOW: Final = "--allow"
_SEPARATOR: Final = "--"


class ScrubbedLaunch:
    """Declared by `interfaces/scrubbed_launch_interface.py::ScrubbedLaunchInterface`."""

    def __init__(self, launcher: Sequence[str]) -> None:
        if not launcher:
            raise ValueError("the MCP launcher prefix must name at least a command")
        self._launcher = tuple(launcher)

    def argv(self, server: McpServerSpec) -> tuple[str, ...]:
        if server.trust != "local" or not server.command:
            raise ValueError(f"MCP server {server.name!r} is not a local server with a command")
        allow = tuple(token for name in server.env_allow for token in (_ALLOW, name))
        return (*self._launcher, *allow, _SEPARATOR, *server.command)
