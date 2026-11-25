# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the gateway `vibey mcp --scope web` serves an engine session through
(SP-LOOPS Phase 6, Task 6; R3). Interfaces declare; they never consume."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey.infrastructure.mcp.interfaces.hub_gateway_interface import HubGatewayInterface


@runtime_checkable
class SessionWebGatewayInterface(HubGatewayInterface, Protocol):
    """A `HubGatewayInterface` that holds only the `web` scope (`SESSION_SCOPES`) and sends
    only `vibey_search` and `vibey_fetch`, to the hub its session's environment names, with the
    session's own token read from its file on each call. `call` and `reach` are the same: it
    never starts a hub. A session with no web, a person, or any other tool is a
    `SessionHubError` that says why, and nothing is sent."""
