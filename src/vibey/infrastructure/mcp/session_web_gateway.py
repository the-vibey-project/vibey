# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub gateway behind `vibey mcp --scope web`: an engine session's own, web only (SP-LOOPS
Phase 6, Task 6; R3).

A claudeloop run reaches the hub's web tools through one MCP server in its capability snapshot,
`vibey-web`, which the worker adds when the run holds a web grant and which the scrubbed launcher
starts with exactly the grant's two names (`VIBEY_HUB_URL`, `VIBEY_WEB_TOKEN_FILE`). That server
is this gateway under the family's own stdio MCP server (`stdio_server.py`), given the hub's web
catalog alone (`WEB_TOOL_CATALOG`).

It is not the agent's gateway: it never reads the agent token, never starts a hub and holds
only `web`. Each call goes through the session's own client (`web/session_hub_client.py`), the
one `vibey search` uses, so the rules are that client's: loopback only, the token read from its
file on every call and never kept, sent once, refusals by kind, the token never in an error. A
call for any tool but `vibey_search` or `vibey_fetch`, a session with no web, and a person (no
session names at all) are refused before a client is built. Declared by
`interfaces/session_web_gateway_interface.py::SessionWebGatewayInterface`.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from typing import Final

from vibey.domain.host_tools import HubCall
from vibey.domain.hub_scope import HubScope
from vibey.domain.session_principal import SESSION_SCOPES
from vibey.domain.session_web_state import HUB_URL_VARIABLE, TOKEN_FILE_VARIABLE
from vibey.infrastructure.mcp.hub_gateway import HubGatewayResponse
from vibey.infrastructure.web.interfaces.session_hub_client_interface import (
    SessionHubClientInterface,
)
from vibey.infrastructure.web.interfaces.session_web_access_interface import (
    SessionWebAccessInterface,
)
from vibey.infrastructure.web.session_hub_client import SessionHubClient, SessionHubError

type SessionHubFactory = Callable[[SessionWebAccessInterface], SessionHubClientInterface]

WEB_ACTS: Final[Mapping[str, str]] = {
    "vibey_search": "search the web",
    "vibey_fetch": "fetch a web page",
}
"""The only two tools this gateway sends, and how a refusal names each."""
NOT_A_SESSION: Final = (
    "vibey mcp --scope web serves only an engine session given its web grant "
    f"({HUB_URL_VARIABLE} and {TOKEN_FILE_VARIABLE}); this process was given neither"
)


class SessionWebGateway:
    """Declared by `interfaces/session_web_gateway_interface.py::SessionWebGatewayInterface`."""

    def __init__(
        self,
        access: SessionWebAccessInterface,
        *,
        hub: SessionHubFactory = SessionHubClient.for_access,
    ) -> None:
        self._access = access
        self._hub = hub

    def agent_scopes(self) -> frozenset[HubScope]:
        return SESSION_SCOPES

    def call(self, call: HubCall) -> HubGatewayResponse:
        what = WEB_ACTS.get(call.tool)
        if what is None:
            raise SessionHubError(
                f"this session's web connector sends only vibey_search and vibey_fetch, never "
                f"{call.tool}",
                kind="refused",
            )
        if self._access.mode != "hub":
            raise SessionHubError(self._access.reason or NOT_A_SESSION, kind="unconfigured")
        document = self._hub(self._access).send(call, what)
        return HubGatewayResponse(
            status_code=200, text=json.dumps(document, ensure_ascii=False), ok=True
        )

    def reach(self, call: HubCall) -> HubGatewayResponse:
        return self.call(call)
