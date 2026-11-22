# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Who brings the hub back when a hub read finds none, decided per call (ADR-0101).

`HubGateway` calls its starter whenever a read finds no hub. Under `vibey acp` that starter is
this router:

- **The keep-alive owns the hub's unit** (vibey loaded it, the operator has not edited it, and
  it is not a hub running outside the service manager): the router only asks the keep-alive for
  a probe and says the hub is away. The keep-alive is the one authority that restarts the unit,
  under the bootstrap lock, with its rate limit, after probing again -- so a read never restarts
  a hub that is still starting, never kicks a unit the keep-alive just restarted, and two
  windows restart it once.
- **Otherwise** (no unit loaded: the grant is off, no service manager, a failed load, an edited
  unit, or a hub running outside the service manager), the bounded `vibey hub start` fallback
  runs (`BoundedHubStarter`). It never touches a unit: an edited unit is never restarted, and a
  second hub never starts beside a live one (`vibey hub start` finds its lock held).

Declared by `interfaces/hub_start_router_interface.py`.
"""

from __future__ import annotations

from vibey.application.acp.interfaces.acp_keep_alive_interface import AcpKeepAliveInterface
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError, HubStarter


class HubStartRouter:
    """Declared by `HubStartRouterInterface`."""

    def __init__(self, fallback: HubStarter) -> None:
        self._fallback = fallback
        self._keep_alive: AcpKeepAliveInterface | None = None

    def attach(self, keep_alive: AcpKeepAliveInterface) -> None:
        self._keep_alive = keep_alive

    def __call__(self) -> bool:
        keep_alive = self._keep_alive
        if keep_alive is not None and keep_alive.owns_hub():
            keep_alive.request_probe()
            raise HubGatewayError(
                "the hub is away; vibey's keep-alive is checking its service and restarts it if "
                "it is down -- try again in a moment"
            )
        return self._fallback()
