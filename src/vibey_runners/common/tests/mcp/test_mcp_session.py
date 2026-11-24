# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One MCP session over the shared JSON-RPC peer (SP-LOOPS Phase 5, Task 3; R5, R6, R15).

Every server here is an in-memory script (`mcp_fakes.MemoryTransport`): no process, no network.
The only real wait is the 0.01s request timeout of the test that proves a silent server is
given up on. Module-level test functions rather than a class with an interface beside it
(ADR-0016).
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest
from mcp_fakes import MemoryTransport, initialize_with, standard

from vibey_runners.common.jsonrpc.errors import METHOD_NOT_FOUND
from vibey_runners.common.mcp.interfaces.mcp_session_interface import McpSessionInterface
from vibey_runners.common.mcp.interfaces.mcp_transport_interface import McpTransportInterface
from vibey_runners.common.mcp.mcp_call_result import McpCallResult
from vibey_runners.common.mcp.mcp_errors import McpToolError, McpUnavailable
from vibey_runners.common.mcp.mcp_session import McpSession
from vibey_runners.common.mcp.mcp_tool import McpTool
from vibey_runners.common.mcp.protocol import LATEST_PROTOCOL, SUPPORTED_PROTOCOLS


def _session(transport: MemoryTransport, **options: Any) -> McpSession:
    settings: dict[str, Any] = {
        "client_name": "qwenloop",
        "client_version": "9.9.9",
        "timeout_seconds": 5.0,
        **options,
    }
    return McpSession(transport, **settings)


async def _started(transport: MemoryTransport, **options: Any) -> McpSession:
    session = _session(transport, **options)
    await session.start()
    return session


def test_the_protocol_versions_are_the_ones_vibeys_server_answers() -> None:
    assert SUPPORTED_PROTOCOLS == ("2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25")
    assert SUPPORTED_PROTOCOLS[-1] == LATEST_PROTOCOL


@pytest.mark.parametrize("answered", SUPPORTED_PROTOCOLS)
async def test_start_offers_the_latest_protocol_and_accepts_an_older_supported_one(
    answered: str,
) -> None:
    transport = MemoryTransport(initialize_with(answered))
    session = await _started(transport)
    assert isinstance(session, McpSessionInterface)
    assert isinstance(transport, McpTransportInterface)
    assert session.alive
    initialize = transport.sent[0]
    assert initialize["method"] == "initialize"
    assert initialize["params"] == {
        "protocolVersion": LATEST_PROTOCOL,
        "capabilities": {},
        "clientInfo": {"name": "qwenloop", "version": "9.9.9"},
    }
    assert transport.sent[1] == {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {},
    }
    await session.close(0.5)


@pytest.mark.parametrize("answered", ["1999-01-01", None, 20251125, {"v": 1}])
async def test_an_unknown_protocol_version_is_unavailable_and_named(answered: object) -> None:
    transport = MemoryTransport(initialize_with(answered))
    session = _session(transport)
    with pytest.raises(McpUnavailable) as caught:
        await session.start()
    message = str(caught.value)
    assert message.startswith("MCP server 'mem' (memory) answered protocol version")
    assert repr(answered) in message
    assert LATEST_PROTOCOL in message
    assert not session.alive
    assert transport.closed == [0.0]
    assert "notifications/initialized" not in transport.methods()


async def test_a_transport_that_cannot_open_is_unavailable() -> None:
    transport = MemoryTransport(refuse_open=FileNotFoundError(2, "No such file"))
    session = _session(transport)
    with pytest.raises(McpUnavailable, match=r"^MCP server 'mem' \(memory\) could not start: "):
        await session.start()
    assert not session.alive
    assert transport.closed == []


async def test_an_initialize_answered_with_an_error_is_unavailable() -> None:
    def refuse(message: dict[str, Any], server: MemoryTransport) -> None:
        server.fail(message, -32602, "bad params")

    transport = MemoryTransport(refuse)
    session = _session(transport)
    with pytest.raises(McpUnavailable, match="refused initialize: .*bad params"):
        await session.start()
    assert not session.alive
    assert transport.closed == [0.0]


async def test_a_server_whose_input_breaks_after_initialize_is_unavailable() -> None:
    def breaks(message: dict[str, Any], server: MemoryTransport) -> None:
        standard(message, server)
        server.refuse_write = BrokenPipeError(32, "Broken pipe")

    transport = MemoryTransport(breaks)
    session = _session(transport)
    with pytest.raises(McpUnavailable, match="could not be written to: BrokenPipeError"):
        await session.start()
    assert not session.alive


async def test_a_request_that_cannot_be_written_kills_the_session() -> None:
    transport = MemoryTransport()
    session = await _started(transport)
    transport.refuse_write = ConnectionResetError(54, "Connection reset by peer")
    with pytest.raises(McpUnavailable) as caught:
        await session.call("echo", {})
    assert str(caught.value) == (
        "MCP server 'mem' (memory) could not be written to: ConnectionResetError"
    )
    assert not session.alive
    assert transport.closed == [0.0]


async def test_a_transport_that_refuses_a_request_ends_the_session_with_its_message() -> None:
    # The HTTP transport refuses a status, a redirect or an oversize reply from its writer, and
    # its message already names the server: the session ends and passes the message on.
    transport = MemoryTransport()
    session = await _started(transport)
    transport.refuse_write = McpUnavailable("MCP server 'mem' (https h.test) answered HTTP 500")
    with pytest.raises(McpUnavailable) as caught:
        await session.call("echo", {})
    assert str(caught.value) == "MCP server 'mem' (https h.test) answered HTTP 500"
    assert not session.alive
    assert transport.closed == [0.0]
    with pytest.raises(McpUnavailable, match="is not running"):
        await session.list_tools()


async def test_a_transport_that_refuses_the_initialized_notification_ends_the_session() -> None:
    def refuses_the_notification(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "notifications/initialized":
            raise McpUnavailable("MCP server 'mem' (https h.test) answered HTTP 403")
        standard(message, server)

    transport = MemoryTransport(refuses_the_notification)
    session = _session(transport)
    with pytest.raises(McpUnavailable, match=r"answered HTTP 403$"):
        await session.start()
    assert not session.alive
    assert transport.closed == [0.0]


async def test_list_tools_follows_next_cursor_and_stops_at_max_tools() -> None:
    pages: dict[object, dict[str, Any]] = {
        None: {
            "tools": [
                {"name": "a", "description": "A.", "inputSchema": {"type": "object"}},
                7,
                {"description": "no name"},
            ],
            "nextCursor": "p2",
        },
        "p2": {
            "tools": [
                {"name": "b", "description": 9, "inputSchema": ["not", "a", "map"]},
                {"name": "c"},
            ],
            "nextCursor": "p3",
        },
        "p3": {"tools": [{"name": "d"}, {"name": "e"}, {"name": "f"}], "nextCursor": "p4"},
        "p4": {"tools": [{"name": "never"}]},
    }

    def paged(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/list":
            server.reply(message, pages[(message.get("params") or {}).get("cursor")])
        else:
            standard(message, server)

    transport = MemoryTransport(paged)
    session = await _started(transport, max_tools=4)
    tools = await session.list_tools()
    assert tools == (
        McpTool("a", "A.", {"type": "object"}),
        McpTool("b", "", {}),
        McpTool("c", "", {}),
        McpTool("d", "", {}),
    )
    cursors = [m["params"] for m in transport.sent if m.get("method") == "tools/list"]
    assert cursors == [{}, {"cursor": "p2"}, {"cursor": "p3"}]
    again = await session.list_tools()
    assert again is tools
    assert transport.methods().count("tools/list") == 3


@pytest.mark.parametrize(
    "page",
    [{}, {"tools": "not a list"}, {"tools": [], "nextCursor": ""}, {"tools": [], "nextCursor": 3}],
)
async def test_a_page_without_tools_or_a_cursor_ends_the_listing(page: dict[str, Any]) -> None:
    def single(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/list":
            server.reply(message, page)
        else:
            standard(message, server)

    transport = MemoryTransport(single)
    session = await _started(transport)
    assert await session.list_tools() == ()
    assert transport.methods().count("tools/list") == 1


async def test_a_server_that_pages_forever_is_asked_at_most_max_tools_times() -> None:
    counter = iter(range(1_000_000))

    def endless(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/list":
            server.reply(message, {"tools": [], "nextCursor": f"c{next(counter)}"})
        else:
            standard(message, server)

    transport = MemoryTransport(endless)
    session = await _started(transport, max_tools=3)
    assert await session.list_tools() == ()
    assert transport.methods().count("tools/list") == 3


async def test_a_tools_list_changed_notification_drops_the_cache() -> None:
    transport = MemoryTransport()
    session = await _started(transport)
    first = await session.list_tools()
    assert await session.list_tools() is first
    transport.send({"method": "notifications/message", "params": {"level": "info"}})
    assert await _answered_ping(transport) == {}
    assert await session.list_tools() is first
    transport.send({"method": "notifications/tools/list_changed", "params": {}})
    # The peer starts one task per message in arrival order, so once the ping that follows the
    # notification is answered, the notification has been handled.
    assert await _answered_ping(transport) == {}
    second = await session.list_tools()
    assert second == first
    assert second is not first
    assert transport.methods().count("tools/list") == 2


async def test_a_server_ping_is_answered_and_other_server_requests_are_refused() -> None:
    def asks(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/call":
            server.pending = message  # type: ignore[attr-defined]
            server.send({"id": "s-1", "method": "ping"})
            server.send({"id": "s-2", "method": "sampling/createMessage", "params": {}})
        elif message.get("id") in {"s-1", "s-2"}:
            answers = [m for m in server.sent if m.get("id") in {"s-1", "s-2"}]
            if len(answers) == 2:
                server.reply(server.pending, {"content": []})  # type: ignore[attr-defined]
        else:
            standard(message, server)

    transport = MemoryTransport(asks)
    session = await _started(transport)
    assert await session.call("echo", {}) == McpCallResult("", False)
    answers = {m["id"]: m for m in transport.sent if m.get("id") in {"s-1", "s-2"}}
    assert answers["s-1"]["result"] == {}
    assert answers["s-2"]["error"]["code"] == METHOD_NOT_FOUND
    assert "sampling/createMessage" in answers["s-2"]["error"]["message"]


async def test_a_jsonrpc_error_answer_is_a_tool_error_and_the_session_stays_alive() -> None:
    def explodes(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/call" and message["params"]["name"] == "boom":
            server.fail(message, -32000, "exploded")
        else:
            standard(message, server)

    transport = MemoryTransport(explodes)
    session = await _started(transport)
    with pytest.raises(McpToolError) as caught:
        await session.call("boom", {"x": 1})
    assert str(caught.value) == (
        "MCP server 'mem' (memory) answered tools/call with error -32000: exploded"
    )
    assert session.alive
    assert transport.closed == []
    assert await session.call("echo", {"x": 1}) == McpCallResult('{"x": 1}', False)


async def test_a_call_joins_the_text_parts_and_carries_is_error() -> None:
    def mixed(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/call":
            content = [
                {"type": "text", "text": "one"},
                {"type": "image", "data": "..."},
                3,
                {"type": "text", "text": "two"},
                {"type": "text"},
            ]
            server.reply(message, {"content": content, "isError": True})
        else:
            standard(message, server)

    transport = MemoryTransport(mixed)
    session = await _started(transport)
    assert await session.call("echo", {"a": [1]}) == McpCallResult("one\ntwo\n", True)
    call = [m for m in transport.sent if m.get("method") == "tools/call"][0]
    assert call["params"] == {"name": "echo", "arguments": {"a": [1]}}


@pytest.mark.parametrize("result", [{"content": "text"}, {"isError": "yes"}, {}])
async def test_a_malformed_call_result_is_empty_text_and_not_an_error(
    result: dict[str, Any],
) -> None:
    def odd(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/call":
            server.reply(message, result)
        else:
            standard(message, server)

    session = await _started(MemoryTransport(odd))
    assert await session.call("echo", {}) == McpCallResult("", False)


async def test_a_server_that_never_answers_times_out_and_the_session_is_dead() -> None:
    def silent(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "initialize":
            standard(message, server)

    transport = MemoryTransport(silent)
    session = await _started(transport, timeout_seconds=0.01)
    with pytest.raises(McpUnavailable) as caught:
        await session.list_tools()
    assert str(caught.value) == "MCP server 'mem' (memory) did not answer tools/list within 0.01s"
    assert not session.alive
    assert transport.closed == [0.0]
    sent = len(transport.sent)
    with pytest.raises(McpUnavailable, match=r"^MCP server 'mem' \(memory\) is not running$"):
        await session.call("echo", {})
    assert len(transport.sent) == sent


async def test_a_server_that_closes_its_stream_mid_call_is_dead() -> None:
    def hangs_up(message: dict[str, Any], server: MemoryTransport) -> None:
        if message.get("method") == "tools/call":
            server.reader.feed_eof()
        else:
            standard(message, server)

    transport = MemoryTransport(hangs_up)
    session = await _started(transport)
    with pytest.raises(McpUnavailable, match=r"closed its stream during tools/call$"):
        await session.call("echo", {})
    assert not session.alive
    assert transport.closed == [0.0]


async def test_close_closes_the_transport_with_its_grace_and_is_idempotent() -> None:
    transport = MemoryTransport()
    session = await _started(transport)
    await session.close(2.5)
    assert not session.alive
    assert transport.closed == [2.5]
    await session.close(2.5)
    assert transport.closed == [2.5, 2.5]
    with pytest.raises(McpUnavailable, match="is not running"):
        await session.list_tools()


async def test_a_session_never_started_is_not_running_and_closes_quietly() -> None:
    transport = MemoryTransport()
    session = _session(transport)
    assert not session.alive
    with pytest.raises(McpUnavailable, match="is not running"):
        await session.call("echo", {})
    await session.close(1.0)
    assert transport.closed == [1.0]
    assert transport.sent == []


async def _answered_ping(transport: MemoryTransport, spins: int = 500) -> object:
    """Send a server ping and yield to the loop until the client's answer to it is written."""
    ping_id = f"ping-{len(transport.sent)}"
    transport.send({"id": ping_id, "method": "ping"})
    for _ in range(spins):
        for message in transport.sent:
            if message.get("id") == ping_id:
                return message.get("result")
        await asyncio.sleep(0)
    raise AssertionError("the ping was never answered")
