# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One ACP prompt turn over the hub chat: the updates it streams, the modes it honours, and
how it ends when a `session/cancel` lands before, during or after the hub call (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

import pytest
from acp.schema import PromptResponse, SessionNotification
from acp_fakes import FakeChannel, FakeHub, build_agent, build_turn, context, text, until

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.dto import HubTurn
from vibey.application.acp.interfaces.acp_prompt_turn_interface import AcpPromptTurnInterface
from vibey.domain.acp.protocol import StopReason
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_chat import ChatIntent, ChatSlashSpec, HubChat
from vibey.domain.hub_scope import HubForbidden, HubScope
from vibey.infrastructure.jsonrpc.codec import CODEC
from vibey.infrastructure.jsonrpc.peer import JsonRpcPeer

PROJECT = UUID("7d6c2a8e-0c41-4c1e-9d0e-2f4b8f0a1b2c")
PROJECTS_TURN = HubTurn(
    reply="1 project(s):\n- demo [BUILD]",
    tool_calls=(
        {"name": "vibey_projects", "arguments": {}, "result": [{"name": "demo", "phase": "BUILD"}]},
    ),
    gates=(),
    project_id=None,
)


def test_the_turn_satisfies_its_interface() -> None:
    assert isinstance(build_turn(FakeChannel(), FakeHub()), AcpPromptTurnInterface)


async def test_prompt_streams_tool_call_pending_in_progress_completed_then_reply() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)

    stop = await build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")

    assert stop is StopReason.END_TURN
    assert channel.kinds == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "completed"),
        ("agent_message_chunk", None),
    ]
    for update in channel.updates:
        assert_wire_exact(SessionNotification, {"sessionId": "s", "update": update})
    start = channel.updates[0]
    assert start["toolCallId"] == "t1-1"
    assert start["title"] == "List projects"
    assert start["kind"] == "read"
    assert start["rawInput"] == {"message": "/projects"}
    assert {update["toolCallId"] for update in channel.updates[:3]} == {"t1-1"}
    result_text = channel.updates[2]["content"][0]["content"]["text"]
    assert json.loads(result_text) == [{"name": "demo", "phase": "BUILD"}]
    assert channel.texts == ["1 project(s):\n- demo [BUILD]"]
    assert set(channel.sessions) == {"s"}


async def test_a_run_intent_is_an_execute_tool_call_in_drive_mode() -> None:
    channel, hub = FakeChannel(), FakeHub(HubTurn("Resumed.", (), (), PROJECT))

    await build_turn(channel, hub).run(context(), [text(f"/start {PROJECT}")], turn_id="t1")

    assert channel.updates[0]["kind"] == "execute"
    assert channel.updates[0]["title"] == "Resume project worker"
    assert hub.calls[0].message == f"/start {PROJECT}"


async def test_a_long_result_is_truncated_to_the_configured_limit() -> None:
    huge = HubTurn("ok", ({"name": "vibey_projects", "result": "x" * 5000},), (), None)
    channel = FakeChannel()

    await build_turn(channel, FakeHub(huge), max_result_chars=500).run(
        context(), [text("/projects")], turn_id="t1"
    )

    result_text = channel.updates[2]["content"][0]["content"]["text"]
    assert len(result_text) < 1000
    assert "truncat" in result_text


async def test_a_turn_with_no_tool_call_completes_without_content() -> None:
    channel = FakeChannel()

    await build_turn(channel, FakeHub()).run(context(), [text("/projects")], turn_id="t1")

    assert channel.updates[2] == {
        "sessionUpdate": "tool_call_update",
        "toolCallId": "t1-1",
        "status": "completed",
    }
    assert channel.texts == ["Done."]


async def test_the_project_the_hub_reports_becomes_the_sessions_project() -> None:
    session = context()
    hub = FakeHub(HubTurn("demo is in BUILD.", (), (), PROJECT))

    await build_turn(FakeChannel(), hub).run(session, [text(f"/status {PROJECT}")], turn_id="t1")
    await build_turn(FakeChannel(), hub).run(session, [text("/status")], turn_id="t2")

    assert session.project_id == PROJECT
    assert [call.project_id for call in hub.calls] == [None, PROJECT]


async def test_a_turn_without_a_project_keeps_the_sessions_project() -> None:
    session = context()
    session.project_id = PROJECT

    await build_turn(FakeChannel(), FakeHub(PROJECTS_TURN)).run(
        session, [text("/projects")], turn_id="t1"
    )

    assert session.project_id == PROJECT


async def test_hub_refusal_marks_the_tool_call_failed_and_still_ends_turn() -> None:
    channel = FakeChannel()
    hub = FakeHub(error=HubForbidden("hub refused (403): scope run is not granted"))

    stop = await build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")

    assert stop is StopReason.END_TURN
    assert channel.kinds == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "failed"),
        ("agent_message_chunk", None),
    ]
    failed_text = channel.updates[2]["content"][0]["content"]["text"]
    assert failed_text == "hub refused (403): scope run is not granted"
    assert channel.texts == ["hub refused (403): scope run is not granted"]


async def test_observe_mode_refuses_run_intents_without_calling_the_hub() -> None:
    channel, hub = FakeChannel(), FakeHub()

    stop = await build_turn(channel, hub).run(
        context(mode_id="observe"), [text(f"/start {PROJECT}")], turn_id="t1"
    )

    assert stop is StopReason.END_TURN
    assert hub.calls == []
    assert len(channel.updates) == 1
    assert "drive mode" in channel.texts[-1]
    assert "/start" in channel.texts[-1]


async def test_observe_mode_still_reads() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)

    await build_turn(channel, hub).run(
        context(mode_id="observe"), [text("/projects")], turn_id="t1"
    )

    assert len(hub.calls) == 1


async def test_observe_mode_refuses_a_bare_number_the_hub_would_read_as_a_gate_answer() -> None:
    # Locally, with no open gates, "1" parses as a projects read; the hub, which sees the
    # open gates, reads it as an answer to the oldest one. The stricter reading wins.
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)

    await build_turn(channel, hub).run(context(mode_id="observe"), [text(" 1 ")], turn_id="t1")

    assert hub.calls == []
    assert "drive mode" in channel.texts[-1]


async def test_drive_mode_sends_a_bare_number_to_the_hub() -> None:
    hub = FakeHub(PROJECTS_TURN)

    await build_turn(FakeChannel(), hub).run(context(), [text("1")], turn_id="t1")

    assert [call.message for call in hub.calls] == ["1"]


async def test_a_scope_the_hub_does_not_grant_is_refused_naming_agent_scopes() -> None:
    channel = FakeChannel()
    hub = FakeHub(scopes=frozenset({HubScope.VIEW}))

    await build_turn(channel, hub).run(context(), [text(f"/start {PROJECT}")], turn_id="t1")

    assert hub.calls == []
    assert "agent_scopes" in channel.texts[-1]
    assert "`run`" in channel.texts[-1]


async def test_request_id_is_stable_per_session_and_turn() -> None:
    hub = FakeHub(PROJECTS_TURN)
    turn = build_turn(FakeChannel(), hub)

    await turn.run(context(), [text("/projects")], turn_id="t1")
    await turn.run(context(), [text("/projects")], turn_id="t1")
    await turn.run(context("s2"), [text("/projects")], turn_id="t1")

    assert [call.request_id for call in hub.calls] == ["acp-s-t1", "acp-s-t1", "acp-s2-t1"]


async def test_parse_error_is_a_message_not_a_jsonrpc_error() -> None:
    channel, hub = FakeChannel(), FakeHub()

    stop = await build_turn(channel, hub).run(context(), [text("/bogus")], turn_id="t1")

    assert stop is StopReason.END_TURN
    assert hub.calls == []
    assert channel.kinds == [("agent_message_chunk", None)]
    assert "unknown command `/bogus`" in channel.texts[0]


async def test_an_empty_prompt_is_answered_with_a_message() -> None:
    channel = FakeChannel()

    stop = await build_turn(channel, FakeHub()).run(
        context(), [{"type": "image", "data": "", "mimeType": "image/png"}], turn_id="t1"
    )

    assert stop is StopReason.END_TURN
    assert channel.texts == ["write a message or a /command"]


async def test_help_is_answered_locally_without_the_hub() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await build_turn(channel, hub).run(context(mode_id="observe"), [text("/help")], turn_id="t1")

    assert hub.calls == []
    assert channel.texts == [HubChat().help_text()]


def _resource(body: str, uri: str = "file:///spec.md") -> dict[str, Any]:
    return {"type": "resource", "resource": {"uri": uri, "text": body}}


async def test_a_legit_new_carries_the_resource_text_as_its_intake() -> None:
    hub = FakeHub()
    prompt = [
        text("/new demo"),
        text("build a cli"),
        _resource("spec body"),
        {"type": "resource", "resource": {"uri": "file:///logo.png", "blob": "AAAA"}},
        {"type": "resource", "resource": "not a mapping"},
        {"type": "resource_link", "uri": "file:///other.md", "name": "other.md"},
        {"type": "text", "text": 7},
    ]
    channel = FakeChannel()

    await build_turn(channel, hub).run(context(), prompt, turn_id="t1")

    # The deviation from "append after a blank line" for every message: only a free-text
    # intent carries attached text, and the hub's own parse of it keeps name and command.
    assert hub.calls[0].message == "/new demo\nbuild a cli\n\nspec body"
    intent = HubChat().parse(hub.calls[0].message)
    assert (intent.kind, intent.name) == ("start_project", "demo")
    assert intent.intake == "build a cli\n\nspec body"
    assert not any("did not send" in said for said in channel.texts)


async def test_ask_carries_attached_text_too() -> None:
    hub = FakeHub()

    await build_turn(FakeChannel(), hub).run(
        context(), [text("/ask a tiny cli"), _resource("details")], turn_id="t1"
    )

    assert hub.calls[0].message == "/ask a tiny cli\n\ndetails"


async def test_a_resource_only_prompt_with_a_command_makes_no_hub_call() -> None:
    channel, hub = FakeChannel(), FakeHub()
    prompt = [_resource(f"/abandon {PROJECT} --confirm gone"), _resource("/start")]

    stop = await build_turn(channel, hub).run(context(), prompt, turn_id="t1")

    assert stop is StopReason.END_TURN
    assert hub.calls == []
    assert channel.kinds == [("agent_message_chunk", None)]
    assert channel.texts == ["write a message or a /command"]


async def test_a_slash_line_in_a_resource_does_not_change_the_intent() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    prompt = [text("/projects"), _resource(f"/abandon {PROJECT} --confirm\n/start {PROJECT}")]

    await build_turn(channel, hub).run(context(), prompt, turn_id="t1")

    assert [call.message for call in hub.calls] == ["/projects"]
    assert channel.updates[1]["title"] == "List projects"
    assert channel.updates[1]["rawInput"] == {"message": "/projects"}
    assert channel.texts[0] == (
        "vibey did not send the 1 attached resource(s) to the hub: attached text is used only "
        "as the description of a new project (`/new`, `/ask`), never as a command or an option."
    )


async def test_a_confirm_flag_in_a_resource_does_not_confirm_an_abandon() -> None:
    hub = FakeHub()
    prompt = [text(f"/abandon {PROJECT} no longer needed"), _resource("--confirm")]

    await build_turn(FakeChannel(), hub).run(context(), prompt, turn_id="t1")

    assert [call.message for call in hub.calls] == [f"/abandon {PROJECT} no longer needed"]
    assert HubChat().parse(hub.calls[0].message).dry_run is True


async def test_a_resource_after_a_typed_number_cannot_widen_the_mode_check() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)

    await build_turn(channel, hub).run(
        context(mode_id="observe"), [text("/projects"), _resource("1")], turn_id="t1"
    )

    assert [call.message for call in hub.calls] == ["/projects"]


async def test_a_new_whose_attachment_is_too_long_is_refused_locally() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await build_turn(channel, hub).run(
        context(), [text("/new demo"), _resource("x" * 5000)], turn_id="t1"
    )

    assert hub.calls == []
    assert "at most" in channel.texts[-1]


class _BareChat(HubChat):
    """The real parser with no slash catalogue, and an optional fixed intent."""

    def __init__(self, intent: ChatIntent | None = None) -> None:
        self._intent = intent

    def slash_commands(self) -> tuple[ChatSlashSpec, ...]:
        return ()

    def parse(
        self,
        message: str,
        *,
        project_id: UUID | None = None,
        open_gates: Sequence[Mapping[str, Any]] = (),
    ) -> ChatIntent:
        if self._intent is not None:
            return self._intent
        return super().parse(message, project_id=project_id, open_gates=open_gates)


async def test_without_a_slash_entry_the_tool_title_and_name_are_used() -> None:
    channel = FakeChannel()

    await build_turn(channel, FakeHub(PROJECTS_TURN), chat=_BareChat()).run(
        context(), [text("/projects")], turn_id="t1"
    )
    await build_turn(channel, FakeHub(), chat=_BareChat()).run(
        context(mode_id="observe"), [text(f"/start {PROJECT}")], turn_id="t2"
    )

    assert channel.updates[0]["title"] == "List projects"
    assert "`vibey_start_work` needs drive mode" in channel.texts[-1]


async def test_an_intent_naming_an_unknown_tool_is_refused() -> None:
    channel, hub = FakeChannel(), FakeHub()
    chat = _BareChat(ChatIntent(kind="projects", tool_name="vibey_no_such_tool"))

    stop = await build_turn(channel, hub, chat=chat).run(context(), [text("x")], turn_id="t1")

    assert stop is StopReason.END_TURN
    assert hub.calls == []
    assert "vibey_no_such_tool" in channel.texts[-1]


# -- cancellation ---------------------------------------------------------------------------


async def test_cancel_during_slow_hub_call_reports_real_outcome_within_grace() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    hub.release = asyncio.Event()
    run = asyncio.create_task(
        build_turn(channel, hub, settings=AcpSettings(cancel_grace_seconds=5.0)).run(
            context(), [text("/projects")], turn_id="t1"
        )
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    run.cancel()
    await until(lambda: not run.done() and len(channel.updates) == 2)
    hub.release.set()

    with pytest.raises(asyncio.CancelledError):
        await run
    assert channel.kinds == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "completed"),
    ]
    assert json.loads(channel.updates[2]["content"][0]["content"]["text"]) == [
        {"name": "demo", "phase": "BUILD"}
    ]


async def test_a_refusal_within_grace_is_reported_as_failed() -> None:
    channel = FakeChannel()
    hub = FakeHub(error=HubForbidden("hub refused (403): no"))
    hub.release = asyncio.Event()
    run = asyncio.create_task(
        build_turn(channel, hub, settings=AcpSettings(cancel_grace_seconds=5.0)).run(
            context(), [text("/projects")], turn_id="t1"
        )
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    run.cancel()
    await asyncio.sleep(0)
    hub.release.set()

    with pytest.raises(asyncio.CancelledError):
        await run
    assert channel.kinds[-1] == ("tool_call_update", "failed")
    assert channel.updates[-1]["content"][0]["content"]["text"] == "hub refused (403): no"


async def test_cancel_after_grace_reports_failed_with_request_id() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    hub.release = asyncio.Event()
    run = asyncio.create_task(
        build_turn(channel, hub, settings=AcpSettings(cancel_grace_seconds=0.0)).run(
            context(), [text("/projects")], turn_id="t1"
        )
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert channel.kinds[-1] == ("tool_call_update", "failed")
    assert channel.updates[-1]["content"][0]["content"]["text"] == (
        "cancelled before the hub answered; the hub may still apply it (request id acp-s-t1)"
    )
    hub.release.set()
    await asyncio.sleep(0)


async def test_cancel_before_the_hub_call_closes_the_tool_call_and_never_calls_the_hub() -> None:
    channel, hub = FakeChannel(), FakeHub()
    gate = channel.hold_at[2] = asyncio.Event()  # in_progress is being sent
    run = asyncio.create_task(
        build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")
    )
    await until(lambda: len(channel.updates) == 2)

    gate.set()
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert hub.calls == []
    assert channel.kinds[-1] == ("tool_call_update", "failed")
    assert channel.updates[-1]["content"][0]["content"]["text"] == (
        "cancelled before it was sent to the hub"
    )


async def test_cancel_while_the_pending_frame_is_written_still_closes_the_tool_call() -> None:
    # The transport finishes a frame it is cancelled during, so the client has `pending`;
    # the turn must close it rather than leave it pending forever (review B-3).
    channel, hub = FakeChannel(), FakeHub()
    gate = channel.hold_at[1] = asyncio.Event()
    run = asyncio.create_task(
        build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")
    )
    await until(lambda: len(channel.updates) == 1)

    run.cancel()
    await asyncio.sleep(0)
    assert len(channel.updates) == 1  # the settle waits for the pending frame to go out
    gate.set()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert hub.calls == []
    assert channel.kinds == [("tool_call", "pending"), ("tool_call_update", "failed")]
    assert channel.updates[-1]["content"][0]["content"]["text"] == (
        "cancelled before it was sent to the hub"
    )


async def test_an_unexpected_hub_failure_fails_the_tool_call_and_ends_the_turn() -> None:
    channel = FakeChannel()
    hub = FakeHub(error=OSError("state dir is read-only"))

    stop = await build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")

    assert stop is StopReason.END_TURN
    assert channel.kinds == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "failed"),
        ("agent_message_chunk", None),
    ]
    assert channel.updates[2]["content"][0]["content"]["text"] == (
        "OSError: state dir is read-only"
    )
    assert channel.texts == ["OSError: state dir is read-only"]


async def test_an_unexpected_failure_within_grace_is_reported_by_type() -> None:
    channel = FakeChannel()
    hub = FakeHub(error=RuntimeError("executor shut down"))
    hub.release = asyncio.Event()
    run = asyncio.create_task(
        build_turn(channel, hub, settings=AcpSettings(cancel_grace_seconds=5.0)).run(
            context(), [text("/projects")], turn_id="t1"
        )
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    run.cancel()
    await asyncio.sleep(0)
    hub.release.set()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert channel.updates[-1]["content"][0]["content"]["text"] == (
        "RuntimeError: executor shut down"
    )


async def test_cancel_after_the_outcome_was_reported_reports_nothing_twice() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    gate = channel.hold_at[3] = asyncio.Event()  # the completed update hangs
    run = asyncio.create_task(
        build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")
    )
    await until(lambda: len(channel.updates) == 3)

    gate.set()
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert channel.kinds == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "completed"),
    ]


@pytest.mark.parametrize(
    ("hub", "closing"),
    [
        (FakeHub(PROJECTS_TURN), ("tool_call_update", "completed")),
        (FakeHub(error=OSError("down")), ("tool_call_update", "failed")),
    ],
)
async def test_a_cancel_while_the_close_waits_to_be_written_still_sends_it_once(
    hub: FakeHub, closing: tuple[str, str]
) -> None:
    # Review S-3: the close waits for the write lock when the cancel lands; it must still go
    # out, once, rather than be dropped with the tool call left in progress.
    channel = FakeChannel()
    held = channel.hold_before[3] = asyncio.Event()
    run = asyncio.create_task(
        build_turn(channel, hub).run(context(), [text("/projects")], turn_id="t1")
    )
    await asyncio.wait_for(channel.write_waiting.wait(), 5)

    run.cancel()
    await asyncio.sleep(0)
    held.set()
    with pytest.raises(asyncio.CancelledError):
        await run

    assert channel.kinds == [("tool_call", "pending"), ("tool_call_update", "in_progress"), closing]


# -- through a real JSON-RPC peer -----------------------------------------------------------


class _Wire:
    """An `AcpAgent` served by a real `JsonRpcPeer` on a test-fed reader."""

    def __init__(self, channel: FakeChannel, hub: FakeHub, settings: AcpSettings) -> None:
        self.reader = asyncio.StreamReader()
        self.lines: list[dict[str, Any]] = []
        self.agent = build_agent(channel, hub, settings=settings)
        self.peer = JsonRpcPeer(
            self.reader,
            self._write,
            on_request=self.agent.handle_request,
            on_notification=self.agent.handle_notification,
            codec=CODEC,
            eof_grace_seconds=5.0,
        )
        self.task = asyncio.create_task(self.peer.run())

    async def _write(self, line: str) -> None:
        assert line.endswith("\n") and line.count("\n") == 1
        self.lines.append(json.loads(line))

    def send(self, *messages: dict[str, Any]) -> None:
        self.reader.feed_data(
            b"".join((json.dumps({"jsonrpc": "2.0", **m}) + "\n").encode() for m in messages)
        )

    def response(self, msg_id: int) -> dict[str, Any] | None:
        return next((line for line in self.lines if line.get("id") == msg_id), None)

    async def close(self) -> None:
        self.reader.feed_eof()
        await asyncio.wait_for(self.task, 10)


async def test_cancel_in_the_same_read_as_prompt_returns_cancelled() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    wire = _Wire(channel, hub, AcpSettings())
    wire.send({"id": 1, "method": "session/new", "params": {"cwd": "/work", "mcpServers": []}})
    await until(lambda: wire.response(1) is not None)

    wire.send(
        {
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": "s", "prompt": [text("/projects")]},
        },
        {"method": "session/cancel", "params": {"sessionId": "s"}},
    )
    await until(lambda: wire.response(2) is not None)
    await wire.close()

    response = wire.response(2)
    assert response is not None
    assert response["result"] == {"stopReason": "cancelled"}
    assert_wire_exact(PromptResponse, response["result"])
    assert hub.calls == []
    assert not wire.agent.sessions["s"].turn_active


async def test_the_next_prompt_after_a_cancel_ends_normally() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    wire = _Wire(channel, hub, AcpSettings())
    wire.send({"id": 1, "method": "session/new", "params": {"cwd": "/work", "mcpServers": []}})
    await until(lambda: wire.response(1) is not None)
    prompt = {"sessionId": "s", "prompt": [text("/projects")]}

    wire.send(
        {"id": 2, "method": "session/prompt", "params": prompt},
        {"method": "session/cancel", "params": {"sessionId": "s"}},
    )
    await until(lambda: wire.response(2) is not None)
    wire.send({"method": "session/cancel", "params": {"sessionId": "s"}})
    wire.send({"id": 3, "method": "session/prompt", "params": prompt})
    await until(lambda: wire.response(3) is not None)
    await wire.close()

    assert wire.response(2) == {"jsonrpc": "2.0", "id": 2, "result": {"stopReason": "cancelled"}}
    assert wire.response(3) == {"jsonrpc": "2.0", "id": 3, "result": {"stopReason": "end_turn"}}
    assert len(hub.calls) == 1


async def test_cancel_through_the_peer_waits_for_the_hub_within_grace() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    hub.release = asyncio.Event()
    wire = _Wire(channel, hub, AcpSettings(cancel_grace_seconds=5.0))
    wire.send({"id": 1, "method": "session/new", "params": {"cwd": "/work", "mcpServers": []}})
    await until(lambda: wire.response(1) is not None)
    wire.send(
        {
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": "s", "prompt": [text("/projects")]},
        }
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    wire.send({"method": "session/cancel", "params": {"sessionId": "s"}})
    await until(lambda: wire.agent.sessions["s"].cancel_requested)
    hub.release.set()
    await until(lambda: wire.response(2) is not None)
    await wire.close()

    assert wire.response(2) == {"jsonrpc": "2.0", "id": 2, "result": {"stopReason": "cancelled"}}
    assert channel.kinds[-1] == ("tool_call_update", "completed")
    assert all("error" not in line for line in wire.lines)


async def test_a_repeated_cancel_during_grace_still_reports_the_request_id() -> None:
    # Esc pressed twice: the second cancel must not interrupt the settle (review A-1).
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    hub.release = asyncio.Event()
    agent = build_agent(channel, hub, settings=AcpSettings(cancel_grace_seconds=0.2))
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    prompt = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("/projects")]})
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0.05)
    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "cancelled"}
    assert channel.kinds[-1] == ("tool_call_update", "failed")
    assert channel.updates[-1]["content"][0]["content"]["text"] == (
        "cancelled before the hub answered; the hub may still apply it (request id acp-s-t1)"
    )
    hub.release.set()
    await asyncio.sleep(0)


async def test_a_repeated_cancel_within_grace_still_reports_the_real_outcome() -> None:
    channel, hub = FakeChannel(), FakeHub(PROJECTS_TURN)
    hub.release = asyncio.Event()
    agent = build_agent(channel, hub, settings=AcpSettings(cancel_grace_seconds=5.0))
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    prompt = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("/projects")]})
    )
    await asyncio.wait_for(hub.entered.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0)
    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0)
    hub.release.set()

    assert await asyncio.wait_for(prompt, 5) == {"stopReason": "cancelled"}
    assert channel.kinds[-1] == ("tool_call_update", "completed")
