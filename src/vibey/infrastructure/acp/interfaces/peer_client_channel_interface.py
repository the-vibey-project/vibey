# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/infrastructure/acp/peer_client_channel.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from vibey_runners.common.jsonrpc.interfaces.peer_interface import JsonRpcPeerInterface

from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface


@runtime_checkable
class PeerClientChannelInterface(ClientChannelInterface, Protocol):
    """The application's client channel over the JSON-RPC peer, which is made after it: the
    peer needs the agent's handlers and the agent needs this channel (SP-ACP Task 3, B-9)."""

    def attach(self, peer: JsonRpcPeerInterface) -> None:
        """Send everything from now on over `peer`; before it, every send is refused."""
        ...
