# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for forwarding a validated `HubCall` to the local hub (ADR-0100)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.domain.hub_scope import HubScope

if TYPE_CHECKING:
    from vibey.domain.host_tools import HubCall
    from vibey.infrastructure.mcp.hub_gateway import HubGatewayResponse


@runtime_checkable
class HubGatewayInterface(Protocol):
    def agent_scopes(self) -> frozenset[HubScope]:
        """The scopes declared for the agent principal on this hub."""
        ...

    def call(self, call: HubCall) -> HubGatewayResponse:
        """Execute ``call`` against the running hub, auto-starting it once if needed."""
        ...
