# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpHubClient`: the ACP agent's port onto the hub, over the MCP `HubGateway` (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import json
import logging
import threading
from typing import Any
from uuid import UUID

import pytest

from vibey.application.acp.dto import HubToolResult, HubTurn, LedgerPage
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.domain.acp.session_log import (
    SESSION_PAGE,
    AcpSessionLimitReached,
    InvalidSessionCursor,
    SessionEventConflict,
    UnknownAcpSession,
)
from vibey.domain.errors import VibeyError
from vibey.domain.host_tools import HostToolError, HubCall
from vibey.domain.hub_scope import HubScope
from vibey.infrastructure.acp.acp_hub_client import AcpHubClient
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError, HubGatewayResponse

PROJECT = UUID("7d6c2a8e-0c41-4c1e-9d0e-2f4b8f0a1b2c")


class _Gateway:
    """Answers each call with the next scripted response, recording the call and its thread."""

    def __init__(self, *responses: HubGatewayResponse | Exception) -> None:
        self._responses = list(responses)
        self.calls: list[HubCall] = []
        self.threads: list[int] = []

    def agent_scopes(self) -> frozenset[HubScope]:
        return frozenset({HubScope.VIEW})

    def call(self, call: HubCall) -> HubGatewayResponse:
        self.calls.append(call)
        self.threads.append(threading.get_ident())
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _ok(document: Any, status: int = 200) -> HubGatewayResponse:
    return HubGatewayResponse(status_code=status, text=json.dumps(document), ok=status < 400)


def test_the_client_satisfies_the_application_port() -> None:
    assert isinstance(AcpHubClient(gateway=_Gateway()), AcpHubPortInterface)


async def test_chat_posts_the_message_and_parses_the_turn_off_the_event_loop() -> None:
    gateway = _Gateway(
        _ok(
            {
                "reply": "1 project(s)",
                "tool_calls": [{"name": "vibey_projects", "result": []}, "junk"],
                "gates": [{"gate_id": "g", "kind": "approval"}, 3],
                "project_id": str(PROJECT),
            }
        )
    )

    turn = await AcpHubClient(gateway=gateway).chat(
        "/projects", project_id=PROJECT, request_id="acp-s-t1"
    )

    assert gateway.calls == [
        HubCall(
            tool="vibey_chat",
            method="POST",
            route="/api/v1/chat/messages",
            body={"message": "/projects", "project_id": str(PROJECT), "request_id": "acp-s-t1"},
        )
    ]
    assert gateway.threads[0] != threading.get_ident()
    assert turn == HubTurn(
        reply="1 project(s)",
        tool_calls=({"name": "vibey_projects", "result": []},),
        gates=({"gate_id": "g", "kind": "approval"},),
        project_id=PROJECT,
    )


async def test_chat_without_a_project_sends_null_and_tolerates_missing_members() -> None:
    gateway = _Gateway(_ok({"reply": 5, "tool_calls": "x", "project_id": None}))

    turn = await AcpHubClient(gateway=gateway).chat("/projects", project_id=None, request_id="r")

    body = gateway.calls[0].body
    assert body is not None and body["project_id"] is None
    assert turn == HubTurn(reply="5", tool_calls=(), gates=(), project_id=None)


async def test_a_refused_chat_raises_naming_the_status() -> None:
    gateway = _Gateway(HubGatewayResponse(status_code=403, text="forbidden", ok=False))

    with pytest.raises(HubGatewayError, match=r"hub refused \(403\): forbidden"):
        await AcpHubClient(gateway=gateway).chat("/start", project_id=None, request_id="r")


@pytest.mark.parametrize("text", ["not json", "[1, 2]", '{"project_id": "not-a-uuid"}'])
async def test_a_chat_answer_that_is_not_a_turn_raises(text: str) -> None:
    gateway = _Gateway(HubGatewayResponse(status_code=200, text=text, ok=True))

    with pytest.raises(HubGatewayError, match="not a chat turn"):
        await AcpHubClient(gateway=gateway).chat("/projects", project_id=None, request_id="r")


async def test_an_unreachable_hub_surfaces_as_a_vibey_error() -> None:
    gateway = _Gateway(HubGatewayError("no hub is running"))

    with pytest.raises(VibeyError, match="no hub is running"):
        await AcpHubClient(gateway=gateway).chat("/projects", project_id=None, request_id="r")


async def test_call_tool_builds_the_call_from_the_catalogue() -> None:
    gateway = _Gateway(HubGatewayResponse(status_code=200, text='{"ok": true}', ok=True))

    result = await AcpHubClient(gateway=gateway).call_tool(
        "vibey_status", {"project_id": str(PROJECT)}, request_id="r"
    )

    assert result == HubToolResult(ok=True, status_code=200, text='{"ok": true}')
    assert gateway.calls[0].route == f"/api/v1/projects/{PROJECT}/status"


async def test_call_tool_reports_a_refusal_without_raising() -> None:
    gateway = _Gateway(HubGatewayResponse(status_code=403, text="no", ok=False))

    result = await AcpHubClient(gateway=gateway).call_tool("vibey_projects", {}, request_id="r")

    assert result == HubToolResult(ok=False, status_code=403, text="no")


async def test_call_tool_refuses_bad_arguments_before_any_call() -> None:
    gateway = _Gateway()

    with pytest.raises(HostToolError):
        await AcpHubClient(gateway=gateway).call_tool(
            "vibey_status", {"project_id": "nope"}, request_id="r"
        )

    assert gateway.calls == []


async def test_ledger_after_pages_the_live_feed() -> None:
    gateway = _Gateway(_ok({"events": [{"seq": 4}, {"seq": 5}, "junk"], "last_seq": 5}))

    page = await AcpHubClient(gateway=gateway).ledger_after(PROJECT, 3, 50)

    assert page == LedgerPage(events=({"seq": 4}, {"seq": 5}), last_seq=5)
    assert gateway.calls[0] == HubCall(
        tool="vibey_ledger_after",
        method="GET",
        route=f"/api/v1/projects/{PROJECT}/ledger/after",
        query=(("seq", "3"), ("limit", "50")),
    )


@pytest.mark.parametrize("last_seq", [None, "5", True])
async def test_ledger_after_without_an_integer_last_seq_is_none(last_seq: object) -> None:
    gateway = _Gateway(_ok({"events": [], "last_seq": last_seq}))

    page = await AcpHubClient(gateway=gateway).ledger_after(PROJECT, 0, 10)

    assert page == LedgerPage(events=(), last_seq=None)


async def test_a_refused_ledger_page_raises() -> None:
    gateway = _Gateway(HubGatewayResponse(status_code=404, text="no project", ok=False))

    with pytest.raises(HubGatewayError, match=r"hub refused \(404\)"):
        await AcpHubClient(gateway=gateway).ledger_after(PROJECT, 0, 10)


async def test_healthy_is_the_liveness_route() -> None:
    gateway = _Gateway(
        HubGatewayResponse(status_code=200, text="{}", ok=True),
        HubGatewayResponse(status_code=503, text="", ok=False),
        HubGatewayError("no hub"),
    )
    client = AcpHubClient(gateway=gateway)

    assert [await client.healthy(), await client.healthy(), await client.healthy()] == [
        True,
        False,
        False,
    ]
    assert gateway.calls[0] == HubCall(tool="vibey_health", method="GET", route="/health/live")


def test_agent_scopes_are_the_gateways() -> None:
    assert AcpHubClient(gateway=_Gateway()).agent_scopes() == frozenset({HubScope.VIEW})


async def test_an_os_failure_reaching_the_hub_surfaces_as_a_vibey_error() -> None:
    error = OSError("read-only state dir")
    client = AcpHubClient(gateway=_Gateway(error, error, error))

    with pytest.raises(HubGatewayError, match="could not be reached") as caught:
        await client.chat("/projects", project_id=None, request_id="r")

    assert caught.value.__cause__ is error
    with pytest.raises(HubGatewayError, match="could not be reached"):
        await client.ledger_after(PROJECT, 0, 10)
    assert await client.healthy() is False


@pytest.mark.parametrize(
    "error", [TypeError("bad call"), KeyError("missing"), RuntimeError("shut down")]
)
async def test_a_defect_is_not_reported_as_an_unreachable_hub(error: Exception) -> None:
    # Only a transport failure is "the hub could not be reached": a bug reaches the caller as
    # itself, so the peer logs it with its traceback instead of a misleading message.
    client = AcpHubClient(gateway=_Gateway(error, error))

    with pytest.raises(type(error)) as caught:
        await client.chat("/projects", project_id=None, request_id="r")
    assert caught.value is error
    with pytest.raises(type(error)):
        await client.call_tool("vibey_projects", {}, request_id="r")


async def test_healthy_never_raises_and_logs_a_defect_with_its_traceback(
    caplog: pytest.LogCaptureFixture,
) -> None:
    client = AcpHubClient(gateway=_Gateway(TypeError("bad call")))

    with caplog.at_level(logging.ERROR):
        assert await client.healthy() is False

    assert "bad call" in caplog.text and "Traceback" in caplog.text


# -- an ACP session's log -------------------------------------------------------------------

SID = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a01"


async def test_create_session_posts_the_id_and_folder() -> None:
    gateway = _Gateway(_ok({"session_id": SID}, 201))
    await AcpHubClient(gateway=gateway).create_session(SID, "/work")
    assert gateway.calls == [
        HubCall(
            tool="vibey_acp_session",
            method="POST",
            route="/api/v1/acp/sessions",
            body={"session_id": SID, "cwd": "/work"},
        )
    ]


async def test_append_event_posts_one_event() -> None:
    gateway = _Gateway(_ok({"stored": True}))
    await AcpHubClient(gateway=gateway).append_event(SID, 3, "plan", {"entries": []})
    assert gateway.calls[0].route == f"/api/v1/acp/sessions/{SID}/events"
    assert gateway.calls[0].body == {"seq": 3, "kind": "plan", "payload": {"entries": []}}


@pytest.mark.parametrize(
    ("status", "error"),
    [
        (403, UnknownAcpSession),
        (404, UnknownAcpSession),
        (409, SessionEventConflict),
        (507, AcpSessionLimitReached),
        (500, HubGatewayError),
    ],
)
async def test_a_refused_session_write_says_why(status: int, error: type[Exception]) -> None:
    gateway = _Gateway(_ok({"detail": "no"}, status), _ok({"detail": "no"}, status))
    client = AcpHubClient(gateway=gateway)
    with pytest.raises(error):
        await client.append_event(SID, 1, "plan", {})
    with pytest.raises(error):
        await client.create_session(SID, "/work")


@pytest.mark.parametrize("session_id", ["s", "../x", SID.upper(), f"{SID}/../../gates"])
async def test_only_an_id_vibey_mints_is_put_in_a_route(session_id: str) -> None:
    gateway = _Gateway()
    client = AcpHubClient(gateway=gateway)
    with pytest.raises(UnknownAcpSession):
        await client.append_event(session_id, 1, "plan", {})
    with pytest.raises(UnknownAcpSession):
        await client.session_events(session_id, 0, cwd="/work")
    assert gateway.calls == []


def _page(first: int, count: int) -> dict[str, Any]:
    events = [{"seq": n, "kind": "plan", "payload": {}} for n in range(first, first + count)]
    return {"events": events, "last_seq": first + count - 1 if count else None}


async def test_session_events_pages_until_a_short_page() -> None:
    gateway = _Gateway(_ok(_page(1, SESSION_PAGE)), _ok(_page(SESSION_PAGE + 1, 2)))
    events = await AcpHubClient(gateway=gateway).session_events(SID, 0, cwd="/work dir")
    assert [event.seq for event in events] == list(range(1, SESSION_PAGE + 3))
    assert [call.query for call in gateway.calls] == [
        (("after", "0"), ("limit", str(SESSION_PAGE)), ("cwd", "/work dir")),
        (("after", str(SESSION_PAGE)), ("limit", str(SESSION_PAGE)), ("cwd", "/work dir")),
    ]


async def test_session_events_passes_over_what_is_not_an_event_after_the_cursor() -> None:
    page = {
        "events": [
            {"seq": 1, "kind": "plan", "payload": {}},  # not after the cursor
            {"seq": True, "kind": "plan", "payload": {}},
            {"seq": 6, "kind": 3, "payload": {}},
            {"seq": 7, "kind": "plan", "payload": []},
            {"seq": 8, "kind": "plan", "payload": {"entries": []}},
            "junk",
        ]
    }
    events = await AcpHubClient(gateway=_Gateway(_ok(page))).session_events(SID, 5, cwd="/w")
    assert [(e.seq, dict(e.payload)) for e in events] == [(8, {"entries": []})]


@pytest.mark.parametrize("status", [403, 404])
async def test_a_session_the_hub_does_not_keep_is_unknown(status: int) -> None:
    gateway = _Gateway(_ok({"detail": "no session"}, status))
    with pytest.raises(UnknownAcpSession):
        await AcpHubClient(gateway=gateway).session_events(SID, 0, cwd="/work")


async def test_list_sessions_reads_a_page_and_its_cursor() -> None:
    stamp = "2026-11-21T12:00:00+00:00"
    document = {
        "sessions": [
            {"session_id": SID, "cwd": "/w", "title": "t", "updated_at": stamp, "closed": True},
            {"session_id": SID, "cwd": "/w", "title": None, "updated_at": stamp, "closed": 1},
            {"session_id": 3, "cwd": "/w", "updated_at": stamp},
            {"session_id": SID, "cwd": "/w", "title": 4, "updated_at": stamp},
            {"session_id": SID, "cwd": "/w", "updated_at": "yesterday"},
            {"session_id": SID, "cwd": "/w"},
        ],
        "next_cursor": "abc",
    }
    gateway = _Gateway(_ok(document))
    records, cursor = await AcpHubClient(gateway=gateway).list_sessions(cwd="/w", cursor="x")
    assert gateway.calls[0].query == (("limit", str(SESSION_PAGE)), ("cwd", "/w"), ("cursor", "x"))
    assert [(r.title, r.closed) for r in records] == [("t", True), (None, False)]
    assert records[0].updated_at.isoformat() == stamp
    assert cursor == "abc"


async def test_the_last_list_page_has_no_cursor() -> None:
    gateway = _Gateway(_ok({"sessions": [], "next_cursor": None}))
    assert await AcpHubClient(gateway=gateway).list_sessions(cwd=None, cursor=None) == ((), None)
    assert gateway.calls[0].query == (("limit", str(SESSION_PAGE)),)


async def test_a_cursor_the_hub_refuses_is_an_invalid_cursor() -> None:
    gateway = _Gateway(_ok({"detail": "bad"}, 422), _ok({"detail": "bad"}, 422))
    client = AcpHubClient(gateway=gateway)
    with pytest.raises(InvalidSessionCursor):
        await client.list_sessions(cwd=None, cursor="nope")
    with pytest.raises(HubGatewayError):
        await client.list_sessions(cwd=None, cursor=None)
