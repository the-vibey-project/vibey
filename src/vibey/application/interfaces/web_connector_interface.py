# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for a run's `vibey-web` MCP connector (SP-LOOPS Phase 6, Task 6; R3). Interfaces
declare; they never consume."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec


@runtime_checkable
class WebConnectorInterface(Protocol):
    def spec(self, token_file: Path) -> McpServerSpec:
        """The one MCP server a run holding a web grant is given: `vibey-web`, local (stdio, so
        started through the scrubbed launcher), keeping exactly `VIBEY_HUB_URL` and
        `VIBEY_WEB_TOKEN_FILE`, running `vibey mcp --scope web --token-file <token_file>`."""
        ...
