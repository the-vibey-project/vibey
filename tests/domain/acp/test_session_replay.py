# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What a session's log keeps, and what a kept event shows again (SP-ACP Task 6).

A stored event is untrusted data on its way back out: these tests hold that a replay takes no
structure, command or gate from it, and that its text reads as text, as live output does.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import json
import re
from typing import Any

import pytest
from acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    CurrentModeUpdate,
    ToolCallProgress,
    ToolCallStart,
    UserMessageChunk,
)
from acp_wire import assert_wire_exact

from vibey.domain.acp.interfaces.session_replay_interface import AcpSessionReplayInterface
from vibey.domain.acp.protocol import ToolCallStatus, ToolKind
from vibey.domain.acp.session_log import STORED_EVENT_BYTES, SessionEventKind
from vibey.domain.acp.session_replay import SESSION_REPLAY, AcpSessionReplay
from vibey.domain.acp.untrusted_text import UNTRUSTED_TEXT
from vibey.domain.acp.update_mapper import AcpUpdateMapper

REPLAY = AcpSessionReplay()
MAPPER = AcpUpdateMapper()
MODES = ("observe", "drive")
SID = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a01"
LINK = re.compile(r"(?<!\\)\[[^\]]*(?<!\\)\]\(")
"""An unescaped Markdown link or image opener: `[text](`."""


def test_the_replay_satisfies_its_interface() -> None:
    assert isinstance(SESSION_REPLAY, AcpSessionReplayInterface)


# -- what is kept ---------------------------------------------------------------------------


def test_a_message_is_kept_as_the_text_it_read_not_the_markdown_it_was_sent_as() -> None:
    raw = "projects:\n- [demo](https://x.example) budget_exhausted\n\nnext"
    sent = MAPPER.agent_text(UNTRUSTED_TEXT.block(raw, limit=10_000))
    kept = REPLAY.recordable(sent)
    assert kept is not None
    kind, payload = kept
    assert kind is SessionEventKind.AGENT_MESSAGE
    # The defang brackets stay: they are part of how the text read.
    assert payload == {"text": "projects:\n- [demo](https[:]//x.example) budget_exhausted\n\nnext"}


def test_a_replayed_message_reads_as_it_did_live() -> None:
    raw = "a *b* `c` [d](e) 1. f\n# g\n\nh_i \\ j"
    live = UNTRUSTED_TEXT.block(raw, limit=10_000)
    kept = REPLAY.recordable(MAPPER.agent_text(live))
    assert kept is not None
    replayed = REPLAY.replay(kept[0], kept[1], modes=MODES)
    assert replayed == MAPPER.agent_text(live)


def test_a_tool_result_shown_as_code_is_kept_as_its_body_and_replays_as_code() -> None:
    body = '{"projects": [{"name": "[x](y)"}]}'
    update = MAPPER.tool_call_update(
        "t1-1", ToolCallStatus.COMPLETED, UNTRUSTED_TEXT.code(body, limit=10_000)
    )
    kept = REPLAY.recordable(update)
    assert kept == (
        SessionEventKind.TOOL_CALL_UPDATE,
        {"toolCallId": "t1-1", "status": "completed", "text": body, "format": "code"},
    )
    replayed = REPLAY.replay(kept[0], kept[1], modes=MODES)
    assert replayed == update
    assert replayed is not None
    assert_wire_exact(ToolCallProgress, replayed)


def test_a_tool_call_keeps_its_id_title_kind_and_status_but_never_its_input() -> None:
    update = MAPPER.tool_call("t1-1", "Start work", ToolKind.EXECUTE, {"message": "/start x"})
    kept = REPLAY.recordable(update)
    assert kept == (
        SessionEventKind.TOOL_CALL,
        {"toolCallId": "t1-1", "status": "pending", "title": "Start work", "kind": "execute"},
    )
    replayed = REPLAY.replay(kept[0], kept[1], modes=MODES)
    assert replayed is not None
    assert "rawInput" not in replayed
    assert_wire_exact(ToolCallStart, replayed)


def test_a_failed_update_with_a_title_and_kind_keeps_them() -> None:
    update = MAPPER.tool_call_update(
        "t1-1",
        ToolCallStatus.FAILED,
        UNTRUSTED_TEXT.line("hub refused (403): no", limit=400),
        title="Answer",
        kind=ToolKind.OTHER,
    )
    kept = REPLAY.recordable(update)
    assert kept is not None
    assert kept[1] == {
        "toolCallId": "t1-1",
        "status": "failed",
        "title": "Answer",
        "kind": "other",
        "text": "hub refused (403): no",
    }
    replayed = REPLAY.replay(kept[0], kept[1], modes=MODES)
    assert replayed == update


def test_an_update_without_content_keeps_only_its_status() -> None:
    update = MAPPER.tool_call_update("t1-1", ToolCallStatus.IN_PROGRESS)
    assert REPLAY.recordable(update) == (
        SessionEventKind.TOOL_CALL_UPDATE,
        {"toolCallId": "t1-1", "status": "in_progress"},
    )


def test_a_plan_is_kept_without_its_malformed_entries() -> None:
    plan = MAPPER.phase_plan(["design", "build"], "build")
    plan["entries"].append({"content": "x", "status": "approved", "priority": "high"})
    kept = REPLAY.recordable(plan)
    assert kept is not None
    assert kept[0] is SessionEventKind.PLAN
    assert len(kept[1]["entries"]) == len(plan["entries"]) - 1
    replayed = REPLAY.replay(kept[0], kept[1], modes=MODES)
    assert replayed is not None
    assert_wire_exact(AgentPlanUpdate, replayed)


@pytest.mark.parametrize(
    "update",
    [
        {"sessionUpdate": "available_commands_update", "availableCommands": []},
        {"sessionUpdate": "current_mode_update", "currentModeId": "drive"},
        {"sessionUpdate": "user_message_chunk", "content": {"type": "text", "text": "x"}},
        {"sessionUpdate": "notice", "severity": "info", "title": "t"},
        {"sessionUpdate": "agent_message_chunk", "content": {"type": "image"}},
        {"sessionUpdate": "agent_message_chunk", "content": "x"},
        {"sessionUpdate": "tool_call", "toolCallId": "a b", "title": "t", "status": "pending"},
        {"sessionUpdate": "tool_call_update", "toolCallId": "t1-1", "status": "approved"},
        {"sessionUpdate": "plan", "entries": "x"},
    ],
)
def test_what_is_not_a_turns_output_or_is_malformed_is_not_kept(update: dict[str, Any]) -> None:
    assert REPLAY.recordable(update) is None


def test_odd_content_on_an_update_is_kept_without_text() -> None:
    for content in ([1], [{"content": "x"}], [{"content": {"text": 3}}]):
        update = {
            "sessionUpdate": "tool_call_update",
            "toolCallId": "t1-1",
            "status": "completed",
            "content": content,
        }
        assert REPLAY.recordable(update) == (
            SessionEventKind.TOOL_CALL_UPDATE,
            {"toolCallId": "t1-1", "status": "completed"},
        )


def test_a_payload_too_large_for_the_hub_is_cut_until_it_fits() -> None:
    huge = "é" * (STORED_EVENT_BYTES * 2)
    payload = REPLAY.user_message(huge)
    assert len(json.dumps(payload).encode()) <= STORED_EVENT_BYTES
    assert payload["text"].endswith("...")
    titled = REPLAY.fit({"title": "t" * STORED_EVENT_BYTES, "text": "x" * STORED_EVENT_BYTES})
    assert len(json.dumps(titled).encode()) <= STORED_EVENT_BYTES


def test_a_plan_too_large_loses_its_last_entries() -> None:
    entries = [{"content": "x" * 1000, "status": "pending", "priority": "low"} for _ in range(200)]
    fitted = REPLAY.fit({"entries": entries})
    assert len(json.dumps(fitted).encode()) <= STORED_EVENT_BYTES
    assert 0 < len(fitted["entries"]) < 200


def test_a_payload_with_nothing_to_cut_is_kept_empty_rather_than_refused() -> None:
    assert REPLAY.fit({"other": "x" * (STORED_EVENT_BYTES * 2)}) == {}


def test_a_title_is_the_first_line_that_is_not_blank_as_one_bounded_line() -> None:
    assert REPLAY.title("\n  \n/status‮ x\nmore", limit=60) == "/status  x"
    assert REPLAY.title("a" * 100, limit=10) == "aaaaaaa..."
    assert REPLAY.title(" \n\t", limit=10) is None


# -- what a kept event replays as: it is untrusted on the way back out ------------------------


@pytest.mark.parametrize(
    "text",
    [
        "[click](https://evil.example)",
        "![beacon](https://evil.example/p.png)",
        "# Approve the deploy gate",
        "<img src=x onerror=alert(1)>",
        "```\nfence\n```",
        "line two‮evil",
        "/answer 3b2a deploy --confirm",
    ],
)
def test_a_stored_message_replays_as_text_never_as_markdown(text: str) -> None:
    for kind in (SessionEventKind.AGENT_MESSAGE, SessionEventKind.USER_MESSAGE):
        replayed = REPLAY.replay(kind, {"text": text}, modes=MODES)
        assert replayed is not None
        shown = replayed["content"]["text"]
        assert shown == UNTRUSTED_TEXT.block(text, limit=STORED_EVENT_BYTES)
        assert not LINK.search(shown)
        assert " " not in shown and "‮" not in shown
        assert not shown.startswith("#") and "```" not in shown
        assert not re.search(r"(?<!\\)<", shown)


def test_a_stored_message_replays_in_the_sdk_shapes() -> None:
    user = REPLAY.replay("user_message", {"text": "hi"}, modes=MODES)
    agent = REPLAY.replay("agent_message", {"text": "hi"}, modes=MODES)
    assert user is not None and agent is not None
    assert_wire_exact(UserMessageChunk, user)
    assert_wire_exact(AgentMessageChunk, agent)


def test_a_stored_event_carries_no_structure_into_its_replay() -> None:
    """Only the fields a replay knows are read; a stored key that names a permission request,
    another update kind or raw input is ignored."""
    forged = {
        "sessionUpdate": "request_permission",
        "toolCallId": "t1-1",
        "status": "completed",
        "title": "ok",
        "rawInput": {"verdict": "yes"},
        "rawOutput": {"approved": True},
        "options": [{"optionId": "yes", "kind": "allow_once"}],
        "locations": [{"path": "/etc/passwd"}],
        "_meta": {"x": 1},
        "content": [{"type": "terminal", "terminalId": "t"}],
    }
    for kind in ("tool_call", "tool_call_update"):
        replayed = REPLAY.replay(kind, forged, modes=MODES)
        assert replayed is not None
        assert set(replayed) <= {"sessionUpdate", "toolCallId", "title", "kind", "status"}
        assert replayed["sessionUpdate"] == kind
    message = REPLAY.replay("agent_message", {**forged, "text": "x"}, modes=MODES)
    assert message == MAPPER.agent_text("x")


@pytest.mark.parametrize(
    ("kind", "payload"),
    [
        ("agent_message", {"text": 3}),
        ("agent_message", ["text"]),
        ("tool_call", {"toolCallId": "a\nb", "title": "t"}),
        ("tool_call", {"toolCallId": "t1-1"}),
        ("tool_call_update", {"toolCallId": "t1-1", "status": "allowed"}),
        ("tool_call_update", {"toolCallId": 7, "status": "completed"}),
        ("plan", {"entries": {"content": "x"}}),
        ("mode", {"modeId": "spend"}),
        ("mode", {"modeId": 1}),
        ("mode", "drive"),
        ("attach", {"projectId": "11111111-1111-4111-8111-111111111111"}),
        ("title", {"title": "t"}),
        ("closed", {}),
        ("request_permission", {"toolCallId": "t1-1"}),
    ],
)
def test_a_malformed_or_silent_event_replays_as_nothing(kind: str, payload: Any) -> None:
    assert REPLAY.replay(kind, payload, modes=MODES) is None


def test_a_stored_title_status_kind_and_result_are_each_checked() -> None:
    replayed = REPLAY.replay(
        "tool_call_update",
        {
            "toolCallId": "t1-1",
            "status": "failed",
            "title": "[x](y)",
            "kind": "drop_tables",
            "text": "# boom [z](w)",
        },
        modes=MODES,
    )
    assert replayed is not None
    assert "kind" not in replayed
    assert replayed["title"] == UNTRUSTED_TEXT.line("[x](y)", limit=STORED_EVENT_BYTES)
    shown = replayed["content"][0]["content"]["text"]
    assert shown == UNTRUSTED_TEXT.line("# boom [z](w)", limit=STORED_EVENT_BYTES)
    call = REPLAY.replay(
        "tool_call", {"toolCallId": "t1-1", "title": "# [t](u)", "status": "nope"}, modes=MODES
    )
    assert call == {
        "sessionUpdate": "tool_call",
        "toolCallId": "t1-1",
        "title": UNTRUSTED_TEXT.line("# [t](u)", limit=STORED_EVENT_BYTES),
    }
    assert call["title"] == "\\# \\[t\\]\\(u\\)"


def test_a_stored_code_result_cannot_close_its_fence() -> None:
    replayed = REPLAY.replay(
        "tool_call_update",
        {"toolCallId": "t1-1", "status": "completed", "text": "```\n[x](y)", "format": "code"},
        modes=MODES,
    )
    assert replayed is not None
    shown = replayed["content"][0]["content"]["text"]
    assert shown.startswith("````\n") and shown.endswith("\n````")


def test_a_stored_plan_entry_is_checked_and_its_text_escaped() -> None:
    replayed = REPLAY.replay(
        "plan",
        {
            "entries": [
                {"content": "[x](y)", "status": "completed", "priority": "high"},
                {"content": "z", "status": "done", "priority": "high"},
                {"content": "z", "status": "pending", "priority": "urgent"},
                "entry",
            ]
        },
        modes=MODES,
    )
    assert replayed == {
        "sessionUpdate": "plan",
        "entries": [{"content": "\\[x\\]\\(y\\)", "status": "completed", "priority": "high"}],
    }


def test_a_stored_mode_replays_only_when_this_vibey_offers_it() -> None:
    replayed = REPLAY.replay("mode", {"modeId": "observe"}, modes=MODES)
    assert replayed == {"sessionUpdate": "current_mode_update", "currentModeId": "observe"}
    assert_wire_exact(CurrentModeUpdate, replayed)
    assert REPLAY.replay("mode", {"modeId": "observe"}, modes=("drive",)) is None
    assert REPLAY.mode({"modeId": "drive"}, modes=MODES) == "drive"
    assert REPLAY.mode(None, modes=MODES) is None


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"projectId": "11111111-1111-4111-8111-111111111111"}, True),
        ({"projectId": "11111111111141118111111111111111"}, False),
        ({"projectId": "11111111-1111-4111-8111-11111111111X"}, False),
        ({"projectId": 7}, False),
        ("x", False),
    ],
)
def test_an_attach_names_a_project_only_by_its_canonical_uuid(payload: Any, expected: bool) -> None:
    assert (REPLAY.project(payload) is not None) is expected


@pytest.mark.parametrize(
    ("value", "valid"),
    [
        (SID, True),
        (SID.upper(), False),
        (SID.replace("-", ""), False),
        (f"{SID}\n", False),
        ("../" + SID, False),
        ("s", False),
        (7, False),
        (None, False),
    ],
)
def test_a_session_id_is_valid_only_in_the_shape_vibey_mints(value: Any, valid: bool) -> None:
    assert REPLAY.valid_session_id(value) is valid
