# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The one place the argv that starts a local MCP server is built (SP-LOOPS Phase 5, R14)."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec


@runtime_checkable
class ScrubbedLaunchInterface(Protocol):
    def argv(self, server: McpServerSpec) -> tuple[str, ...]:
        """The launcher, one `--allow NAME` for each name in `env_allow`, `--`, then the
        server's own command. Holds names only, never a value. Raises `ValueError` for a
        server that is not `local` with a command."""
        ...
