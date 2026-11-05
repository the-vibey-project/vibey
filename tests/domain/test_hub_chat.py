# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Unit tests for the pure hub chat parser and turn renderer (`domain/hub_chat.py`)."""

from __future__ import annotations

from uuid import UUID

import pytest

from vibey.domain.errors import LifecycleInvalid
from vibey.domain.hub_chat import (
    CHAT_SLASH_COMMANDS,
    HUB_CHAT,
    MAX_CHAT_MESSAGE_CHARS,
    ChatIntent,
    HubChat,
)
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface

PID = UUID("11111111-1111-4111-8111-111111111111")
OTHER_PID = UUID("22222222-2222-4222-8222-222222222222")
GID = UUID("33333333-3333-4333-8333-333333333333")


def test_hub_chat_satisfies_protocol() -> None:
    chat = HubChat()
    assert isinstance(chat, HubChatInterface)
    assert isinstance(HUB_CHAT, HubChatInterface)
    specs = chat.slash_commands()
    assert specs == CHAT_SLASH_COMMANDS
    assert specs[0].as_dict()["slash"] == "projects"
    help_text = chat.help_text()
    assert "/projects" in help_text
    assert "/abandon" in help_text


def test_parse_rejects_empty_and_overlong_messages() -> None:
    with pytest.raises(LifecycleInvalid, match="write a message"):
        HUB_CHAT.parse("   ")
    with pytest.raises(LifecycleInvalid, match="at most"):
        HUB_CHAT.parse("x" * (MAX_CHAT_MESSAGE_CHARS + 1))


def test_parse_slash_commands() -> None:
    assert HUB_CHAT.parse("/help", project_id=PID).kind == "help"
    assert HUB_CHAT.parse("/?").kind == "help"
    assert HUB_CHAT.parse("/").kind == "help"
    assert HUB_CHAT.parse("/projects").kind == "projects"
    assert HUB_CHAT.parse("/loops").kind == "loops"
    assert HUB_CHAT.parse("/lanes").kind == "lanes"
    assert HUB_CHAT.parse("/doctor").kind == "doctor"

    gates_all = HUB_CHAT.parse("/gates")
    assert gates_all.kind == "gates" and gates_all.project_id is None
    gates_pid = HUB_CHAT.parse(f"/gates {PID}")
    assert gates_pid.project_id == PID
    with pytest.raises(LifecycleInvalid, match="not a valid UUID"):
        HUB_CHAT.parse("/gates not-a-uuid")

    assert HUB_CHAT.parse("/status", project_id=PID).project_id == PID
    assert HUB_CHAT.parse(f"/status {OTHER_PID}", project_id=PID).project_id == OTHER_PID
    with pytest.raises(LifecycleInvalid, match="select a project"):
        HUB_CHAT.parse("/status")
    with pytest.raises(LifecycleInvalid, match="not a valid UUID"):
        HUB_CHAT.parse("/status bad-uuid")

    assert HUB_CHAT.parse("/budget", project_id=PID).kind == "budget"
    assert HUB_CHAT.parse("/queue", project_id=PID).kind == "queue"
    assert HUB_CHAT.parse("/start", project_id=PID).kind == "start_work"
    assert HUB_CHAT.parse("/pause", project_id=PID).kind == "pause_work"
    assert HUB_CHAT.parse("/stop", project_id=PID).kind == "pause_work"

    with pytest.raises(LifecycleInvalid, match="unknown command `/bogus`"):
        HUB_CHAT.parse("/bogus")


def test_parse_ledger_slash_variations() -> None:
    bare = HUB_CHAT.parse("/ledger", project_id=PID)
    assert bare.kind == "ledger" and bare.project_id == PID and bare.text is None

    with_uuid_only = HUB_CHAT.parse(f"/ledger {OTHER_PID}")
    assert with_uuid_only.project_id == OTHER_PID and with_uuid_only.text is None

    with_uuid_and_text = HUB_CHAT.parse(f"/ledger {OTHER_PID} GateRaised")
    assert with_uuid_and_text.project_id == OTHER_PID and with_uuid_and_text.text == "GateRaised"

    with_text_and_fallback = HUB_CHAT.parse("/ledger GateAnswered", project_id=PID)
    assert (
        with_text_and_fallback.project_id == PID and with_text_and_fallback.text == "GateAnswered"
    )


def test_parse_new_and_ask_slash() -> None:
    with pytest.raises(LifecycleInvalid, match="usage: `/new"):
        HUB_CHAT.parse("/new")

    named = HUB_CHAT.parse("/new demo-app build a cli calculator")
    assert named.kind == "start_project"
    assert named.name == "demo-app"
    assert named.intake == "build a cli calculator"

    name_only = HUB_CHAT.parse("/new demo-only")
    assert name_only.name == "demo-only" and name_only.intake == ""

    asked = HUB_CHAT.parse("/ask Build a clean markdown parser!")
    assert asked.kind == "start_project"
    assert asked.name == "build-a-clean-markdown"
    assert asked.intake == "Build a clean markdown parser!"

    symbols_only = HUB_CHAT.parse("/ask !!!")
    assert symbols_only.name == "task"

    long_word = HUB_CHAT.parse("/ask " + ("a" * 60))
    assert len(long_word.name or "") == 48


def test_parse_abandon_slash() -> None:
    with pytest.raises(LifecycleInvalid, match="select a project"):
        HUB_CHAT.parse("/abandon no longer needed")

    with pytest.raises(LifecycleInvalid, match="give a reason"):
        HUB_CHAT.parse(f"/abandon {PID} --dry-run")

    preview = HUB_CHAT.parse("/abandon obsolete spike", project_id=PID)
    assert preview.kind == "abandon_project"
    assert preview.project_id == PID
    assert preview.reason == "obsolete spike"
    assert preview.dry_run is True

    confirmed = HUB_CHAT.parse(f"/abandon {OTHER_PID} --confirm superseded by v2", project_id=PID)
    assert confirmed.project_id == OTHER_PID
    assert confirmed.reason == "superseded by v2"
    assert confirmed.dry_run is False


def test_parse_answer_slash_and_gate_answers() -> None:
    with pytest.raises(LifecycleInvalid, match="usage: `/answer"):
        HUB_CHAT.parse("/answer")
    with pytest.raises(LifecycleInvalid, match="usage: `/answer"):
        HUB_CHAT.parse(f"/answer {GID}")
    with pytest.raises(LifecycleInvalid, match="specify which gate UUID"):
        HUB_CHAT.parse("/answer accept")

    open_gate = {
        "gate_id": str(GID),
        "project_id": str(PID),
        "kind": "approval",
        "prompt": "Ship it?",
        "options": ["accept", "changes"],
    }
    by_uuid_matched = HUB_CHAT.parse(f"/answer {GID} accept", open_gates=[open_gate])
    assert by_uuid_matched.gate_id == GID
    assert by_uuid_matched.answer == {"verdict": "accept"}

    by_uuid_unlisted = HUB_CHAT.parse(f"/answer {GID} accept", open_gates=[])
    assert by_uuid_unlisted.gate_id == GID
    assert by_uuid_unlisted.answer is None
    assert by_uuid_unlisted.raw_answer == "accept"

    single_open_word = HUB_CHAT.parse("/answer accept", open_gates=[open_gate])
    assert single_open_word.gate_id == GID
    assert single_open_word.answer == {"verdict": "accept"}

    single_open_index = HUB_CHAT.parse("/reply 2", open_gates=[open_gate])
    assert single_open_index.gate_id == GID
    assert single_open_index.answer == {"verdict": "changes"}

    single_open_out_of_range = HUB_CHAT.parse("/reply 9", open_gates=[open_gate])
    assert single_open_out_of_range.answer == {"verdict": "9"}


def test_parse_gate_answer_all_shapes() -> None:
    assert HUB_CHAT.parse_gate_answer("approval", '{"verdict": "accept"}') == {"verdict": "accept"}
    with pytest.raises(LifecycleInvalid, match="valid JSON object"):
        HUB_CHAT.parse_gate_answer("approval", "{bad")
    with pytest.raises(LifecycleInvalid, match="valid JSON object"):
        HUB_CHAT.parse_gate_answer("approval", "{} extra")
    assert HUB_CHAT.parse_gate_answer("question", "defaults") == {"accept_defaults": True}
    with pytest.raises(LifecycleInvalid, match="design question gate"):
        HUB_CHAT.parse_gate_answer("question", "something-else")

    assert HUB_CHAT.parse_gate_answer("approval", "accept") == {"verdict": "accept"}
    with pytest.raises(LifecycleInvalid, match="verdict options"):
        HUB_CHAT.parse_gate_answer("approval", "   ")

    assert HUB_CHAT.parse_gate_answer("choice", "local") == {"choice": "local"}
    with pytest.raises(LifecycleInvalid, match="gate's options"):
        HUB_CHAT.parse_gate_answer("choice", "")

    assert HUB_CHAT.parse_gate_answer("budget_exhausted", "25") == {"max_dollars": 25}
    assert HUB_CHAT.parse_gate_answer("budget_exhausted", "12.5") == {"max_dollars": 12.5}
    with pytest.raises(LifecycleInvalid, match="non-negative number"):
        HUB_CHAT.parse_gate_answer("budget_exhausted", "abc")
    with pytest.raises(LifecycleInvalid, match="non-negative number"):
        HUB_CHAT.parse_gate_answer("budget_exhausted", "-5")
    with pytest.raises(LifecycleInvalid, match="non-negative number"):
        HUB_CHAT.parse_gate_answer("budget_exhausted", "nan")

    assert HUB_CHAT.parse_gate_answer("delivery_exhausted", "retry") == {}
    with pytest.raises(LifecycleInvalid, match="JSON object"):
        HUB_CHAT.parse_gate_answer("custom_unknown_kind", "plain-word")


def test_parse_natural_language_shortcuts() -> None:
    assert HUB_CHAT.parse("help").kind == "help"
    assert HUB_CHAT.parse("projects").kind == "projects"
    assert HUB_CHAT.parse("open gates").kind == "gates"
    assert HUB_CHAT.parse("loops").kind == "loops"
    assert HUB_CHAT.parse("lanes").kind == "lanes"
    assert HUB_CHAT.parse("doctor").kind == "doctor"
    assert HUB_CHAT.parse("status").kind == "projects"
    assert HUB_CHAT.parse("status", project_id=PID).kind == "status"
    assert HUB_CHAT.parse("budget", project_id=PID).kind == "budget"
    assert HUB_CHAT.parse("queue", project_id=PID).kind == "queue"
    assert HUB_CHAT.parse("pause", project_id=PID).kind == "pause_work"
    assert HUB_CHAT.parse("resume", project_id=PID).kind == "start_work"
    assert HUB_CHAT.parse("what is happening right now", project_id=PID).kind == "status"
    assert HUB_CHAT.parse("what is happening right now", project_id=None).kind == "projects"

    open_gate = {
        "gate_id": str(GID),
        "project_id": str(PID),
        "kind": "choice",
        "prompt": "Deploy?",
        "options": ["local", "deploy"],
    }
    bare_num = HUB_CHAT.parse("1", project_id=PID, open_gates=[open_gate])
    assert bare_num.kind == "answer_gate"
    assert bare_num.answer == {"choice": "local"}

    # Out-of-range bare number falls through to status/projects
    out_of_range = HUB_CHAT.parse("9", project_id=PID, open_gates=[open_gate])
    assert out_of_range.kind == "status"


def test_format_gate_prompt_and_summarize_turn() -> None:
    spend_gate = {
        "gate_id": str(GID),
        "project_id": str(PID),
        "kind": "budget_exhausted",
        "prompt": "Raise cap?",
        "options": [],
    }
    plain_gate = {
        "gate_id": str(GID),
        "project_id": str(PID),
        "kind": "approval",
        "prompt": "Approve spec?",
        "options": ["accept", "changes"],
    }
    formatted_spend = HUB_CHAT.format_gate_prompt(spend_gate)
    assert formatted_spend["is_spend"] is True
    assert formatted_spend["requires_scope"] == "spend"
    assert formatted_spend["grant_key"] == "max_dollars"

    formatted_plain = HUB_CHAT.format_gate_prompt(plain_gate)
    assert formatted_plain["is_spend"] is False
    assert formatted_plain["requires_scope"] == "answer"
    assert formatted_plain["grant_key"] is None

    # Help turn
    help_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="help"),
        tool_calls=(),
        gates=(),
        project_id=None,
    )
    assert "Commands you can type" in help_turn["reply"]
    assert help_turn["project_id"] is None

    # Empty tool_calls fallback
    empty_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="projects"),
        tool_calls=(),
        gates=(),
        project_id=PID,
    )
    assert empty_turn["reply"] == "Done."
    assert empty_turn["project_id"] == str(PID)

    # Projects empty vs populated
    no_proj_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="projects"),
        tool_calls=[{"name": "vibey_projects", "result": []}],
        gates=(),
        project_id=None,
    )
    assert "No projects yet" in no_proj_turn["reply"]

    proj_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="projects"),
        tool_calls=[
            {
                "name": "vibey_projects",
                "result": [
                    {"name": "alpha", "phase": "BUILD", "open_gates": 2},
                    "non-mapping-ignored",
                ],
            }
        ],
        gates=(),
        project_id=None,
    )
    assert "alpha [BUILD] (2 open gate(s))" in proj_turn["reply"]

    # Status turn
    status_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="status"),
        tool_calls=[
            {
                "name": "vibey_status",
                "result": {"project": {"name": "alpha", "phase": "REVIEW", "cycle": 2}},
            }
        ],
        gates=[plain_gate],
        project_id=PID,
    )
    assert "alpha is in REVIEW (cycle 2) — 1 open gate(s)." in status_turn["reply"]

    # Gates turn (empty and with spend gate)
    no_gates_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="gates"),
        tool_calls=[{"name": "vibey_gates", "result": {"gates": []}}],
        gates=(),
        project_id=PID,
    )
    assert no_gates_turn["reply"] == "No open human gates."

    with_gates_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="gates"),
        tool_calls=[{"name": "vibey_gates", "result": {"gates": [spend_gate, plain_gate]}}],
        gates=[spend_gate, plain_gate],
        project_id=PID,
    )
    assert "[SPEND GATE — requires spend scope]" in with_gates_turn["reply"]

    # Answer gate turn
    ans_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="answer_gate", gate_id=GID),
        tool_calls=[
            {"name": "vibey_answer_gate", "result": {"gate_id": str(GID), "replayed": True}}
        ],
        gates=(),
        project_id=PID,
    )
    assert "(replayed)" in ans_turn["reply"]

    # Budget, queue, ledger, loops, lanes, doctor, start_project, start_work, abandon_project
    budget_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="budget"),
        tool_calls=[{"name": "vibey_budget", "result": {"dollars_spent": 4.5, "max_dollars": 10}}],
        gates=(),
        project_id=PID,
    )
    assert "Spend: $4.5 / $10." in budget_turn["reply"]

    queue_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="queue"),
        tool_calls=[{"name": "vibey_queue", "result": {"entries": [{"id": "1"}]}}],
        gates=(),
        project_id=PID,
    )
    assert "1 job(s) in the queue." in queue_turn["reply"]

    ledger_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="ledger"),
        tool_calls=[{"name": "vibey_ledger", "result": {"events": [{"seq": 1}]}}],
        gates=(),
        project_id=PID,
    )
    assert "Found 1 ledger event(s)." in ledger_turn["reply"]

    loops_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="loops"),
        tool_calls=[{"name": "vibey_loops", "result": {"loops": [{"name": "sovereignloop"}]}}],
        gates=(),
        project_id=None,
    )
    assert "1 loop(s) configured." in loops_turn["reply"]

    lanes_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="lanes"),
        tool_calls=[{"name": "vibey_lanes", "result": {"lanes": []}}],
        gates=(),
        project_id=None,
    )
    assert "0 active lane(s) on this computer." in lanes_turn["reply"]

    doctor_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="doctor"),
        tool_calls=[
            {
                "name": "vibey_doctor",
                "result": {"checks": [{"name": "database", "mark": "PASS"}]},
            }
        ],
        gates=(),
        project_id=None,
    )
    assert "Hub checks — database: PASS." in doctor_turn["reply"]

    doctor_non_list = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="doctor"),
        tool_calls=[{"name": "vibey_doctor", "result": {"checks": None}}],
        gates=(),
        project_id=None,
    )
    assert doctor_non_list["reply"] == "Done."

    start_proj_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="start_project", name="demo"),
        tool_calls=[
            {
                "name": "vibey_start_project",
                "result": {"name": "demo", "outcome": "design job 1"},
            }
        ],
        gates=(),
        project_id=PID,
    )
    assert "Started project `demo`" in start_proj_turn["reply"]

    work_turn = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="start_work"),
        tool_calls=[{"name": "vibey_start_work", "result": {"message": "worker started"}}],
        gates=(),
        project_id=PID,
    )
    assert work_turn["reply"] == "worker started"

    abandon_dry = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="abandon_project", dry_run=True),
        tool_calls=[{"name": "vibey_abandon_project", "result": {"dry_run": True}}],
        gates=(),
        project_id=PID,
    )
    assert "Dry run complete" in abandon_dry["reply"]

    abandon_real = HUB_CHAT.summarize_turn(
        intent=ChatIntent(kind="abandon_project", dry_run=False),
        tool_calls=[{"name": "vibey_abandon_project", "result": {"dry_run": False}}],
        gates=(),
        project_id=PID,
    )
    assert abandon_real["reply"] == "Project unwound."
