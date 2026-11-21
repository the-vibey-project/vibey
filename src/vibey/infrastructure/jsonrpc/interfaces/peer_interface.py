# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for a bidirectional line-delimited JSON-RPC 2.0 peer."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any, Protocol, runtime_checkable

RequestHandler = Callable[[str, Mapping[str, Any]], Awaitable[Mapping[str, Any]]]
NotificationHandler = Callable[[str, Mapping[str, Any]], Awaitable[None]]


@runtime_checkable
class JsonRpcPeerInterface(Protocol):
    async def run(self) -> None:
        """Serve inbound messages until EOF, then fail pending requests and stop the handlers."""
        ...

    async def request(
        self, method: str, params: Mapping[str, Any], *, timeout: float | None = None
    ) -> Mapping[str, Any]:
        """Send a request and await its result; raises RpcError, PeerClosed, PeerCancelled or TimeoutError."""
        ...

    async def notify(self, method: str, params: Mapping[str, Any]) -> None:
        """Send a notification, which never receives a reply."""
        ...

    def cancel_outbound(
        self, predicate: Callable[[str, Mapping[str, Any]], bool]
    ) -> tuple[str, ...]:
        """Resolve matching pending outbound requests with PeerCancelled; return their ids."""
        ...
