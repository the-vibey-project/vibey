# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/acp/hub_start_router.py` (ADR-0016, ADR-0101). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.application.acp.interfaces.acp_keep_alive_interface import AcpKeepAliveInterface


@runtime_checkable
class HubStartRouterInterface(Protocol):
    def attach(self, keep_alive: AcpKeepAliveInterface) -> None:
        """The keep-alive asked first, once it exists (it needs the gateway this router serves)."""
        ...

    def __call__(self) -> bool:
        """A hub read found no hub. While the keep-alive owns the hub's unit, ask it for a probe
        and raise `HubGatewayError` at once (nothing is restarted here); otherwise run the
        bounded `vibey hub start` fallback."""
        ...
