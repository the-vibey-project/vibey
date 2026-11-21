# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's way back to the client, over the shared JSON-RPC peer (SP-ACP).

The peer needs the agent's handlers and the agent needs this channel, so the channel is made
first and `attach`ed to the peer once both exist. A permission request that the client cancels,
fails or never answers within its timeout is `None`: the caller treats it as no answer, so an
open gate stays open (silence is not consent, sub-doctrine 12.d).

Declared by `application/acp/interfaces/client_channel_interface.py::ClientChannelInterface`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from vibey.domain.acp.protocol import REQUEST_PERMISSION, SESSION_UPDATE
from vibey.infrastructure.jsonrpc.errors import PeerCancelled, PeerClosed, RpcError
from vibey.infrastructure.jsonrpc.interfaces.peer_interface import JsonRpcPeerInterface


class PeerClientChannel:
    """Declared by `application/acp/interfaces/client_channel_interface.py`."""

    def __init__(self) -> None:
        self.client_capabilities: Mapping[str, Any] = {}
        self._peer: JsonRpcPeerInterface | None = None

    def attach(self, peer: JsonRpcPeerInterface) -> None:
        self._peer = peer

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        await self._attached().notify(
            SESSION_UPDATE, {"sessionId": session_id, "update": dict(update)}
        )

    async def request_permission(
        self,
        session_id: str,
        tool_call: Mapping[str, Any],
        options: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> str | None:
        params = {
            "sessionId": session_id,
            "toolCall": dict(tool_call),
            "options": [dict(option) for option in options],
        }
        try:
            result = await self._attached().request(REQUEST_PERMISSION, params, timeout=timeout)
        except (RpcError, PeerClosed, PeerCancelled, TimeoutError):
            return None
        outcome = result.get("outcome")
        if not isinstance(outcome, Mapping) or outcome.get("outcome") != "selected":
            return None
        option_id = outcome.get("optionId")
        return option_id if isinstance(option_id, str) else None

    def cancel_permissions(self, session_id: str) -> tuple[str, ...]:
        # The protocol asks the client to answer `cancelled` after a `session/cancel`, but a
        # client that never does must not hold the turn, so the requests resolve here.
        return self._attached().cancel_outbound(
            lambda method, params: (
                method == REQUEST_PERMISSION and params.get("sessionId") == session_id
            )
        )

    def _attached(self) -> JsonRpcPeerInterface:
        if self._peer is None:
            raise RuntimeError("the ACP client channel is not attached to a peer yet")
        return self._peer
