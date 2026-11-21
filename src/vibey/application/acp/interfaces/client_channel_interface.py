# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ACP agent's way back to the client: session updates and permission requests (SP-ACP).

Implemented by `infrastructure/acp/peer_client_channel.py` over the JSON-RPC peer.
Interfaces declare; they never consume.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ClientChannelInterface(Protocol):
    client_capabilities: Mapping[str, Any]
    """What the client advertised in `initialize` (`clientCapabilities`); `{}` before then."""

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        """Send one `session/update` notification carrying `update` for `session_id`."""
        ...

    async def request_permission(
        self,
        session_id: str,
        tool_call: Mapping[str, Any],
        options: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> str | None:
        """Ask the client with `session/request_permission`; the selected `optionId`, or None
        when the client answered `cancelled`, did not answer within `timeout`, or failed."""
        ...
