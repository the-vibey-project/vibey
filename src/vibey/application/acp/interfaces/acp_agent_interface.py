# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/application/acp/acp_agent.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface


@runtime_checkable
class AcpAgentInterface(Protocol):
    """The ACP agent: the JSON-RPC peer's request and notification handlers."""

    @property
    def sessions(self) -> Mapping[str, AcpSessionStateInterface]:
        """Every session this process holds, by id."""
        ...

    async def handle_request(self, method: str, params: Mapping[str, Any]) -> Mapping[str, Any]:
        """Answer one request; `RpcError` chooses a JSON-RPC error reply."""
        ...

    async def handle_notification(self, method: str, params: Mapping[str, Any]) -> None:
        """Act on one notification (`session/cancel`); an unknown one is ignored."""
        ...

    async def close(self) -> None:
        """Stop what runs beside the requests (live feeds, post-response updates) and wait for
        it to end; called once the connection is over."""
        ...
