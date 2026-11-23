# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind running the hub and naming this computer.

Mirrors `vibey/infrastructure/hub/server.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Sequence
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

    def bind(self, host: str, port: int) -> list[socket.socket]:
        """A socket bound and already listening for every address `host` resolves to, all on
        one port (port 0: the one the system picks for the first). Raises `OSError` when any
        address cannot be had; nothing is left open then."""
        ...

    async def serve(
        self, app: FastAPI, *, sockets: Sequence[socket.socket], tls: HubTls | None = None
    ) -> None:
        """Serves on `sockets`; returns when the server stops. The server closes them as it
        stops, before it waits for open connections: the caller hands it duplicates and keeps
        its own until it has cleared its record."""
        ...


@runtime_checkable
class LocalNamesInterface(Protocol):
    """The names a LAN device may send in `Host` to reach this computer."""

    def names(self, bound: str) -> frozenset[str]:
        """This computer's host name, its `.local` name, its addresses, and `bound`."""
        ...
