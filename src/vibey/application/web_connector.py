# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The MCP connector a claudeloop run reaches the hub's web tools through (SP-LOOPS Phase 6, Task
6; R3).

claudeloop's own `WebSearch` and `WebFetch` stay disallowed, and the claudeloop runner imports
nothing from vibey, so its way to the hub is one more MCP server in the run's own capability
snapshot, which the worker writes: `vibey-web`. It is local, so claudeloop's translator types it
`"type": "stdio"` and starts it through the scrubbed launcher, which keeps only its `env_allow`:
exactly the grant's two names (`VIBEY_HUB_URL`, `VIBEY_WEB_TOKEN_FILE`), the family's one list
(`web_grant_names.py`), the same pair the local runner's shell keeps. It runs the `vibey`
installed beside the worker (`VibeyCommand`, given at composition) as `mcp --scope web
--token-file <the run's token file>`, which serves only `vibey_search` and `vibey_fetch`. The
path is an argument and the token never is: it stays in its 0600 file.

Pure: no environment, no file. Declared by
`interfaces/web_connector_interface.py::WebConnectorInterface`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from vibey_runners.common.capabilities.mcp_server_spec import McpServerSpec
from vibey_runners.common.capabilities.web_grant_names import WEB_GRANT_NAMES

WEB_CONNECTOR_NAME: Final = "vibey-web"
"""The connector's name in a run's snapshot; a person's own server of that name is never
replaced."""


class WebConnector:
    """Declared by `interfaces/web_connector_interface.py::WebConnectorInterface`. `vibey` is the
    command to run: the worker's own, resolved at composition; the bare name only by default."""

    def __init__(self, vibey: str = "vibey") -> None:
        self._vibey = vibey

    def spec(self, token_file: Path) -> McpServerSpec:
        return McpServerSpec(
            name=WEB_CONNECTOR_NAME,
            trust="local",
            command=(self._vibey, "mcp", "--scope", "web", "--token-file", str(token_file)),
            url=None,
            env_allow=tuple(sorted(WEB_GRANT_NAMES)),
        )
