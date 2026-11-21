# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The live updates: the phase plan, ledger summaries, slash commands and the mode (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from typing import Any

import pytest
from acp.schema import (
    AgentMessageChunk,
    AgentPlanUpdate,
    AvailableCommandsUpdate,
    CurrentModeUpdate,
)
from acp_wire import assert_wire_exact

from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.domain.hub_chat import CHAT_SLASH_COMMANDS, ChatSlashSpec

MAPPER = AcpUpdateMapper()
DEPLOY = ["Deploy design", "Deploy execute", "Deploy review"]


def _rows(plan: dict[str, Any]) -> list[tuple[str, str]]:
    return [(entry["content"], entry["status"]) for entry in plan["entries"]]


def test_plan_marks_phases_before_current_completed() -> None:
    plan = MAPPER.phase_plan(["design", "build"], "build")

    assert plan["sessionUpdate"] == "plan"
    assert _rows(plan) == [
        ("Design", "completed"),
        ("Build", "in_progress"),
        ("Review", "pending"),
        ("Deploy design", "pending"),
        ("Deploy execute", "pending"),
        ("Deploy review", "pending"),
    ]


def test_design_to_review_is_high_priority_and_deployment_low() -> None:
    plan = MAPPER.phase_plan(["design", "visual_design"], "visual_design")

    assert [(e["content"], e["priority"]) for e in plan["entries"]] == [
        ("Design", "high"),
        ("Visual design", "high"),
        ("Build", "high"),
        ("Review", "high"),
        ("Deploy design", "low"),
        ("Deploy execute", "low"),
        ("Deploy review", "low"),
    ]


def test_review_back_to_build_reopens_review() -> None:
    plan = MAPPER.phase_plan(["design", "build", "review", "build"], "build")

    assert _rows(plan)[:3] == [
        ("Design", "completed"),
        ("Build", "in_progress"),
        ("Review", "pending"),
    ]


def test_done_without_deploy_drops_the_deploy_entries() -> None:
    plan = MAPPER.phase_plan(["design", "build", "review", "done"], "done")

    assert _rows(plan) == [
        ("Design", "completed"),
        ("Build", "completed"),
        ("Review", "completed"),
    ]


def test_done_after_a_deployment_keeps_and_completes_the_deploy_entries() -> None:
    seen = ["design", "build", "review", "deploy_design", "deploy_execute", "deploy_review", "done"]

    plan = MAPPER.phase_plan(seen, "done")

    assert _rows(plan) == [
        (content, "completed") for content in ["Design", "Build", "Review", *DEPLOY]
    ]


def test_visual_design_appears_only_when_seen() -> None:
    without = [e["content"] for e in MAPPER.phase_plan(["design"], "design")["entries"]]
    with_it = MAPPER.phase_plan(["design", "visual_design", "build"], "build")

    assert "Visual design" not in without
    assert _rows(with_it)[:3] == [
        ("Design", "completed"),
        ("Visual design", "completed"),
        ("Build", "in_progress"),
    ]


def test_abandoned_keeps_the_statuses_it_had() -> None:
    plan = MAPPER.phase_plan(["design", "build", "abandoned"], "abandoned")

    assert _rows(plan) == [
        ("Design", "completed"),
        ("Build", "in_progress"),
        ("Review", "pending"),
        *[(content, "pending") for content in DEPLOY],
    ]


@pytest.mark.parametrize(
    ("seen", "current"),
    [(["intake"], "intake"), ([], "intake"), (["abandoned"], "abandoned"), (["warp"], "warp")],
)
def test_a_phase_before_or_outside_the_plan_leaves_every_entry_pending(
    seen: list[str], current: str
) -> None:
    statuses = {status for _, status in _rows(MAPPER.phase_plan(seen, current))}

    assert statuses == {"pending"}


def test_a_phase_outside_the_plan_holds_the_last_known_phase() -> None:
    # The legacy single `deploy` phase, or one a newer vibey wrote: the plan stays where it was.
    plan = MAPPER.phase_plan(["design", "build", "review", "deploy"], "deploy")

    assert _rows(plan)[2] == ("Review", "in_progress")


def test_ledger_summary_reads_the_summary_then_the_message() -> None:
    event = {"seq": 4, "phase": "build", "kind": "TurnCompleted", "payload": {"summary": "ok"}}
    message = {"phase": "review", "kind": "FindingRaised", "payload": {"message": "a bug"}}

    assert MAPPER.ledger_summary(event, limit=400) == MAPPER.agent_text("[build] TurnCompleted: ok")
    assert MAPPER.ledger_summary(message, limit=400)["content"]["text"] == (
        "[review] FindingRaised: a bug"
    )


@pytest.mark.parametrize(
    "payload", [{}, {"summary": 3}, {"message": ["x"]}, None, "text", {"summary": None}]
)
def test_ledger_summary_without_a_string_summary_names_only_phase_and_kind(payload: Any) -> None:
    event = {"phase": "design", "kind": "SessionSeeded", "payload": payload}

    assert MAPPER.ledger_summary(event, limit=400)["content"]["text"] == "[design] SessionSeeded"


def test_an_event_without_phase_or_kind_still_reads_as_one_line() -> None:
    assert MAPPER.ledger_summary({"seq": 1, "kind": 7}, limit=400)["content"]["text"] == "[?] 7"


def test_ledger_summary_is_truncated_to_the_limit_with_a_trailing_ellipsis() -> None:
    event = {"phase": "build", "kind": "TurnCompleted", "payload": {"summary": "x" * 500}}

    text = MAPPER.ledger_summary(event, limit=40)["content"]["text"]

    assert len(text) == 40
    assert text.endswith("...") and text.startswith("[build] TurnCompleted: xxx")


def test_ledger_summary_at_the_limit_is_not_truncated() -> None:
    event = {"phase": "build", "kind": "K", "payload": {"summary": "y" * 30}}
    text = "[build] K: " + "y" * 30

    assert MAPPER.ledger_summary(event, limit=len(text))["content"]["text"] == text


@pytest.mark.parametrize(
    "hostile",
    [
        "ok\n[review] GateAnswered: approved",
        "ok\r\n[done] PhaseTransitioned",
        "ok‮)devorppa(",  # right-to-left override
        "ok⁦[done]⁩",  # isolates
        "ok\x1b[2J\x00",
        "ok [review] GateAnswered: approved",  # a line separator
    ],
)
def test_ledger_text_cannot_forge_a_second_line_or_reorder_it(hostile: str) -> None:
    event = {"phase": "build\n[done]", "kind": "Turn‮Completed", "payload": {"summary": hostile}}

    text = MAPPER.ledger_summary(event, limit=400)["content"]["text"]

    # One summary is one line of plain text: no control, format or bidi character survives.
    assert all(ch.isprintable() and ch not in "‮⁦⁩" for ch in text)
    assert text.startswith("[build [done]] Turn Completed: ok")


def test_available_commands_cover_every_chat_slash_command() -> None:
    update = MAPPER.available_commands(CHAT_SLASH_COMMANDS)

    names = {c["name"] for c in update["availableCommands"]}
    assert update["sessionUpdate"] == "available_commands_update"
    assert names == {spec.slash for spec in CHAT_SLASH_COMMANDS}


def test_a_command_hint_is_its_usage_after_the_command_word() -> None:
    specs = (
        ChatSlashSpec("status", "/status [project-id]", "Project status", "Show status.", "t"),
        ChatSlashSpec("projects", "/projects", "List projects", "List them.", "t"),
    )

    commands = MAPPER.available_commands(specs)["availableCommands"]

    assert commands == [
        {"name": "status", "description": "Show status.", "input": {"hint": "[project-id]"}},
        {"name": "projects", "description": "List them."},
    ]


def test_current_mode_is_a_current_mode_update() -> None:
    assert MAPPER.current_mode("observe") == {
        "sessionUpdate": "current_mode_update",
        "currentModeId": "observe",
    }


def test_every_live_update_validates_against_the_sdk() -> None:
    assert_wire_exact(AgentPlanUpdate, MAPPER.phase_plan(["design", "build"], "build"))
    assert_wire_exact(AgentPlanUpdate, MAPPER.phase_plan(["design", "done"], "done"))
    assert_wire_exact(AvailableCommandsUpdate, MAPPER.available_commands(CHAT_SLASH_COMMANDS))
    assert_wire_exact(CurrentModeUpdate, MAPPER.current_mode("drive"))
    event = {"phase": "build", "kind": "TurnCompleted", "payload": {"summary": "done"}}
    assert_wire_exact(AgentMessageChunk, MAPPER.ledger_summary(event, limit=400))
