# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind running the hub and naming this computer.

Mirrors `vibey/infrastructure/hub/server.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import socket

    from fastapi import FastAPI

    from vibey.infrastructure.hub.tls import HubTls


@runtime_checkable
class HubServerInterface(Protocol):
    """Serves an ASGI app on one address until stopped.

    The address is bound first, on its own, so the hub can write its record only once the port
    is its own (SP-ACP Task 11b): a record never names a port another process holds."""

    def bind(self, host: str, port: int) -> socket.socket:
        """A socket bound to `host:port` and already listening (port 0: one the system picks).
        Raises `OSError` when the address cannot be had; nothing is left open then."""
        ...

    async def serve(self, app: FastAPI, *, sock: socket.socket, tls: HubTls | None = None) -> None:
        """Serves on `sock`, which `bind` returned; returns when the server stops."""
        ...


@runtime_checkable
class LocalNamesInterface(Protocol):
    """The names a LAN device may send in `Host` to reach this computer."""

    def names(self, bound: str) -> frozenset[str]:
        """This computer's host name, its `.local` name, its addresses, and `bound`."""
        ...
