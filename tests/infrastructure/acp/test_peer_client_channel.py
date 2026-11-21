# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`PeerClientChannel`: session updates and permission requests over the JSON-RPC peer.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

import pytest
from acp.schema import RequestPermissionRequest, SessionNotification

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.infrastructure.acp.peer_client_channel import PeerClientChannel
from vibey.infrastructure.jsonrpc.errors import PeerCancelled, PeerClosed, RpcError

TOOL_CALL = {"toolCallId": "t1-1", "title": "Answer a gate", "kind": "other", "status": "pending"}
OPTIONS = [
    {"optionId": "approve", "name": "Approve", "kind": "allow_once"},
    {"optionId": "reject", "name": "Reject", "kind": "reject_once"},
]


class _Peer:
    """Records what the channel sends and answers requests with a scripted outcome."""

    def __init__(self, reply: Mapping[str, Any] | None = None, error: Exception | None = None):
        self.reply = reply or {}
        self.error = error
        self.notes: list[tuple[str, dict[str, Any]]] = []
        self.requests: list[tuple[str, dict[str, Any], float | None]] = []

    async def run(self) -> None:
        return None

    async def request(
        self, method: str, params: Mapping[str, Any], *, timeout: float | None = None
    ) -> Mapping[str, Any]:
        self.requests.append((method, dict(params), timeout))
        if self.error is not None:
            raise self.error
        return self.reply

    async def notify(self, method: str, params: Mapping[str, Any]) -> None:
        self.notes.append((method, dict(params)))

    def cancel_outbound(
        self, predicate: Callable[[str, Mapping[str, Any]], bool]
    ) -> tuple[str, ...]:
        return ()


def _attached(peer: _Peer) -> PeerClientChannel:
    channel = PeerClientChannel()
    channel.attach(peer)
    return channel


def test_the_channel_satisfies_the_application_port() -> None:
    channel = PeerClientChannel()
    assert isinstance(channel, ClientChannelInterface)
    assert channel.client_capabilities == {}


async def test_an_unattached_channel_refuses_to_send() -> None:
    with pytest.raises(RuntimeError, match="not attached"):
        await PeerClientChannel().notify_update("s", {"sessionUpdate": "agent_message_chunk"})


async def test_notify_update_sends_a_session_update_notification() -> None:
    peer = _Peer()
    update = {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": "hi"}}

    await _attached(peer).notify_update("s", update)

    assert peer.notes == [("session/update", {"sessionId": "s", "update": update})]
    assert_wire_exact(SessionNotification, peer.notes[0][1])


async def test_a_selected_option_is_returned_with_the_request_well_formed() -> None:
    peer = _Peer({"outcome": {"outcome": "selected", "optionId": "approve"}})

    chosen = await _attached(peer).request_permission("s", TOOL_CALL, OPTIONS, timeout=42.0)

    assert chosen == "approve"
    method, params, timeout = peer.requests[0]
    assert method == "session/request_permission"
    assert timeout == 42.0
    assert params == {"sessionId": "s", "toolCall": TOOL_CALL, "options": OPTIONS}
    assert_wire_exact(RequestPermissionRequest, params)


@pytest.mark.parametrize(
    "reply",
    [
        {"outcome": {"outcome": "cancelled"}},
        {"outcome": {"outcome": "selected"}},
        {"outcome": {"outcome": "selected", "optionId": 3}},
        {"outcome": "selected"},
        {},
    ],
)
async def test_anything_but_a_selected_option_is_none(reply: Mapping[str, Any]) -> None:
    assert (
        await _attached(_Peer(reply)).request_permission("s", TOOL_CALL, OPTIONS, timeout=1) is None
    )


@pytest.mark.parametrize(
    "error",
    [RpcError(-32603, "client crashed"), PeerClosed("eof"), PeerCancelled("x"), TimeoutError()],
)
async def test_a_client_error_timeout_or_closed_peer_is_none(error: Exception) -> None:
    channel = _attached(_Peer(error=error))

    assert await channel.request_permission("s", TOOL_CALL, OPTIONS, timeout=1) is None
