# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Every `session/update` the mapper builds is exactly what the official SDK puts on the wire.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import pytest
from acp.schema import (
    AgentMessageChunk,
    SessionNotification,
    SessionUpdateNotice,
    ToolCallProgress,
    ToolCallStart,
    UserMessageChunk,
)
from acp_wire import assert_wire_exact

from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.protocol import NoticeSeverity, ToolCallStatus, ToolKind
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.domain.hub_scope import HubScope

MAPPER = AcpUpdateMapper()


def test_the_mapper_satisfies_its_interface() -> None:
    assert isinstance(MAPPER, AcpUpdateMapperInterface)


def test_agent_text_is_an_agent_message_chunk() -> None:
    update = MAPPER.agent_text("two projects")
    assert update == {
        "sessionUpdate": "agent_message_chunk",
        "content": {"type": "text", "text": "two projects"},
    }
    assert_wire_exact(AgentMessageChunk, update)


def test_user_text_is_a_user_message_chunk() -> None:
    update = MAPPER.user_text("/projects")
    assert update["sessionUpdate"] == "user_message_chunk"
    assert update["content"] == {"type": "text", "text": "/projects"}
    assert_wire_exact(UserMessageChunk, update)


def test_a_tool_call_starts_pending_with_its_raw_input() -> None:
    raw = {"message": "/start"}
    update = MAPPER.tool_call("t1-1", "Resume project worker", ToolKind.EXECUTE, raw)
    assert update == {
        "sessionUpdate": "tool_call",
        "toolCallId": "t1-1",
        "title": "Resume project worker",
        "kind": "execute",
        "status": "pending",
        "rawInput": {"message": "/start"},
    }
    assert update["rawInput"] is not raw
    assert_wire_exact(ToolCallStart, update)


def test_a_tool_call_update_without_text_carries_only_the_status() -> None:
    update = MAPPER.tool_call_update("t1-1", ToolCallStatus.IN_PROGRESS)
    assert update == {
        "sessionUpdate": "tool_call_update",
        "toolCallId": "t1-1",
        "status": "in_progress",
    }
    assert_wire_exact(ToolCallProgress, update)


def test_a_tool_call_update_with_text_carries_it_as_content() -> None:
    update = MAPPER.tool_call_update("t1-1", ToolCallStatus.FAILED, "hub refused (403)")
    assert update["status"] == "failed"
    assert update["content"] == [
        {"type": "content", "content": {"type": "text", "text": "hub refused (403)"}}
    ]
    assert_wire_exact(ToolCallProgress, update)


def test_a_tool_call_update_can_retitle_and_rekind_the_call() -> None:
    update = MAPPER.tool_call_update(
        "t1-1", ToolCallStatus.COMPLETED, "[]", title="List projects", kind=ToolKind.READ
    )
    assert update == {
        "sessionUpdate": "tool_call_update",
        "toolCallId": "t1-1",
        "status": "completed",
        "title": "List projects",
        "kind": "read",
        "content": [{"type": "content", "content": {"type": "text", "text": "[]"}}],
    }
    assert_wire_exact(ToolCallProgress, update)


def test_an_empty_text_is_still_sent_as_content() -> None:
    update = MAPPER.tool_call_update("t1-1", ToolCallStatus.COMPLETED, "")
    assert update["content"][0]["content"]["text"] == ""


def test_a_notice_goes_out_as_a_notice_when_the_client_can_show_one() -> None:
    update = MAPPER.notice(
        "Hub restarted", NoticeSeverity.WARNING, "it was down for 3s", client_notices=True
    )
    assert update == {
        "sessionUpdate": "notice",
        "severity": "warning",
        "title": "Hub restarted",
        "description": "it was down for 3s",
    }
    assert_wire_exact(SessionUpdateNotice, update)


def test_a_notice_falls_back_to_a_message_when_the_client_cannot_show_one() -> None:
    update = MAPPER.notice(
        "Hub restarted", NoticeSeverity.WARNING, "it was down for 3s", client_notices=False
    )
    assert update == MAPPER.agent_text("Hub restarted: it was down for 3s")


@pytest.mark.parametrize(
    ("scope", "kind"),
    [
        (HubScope.VIEW, ToolKind.READ),
        (HubScope.RUN, ToolKind.EXECUTE),
        (HubScope.ANSWER, ToolKind.OTHER),
        (HubScope.SPEND, ToolKind.OTHER),
        (HubScope.BUMP, ToolKind.OTHER),
        (HubScope.WORKFLOWS, ToolKind.OTHER),
    ],
)
def test_a_scope_maps_to_a_tool_kind(scope: HubScope, kind: ToolKind) -> None:
    assert MAPPER.tool_kind_for(scope) is kind


def test_every_update_validates_inside_a_session_notification() -> None:
    updates = [
        MAPPER.agent_text("a"),
        MAPPER.user_text("b"),
        MAPPER.tool_call("c", "C", ToolKind.READ, {}),
        MAPPER.tool_call_update("c", ToolCallStatus.COMPLETED, "done"),
        MAPPER.notice("d", NoticeSeverity.INFO, "e", client_notices=True),
    ]
    for update in updates:
        assert_wire_exact(SessionNotification, {"sessionId": "s", "update": update})
