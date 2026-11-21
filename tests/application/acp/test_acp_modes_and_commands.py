# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpAgent`: slash commands, `session/set_mode`, and following a project's ledger (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

import pytest
from acp.schema import AvailableCommandsUpdate, CurrentModeUpdate, SetSessionModeResponse
from acp_fakes import FakeChannel, FakeHub, build_agent, event, text, until

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.acp_agent import AcpAgent
from vibey.application.acp.dto import HubToolResult, HubTurn
from vibey.domain.acp.protocol import RESOURCE_NOT_FOUND
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_chat import CHAT_SLASH_COMMANDS
from vibey.domain.jsonrpc_errors import INVALID_PARAMS, RpcError
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError

PID = UUID("11111111-1111-4111-8111-111111111111")
NESTED = UUID("22222222-2222-4222-8222-222222222222")
CHAT_PID = UUID("33333333-3333-4333-8333-333333333333")
GATE = "44444444-4444-4444-8444-444444444444"


def projects(*rows: tuple[UUID, str]) -> HubToolResult:
    body = [{"project_id": str(pid), "name": "p", "repo_path": repo} for pid, repo in rows]
    return HubToolResult(ok=True, status_code=200, text=json.dumps(body))


async def new_session(agent: AcpAgent, cwd: str = "/work") -> str:
    result = await agent.handle_request("session/new", {"cwd": cwd, "mcpServers": []})
    return str(result["sessionId"])


def updates_of(channel: FakeChannel, kind: str) -> list[dict[str, Any]]:
    return [update for update in channel.updates if update["sessionUpdate"] == kind]


def project_of(agent: AcpAgent, session_id: str = "s") -> UUID | None:
    return agent._contexts[session_id].project_id  # noqa: SLF001 -- the session as held


async def settle(spins: int = 20) -> None:
    for _ in range(spins):
        await asyncio.sleep(0)


async def test_available_commands_follow_session_new() -> None:
    channel = FakeChannel()
    agent = build_agent(channel, FakeHub())

    await new_session(agent)
    assert channel.updates == []  # the response is written first
    await until(lambda: len(channel.updates) >= 1)

    first = channel.updates[0]
    assert channel.sessions[0] == "s"
    assert first["sessionUpdate"] == "available_commands_update"
    assert {c["name"] for c in first["availableCommands"]} == {s.slash for s in CHAT_SLASH_COMMANDS}
    assert_wire_exact(AvailableCommandsUpdate, first)
    await agent.close()


async def test_set_mode_rejects_unknown_mode() -> None:
    agent = build_agent(FakeChannel(), FakeHub(), settings=AcpSettings(modes=("drive",)))
    session_id = await new_session(agent)

    for mode in ("observe", "spend", None):
        with pytest.raises(RpcError) as caught:
            await agent.handle_request(
                "session/set_mode", {"sessionId": session_id, "modeId": mode}
            )
        assert caught.value.code == INVALID_PARAMS
    assert agent._contexts["s"].mode_id == "drive"  # noqa: SLF001
    await agent.close()


async def test_set_mode_on_an_unknown_session_is_resource_not_found() -> None:
    agent = build_agent(FakeChannel(), FakeHub())

    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/set_mode", {"sessionId": "zz", "modeId": "observe"})

    assert caught.value.code == RESOURCE_NOT_FOUND


async def test_set_mode_sends_current_mode_update_and_changes_scopes() -> None:
    channel, hub = FakeChannel(), FakeHub()
    agent = build_agent(channel, hub)
    session_id = await new_session(agent)

    result = await agent.handle_request(
        "session/set_mode", {"sessionId": session_id, "modeId": "observe"}
    )
    await until(lambda: bool(updates_of(channel, "current_mode_update")))

    assert result == {}
    assert_wire_exact(SetSessionModeResponse, dict(result))
    mode_update = updates_of(channel, "current_mode_update")[0]
    assert mode_update == {"sessionUpdate": "current_mode_update", "currentModeId": "observe"}
    assert_wire_exact(CurrentModeUpdate, mode_update)
    reply = await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text(f"/start {PID}")]}
    )
    assert reply == {"stopReason": "end_turn"}
    assert hub.calls == []  # observe may not start work
    assert "needs drive mode" in channel.said[-1]
    await agent.close()


async def test_gates_held_back_in_observe_come_up_after_switching_to_drive() -> None:
    channel, hub = FakeChannel(), FakeHub()
    gate = {"gate_id": GATE, "kind": "approval", "prompt": "Ship?", "options": ["yes", "no"]}
    hub.turn = HubTurn(reply="One gate.", tool_calls=(), gates=(gate,), project_id=None)
    agent = build_agent(channel, hub, settings=AcpSettings(default_mode="observe"))
    session_id = await new_session(agent)

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )
    assert channel.permission_requests == []  # observe never offers a gate
    await agent.handle_request("session/set_mode", {"sessionId": session_id, "modeId": "drive"})
    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )

    assert len(channel.permission_requests) == 1
    assert channel.permission_requests[0]["tool_call"]["toolCallId"].endswith(GATE)
    await agent.close()


async def test_cwd_inside_a_project_repo_attaches_the_session() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"), (NESTED, "/work/app"), (CHAT_PID, "/elsewhere"))
    hub.ledger = [event(1, phase="design"), event(2, phase="build")]
    agent = build_agent(channel, hub)

    session_id = await new_session(agent, "/work/app/src")
    await until(lambda: bool(updates_of(channel, "plan")))

    assert project_of(agent) == NESTED  # the longest matching repo wins
    assert hub.project_lookups == [f"acp-{session_id}-attach"]
    assert {call[0] for call in hub.ledger_calls} == {NESTED}
    kinds = [update["sessionUpdate"] for update in channel.updates]
    assert kinds[:3] == ["available_commands_update", "agent_message_chunk", "plan"]
    assert channel.said[0] == (
        f"Following project p ({NESTED}) from /work/app. A bare `/start`, `/pause` or "
        "`/abandon` in this session now targets it."
    )
    hub.ledger.append(event(3, summary="tests pass"))
    await until(lambda: "[build] TurnCompleted: tests pass" in channel.said)
    await agent.close()


async def test_the_attached_project_is_the_one_prompts_name() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    agent = build_agent(channel, hub)
    session_id = await new_session(agent, "/work")
    await until(lambda: project_of(agent) == PID)

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/status")]}
    )

    assert hub.calls[0].project_id == PID
    await agent.close()


@pytest.mark.parametrize(
    "answer",
    [
        projects((PID, "/work/other")),
        projects((PID, "/wor")),
        projects((PID, "relative/work")),
        HubToolResult(
            ok=True, status_code=200, text='[{"project_id": "nope", "repo_path": "/work"}]'
        ),
        HubToolResult(ok=True, status_code=200, text='[3, {"repo_path": 4, "project_id": "x"}]'),
        HubToolResult(ok=True, status_code=200, text='{"projects": []}'),
        HubToolResult(ok=True, status_code=200, text="not json"),
    ],
)
async def test_a_cwd_outside_every_project_attaches_nothing(answer: HubToolResult) -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = answer
    agent = build_agent(channel, hub)

    await new_session(agent, "/work")
    await until(lambda: len(hub.project_lookups) == 1)
    await settle()

    assert project_of(agent) is None
    assert hub.ledger_calls == []
    assert [u["sessionUpdate"] for u in channel.updates] == ["available_commands_update"]
    await agent.close()


@pytest.mark.parametrize(
    ("hub_answer", "said"),
    [
        (HubGatewayError("the hub did not answer"), "the hub did not answer"),
        (HubToolResult(ok=False, status_code=403, text="no"), "answered 403"),
    ],
)
async def test_a_project_lookup_that_fails_is_said_once(hub_answer: Any, said: str) -> None:
    channel, hub = FakeChannel(), FakeHub()
    if isinstance(hub_answer, Exception):
        hub.projects_error = hub_answer
    else:
        hub.projects = hub_answer
    agent = build_agent(channel, hub)

    await new_session(agent)
    await until(lambda: len(channel.said) == 1)

    assert said in channel.said[0] and "/projects" in channel.said[0]
    assert project_of(agent) is None
    await agent.close()


async def test_a_turn_that_names_another_project_moves_the_feed() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    agent = build_agent(channel, hub)
    session_id = await new_session(agent, "/work")
    await until(lambda: bool(hub.ledger_calls))

    hub.turn = HubTurn(reply="Status.", tool_calls=(), gates=(), project_id=CHAT_PID)
    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/status")]}
    )
    hub.ledger_calls.clear()
    await until(lambda: len(hub.ledger_calls) >= 3)

    assert project_of(agent) == CHAT_PID
    assert {call[0] for call in hub.ledger_calls} == {CHAT_PID}
    await agent.close()


async def test_a_turn_on_the_same_project_does_not_restart_the_feed() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    hub.ledger = [event(1, phase="build")]
    agent = build_agent(channel, hub)
    session_id = await new_session(agent, "/work")
    await until(lambda: bool(updates_of(channel, "plan")))

    hub.turn = HubTurn(reply="Status.", tool_calls=(), gates=(), project_id=PID)
    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/status")]}
    )
    await settle(50)

    assert len(updates_of(channel, "plan")) == 1  # no second catch-up
    await agent.close()


async def test_the_hubs_project_wins_over_a_late_cwd_lookup() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    hub.projects_release = asyncio.Event()  # the lookup waits
    hub.turn = HubTurn(reply="Status.", tool_calls=(), gates=(), project_id=CHAT_PID)
    agent = build_agent(channel, hub)
    session_id = await new_session(agent, "/work")
    await until(lambda: len(hub.project_lookups) == 1)

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/projects")]}
    )
    hub.projects_release.set()
    await settle(50)

    assert project_of(agent) == CHAT_PID
    assert {call[0] for call in hub.ledger_calls} == {CHAT_PID}
    await agent.close()


async def test_events_held_between_turns_reach_the_client_when_the_next_turn_starts() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    hub.ledger = [event(1, phase="build")]
    agent = build_agent(channel, hub, settings=AcpSettings(live_between_turns=False))
    session_id = await new_session(agent, "/work")
    await until(lambda: bool(updates_of(channel, "plan")))
    hub.ledger.append(event(2, summary="held"))
    await settle(50)
    assert "[build] TurnCompleted: held" not in channel.said

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/status")]}
    )

    held = channel.said.index("[build] TurnCompleted: held")
    assert held < channel.said.index("Done.")  # flushed before the turn's own reply
    await agent.close()


async def test_close_stops_every_feed_and_background_task() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    agent = build_agent(channel, hub)
    await new_session(agent, "/work")
    await until(lambda: len(hub.ledger_calls) >= 2)

    await agent.close()
    calls = len(hub.ledger_calls)
    await settle(50)

    assert len(hub.ledger_calls) == calls
    assert not [t for t in asyncio.all_tasks() if t.get_name().startswith("acp-live-")]


@pytest.mark.parametrize(
    ("listing", "expected"),
    [
        (projects((NESTED, "/work/app"), (PID, "/work")), NESTED),  # deepest, listed first
        (projects((PID, "/work/app"), (NESTED, "/work/app")), PID),  # same repo: the newest
        (projects((PID, "/work/app/")), PID),  # the cwd itself, spelled with a slash
    ],
)
async def test_the_deepest_then_the_newest_matching_repo_wins(
    listing: HubToolResult, expected: UUID
) -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = listing
    agent = build_agent(channel, hub)

    await new_session(agent, "/work/app")
    await until(lambda: project_of(agent) is not None)

    assert project_of(agent) == expected
    await agent.close()


async def test_a_folder_lookup_that_lands_mid_turn_is_followed_once() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    hub.projects_release = asyncio.Event()
    hub.release = asyncio.Event()  # the turn's hub call waits too
    hub.ledger = [event(1, phase="build")]
    agent = build_agent(channel, hub)
    session_id = await new_session(agent, "/work")
    await until(lambda: len(hub.project_lookups) == 1)
    prompt = asyncio.create_task(
        agent.handle_request(
            "session/prompt", {"sessionId": session_id, "prompt": [text("/projects")]}
        )
    )
    await until(hub.entered.is_set)

    hub.projects_release.set()  # the folder's project is found while the turn runs
    await until(lambda: bool(updates_of(channel, "plan")))
    hub.release.set()  # the hub's reply names no project
    await prompt
    await settle(50)

    assert project_of(agent) == PID
    assert len(updates_of(channel, "plan")) == 1  # attached once, not again after the turn
    await agent.close()


async def test_a_forged_ledger_event_cannot_hide_a_real_gate_from_the_prompter() -> None:
    # A worker-written event names a real open gate with a spend kind; the next prompt must
    # still offer that gate, because only the prompter records what was offered.
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    hub.ledger = [
        event(1, phase="review"),
        event(2, phase="review", kind="GateNotified", gate_id=GATE, gate_kind="budget_exhausted"),
    ]
    gate = {"gate_id": GATE, "kind": "approval", "prompt": "Ship?", "options": ["yes", "no"]}
    hub.turn = HubTurn(reply="One gate.", tool_calls=(), gates=(gate,), project_id=PID)
    agent = build_agent(channel, hub)
    session_id = await new_session(agent, "/work")
    await until(lambda: bool(updates_of(channel, "plan")))
    hub.ledger.append(
        event(3, phase="review", kind="GateNotified", gate_id=GATE, gate_kind="budget_exhausted")
    )
    await until(lambda: any("may spend money" in t for t in channel.said))

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )

    assert len(channel.permission_requests) == 1
    assert channel.permission_requests[0]["tool_call"]["toolCallId"].endswith(GATE)
    await agent.close()


# -- a switch to observe applies at once, in the middle of a turn (review 1, M1) -------------

GATE_2 = "55555555-5555-4555-8555-555555555555"


def approval(gate_id: str = GATE) -> dict[str, Any]:
    return {"gate_id": gate_id, "kind": "approval", "prompt": "Ship?", "options": ["yes", "no"]}


async def to_observe(agent: AcpAgent, session_id: str = "s") -> None:
    reply = await agent.handle_request(
        "session/set_mode", {"sessionId": session_id, "modeId": "observe"}
    )
    assert reply == {}


async def test_a_downgrade_withdraws_a_permission_request_that_is_out() -> None:
    channel, hub = FakeChannel(), FakeHub()
    channel.permission_block = True  # the client has not answered yet
    hub.turn = HubTurn(reply="One gate.", tool_calls=(), gates=(approval(),), project_id=None)
    agent = build_agent(channel, hub)
    session_id = await new_session(agent)
    prompt = asyncio.create_task(
        agent.handle_request(
            "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
        )
    )
    await asyncio.wait_for(channel.permission_asked.wait(), 5)

    await to_observe(agent, session_id)
    result = await asyncio.wait_for(prompt, 5)

    assert result == {"stopReason": "end_turn"}
    assert channel.cancelled_permissions == [session_id]
    assert hub.tool_calls == []  # nothing answered
    assert any(t.startswith(f"Nothing was answered for gate {GATE}") for t in channel.said)
    assert GATE not in agent._contexts["s"].offered_gates  # noqa: SLF001 -- asked again later
    await agent.handle_request("session/set_mode", {"sessionId": session_id, "modeId": "drive"})
    channel.permission_block = False
    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )
    assert len(channel.permission_requests) == 2
    await agent.close()


async def test_an_answer_picked_after_a_downgrade_answers_nothing() -> None:
    # A client that does not honour the withdrawal and sends its pick anyway.
    class LatePick(FakeChannel):
        agent: AcpAgent

        async def request_permission(
            self, session_id: str, tool_call: Any, options: Any, *, timeout: float
        ) -> str | None:
            self.permission_requests.append({"tool_call": dict(tool_call)})
            await to_observe(self.agent, session_id)
            return f"{GATE}:0"  # "yes", picked after the switch

        def cancel_permissions(self, session_id: str) -> tuple[str, ...]:
            self.cancelled_permissions.append(session_id)
            return ()

    channel, hub = LatePick(), FakeHub()
    hub.turn = HubTurn(reply="One gate.", tool_calls=(), gates=(approval(),), project_id=None)
    agent = build_agent(channel, hub)
    channel.agent = agent
    session_id = await new_session(agent)

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )

    assert hub.tool_calls == []
    gate_updates = [u for u in channel.updates if str(u.get("toolCallId", "")).endswith(GATE)]
    assert gate_updates[-1]["status"] == "failed"
    assert [t for t in channel.said if t.startswith("Nothing was answered")] == [
        f"Nothing was answered for gate {GATE}: the session left drive mode while it was being "
        "asked. It is asked again after a switch back to drive."
    ]
    await agent.close()


async def test_a_downgrade_between_two_gates_stops_the_second_offer() -> None:
    class SwitchAfterFirst(FakeChannel):
        agent: AcpAgent

        async def notify_update(self, session_id: str, update: Any) -> None:
            await super().notify_update(session_id, update)
            first_gate = str(update.get("toolCallId", "")).endswith(GATE)
            if first_gate and update.get("status") == "completed":
                await to_observe(self.agent, session_id)

    channel, hub = SwitchAfterFirst(), FakeHub()
    channel.permission_answers = [f"{GATE}:0"]
    gates = (approval(GATE), approval(GATE_2))
    hub.turn = HubTurn(reply="Two gates.", tool_calls=(), gates=gates, project_id=None)
    agent = build_agent(channel, hub)
    channel.agent = agent
    session_id = await new_session(agent)

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )

    assert [call[1]["gate_id"] for call in hub.tool_calls] == [GATE]  # only the first
    assert len(channel.permission_requests) == 1
    assert GATE_2 not in agent._contexts["s"].offered_gates  # noqa: SLF001 -- offered in drive
    await agent.close()


async def test_a_downgrade_between_admission_and_the_hub_call_stops_the_call() -> None:
    class SwitchOnAnnounce(FakeChannel):
        agent: AcpAgent

        async def notify_update(self, session_id: str, update: Any) -> None:
            await super().notify_update(session_id, update)
            if update.get("sessionUpdate") == "tool_call":
                await to_observe(self.agent, session_id)

    channel, hub = SwitchOnAnnounce(), FakeHub()
    agent = build_agent(channel, hub)
    channel.agent = agent
    session_id = await new_session(agent)

    reply = await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text(f"/start {PID}")]}
    )

    assert reply == {"stopReason": "end_turn"}
    assert hub.calls == []  # admitted under drive, never sent under observe
    closed = [u for u in channel.updates if u["sessionUpdate"] == "tool_call_update"][-1]
    assert closed["status"] == "failed"
    assert "needs drive mode" in closed["content"][0]["content"]["text"]
    assert "needs drive mode" in channel.said[-1]
    await agent.close()


# -- review 1, S1 and N4 ---------------------------------------------------------------------


async def test_a_defect_in_the_folder_lookup_is_said_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects_error = TypeError("a bug in the listing")
    agent = build_agent(channel, hub)

    await new_session(agent)
    await until(lambda: len(channel.texts) == 1)

    assert channel.said[0].startswith("vibey could not follow this folder's project: TypeError.")
    assert "a bug in the listing" in caplog.text and "Traceback" in caplog.text
    assert project_of(agent) is None
    await agent.close()


async def test_a_failed_background_update_is_read_and_logged(
    caplog: pytest.LogCaptureFixture,
) -> None:
    class Gone(FakeChannel):
        async def notify_update(self, session_id: str, update: Any) -> None:
            raise BrokenPipeError("client went away")

    agent = build_agent(Gone(), FakeHub())

    await new_session(agent)
    await settle()

    assert "a background ACP update failed" in caplog.text and "BrokenPipeError" in caplog.text
    await agent.close()


async def test_a_hub_error_in_the_folder_lookup_is_shown_as_safe_text() -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects_error = HubGatewayError("down [x](https://e)\nmore")
    agent = build_agent(channel, hub)

    await new_session(agent)
    await until(lambda: len(channel.texts) == 1)

    assert "down \\[x\\]\\(https\\[:\\]//e\\) more" in channel.said[0]
    await agent.close()


@pytest.mark.parametrize("cwd", ["/work/../etc", "/work/app/../../etc"])
async def test_a_cwd_with_a_parent_step_attaches_nothing(cwd: str) -> None:
    channel, hub = FakeChannel(), FakeHub()
    hub.projects = projects((PID, "/work"))
    agent = build_agent(channel, hub)

    await new_session(agent, cwd)
    await until(lambda: len(hub.project_lookups) == 1)
    await settle()

    assert project_of(agent) is None and hub.ledger_calls == []
    await agent.close()


async def test_the_following_message_shows_hub_data_as_safe_text() -> None:
    channel, hub = FakeChannel(), FakeHub()
    body = [{"project_id": str(PID), "name": "[evil](https://e)\n# x", "repo_path": "/work"}]
    hub.projects = HubToolResult(ok=True, status_code=200, text=json.dumps(body))
    agent = build_agent(channel, hub)

    await new_session(agent, "/work")
    await until(lambda: any(t.startswith("Following project") for t in channel.said))

    following = next(t for t in channel.said if t.startswith("Following project"))
    assert following.startswith("Following project \\[evil\\]\\(https\\[:\\]//e\\) \\# x (")
    await agent.close()


async def test_a_downgrade_while_the_in_progress_frame_is_written_answers_nothing() -> None:
    # Review 2, R2-M1: the switch lands while the gate's `in_progress` update waits to be
    # written (a slow stdout); the answer must not be sent after it.
    class SwitchDuringInProgress(FakeChannel):
        agent: AcpAgent

        async def notify_update(self, session_id: str, update: Any) -> None:
            is_gate = str(update.get("toolCallId", "")).endswith(GATE)
            if is_gate and update.get("status") == "in_progress":
                await to_observe(self.agent, session_id)  # handled while this write waits
            await super().notify_update(session_id, update)

    channel, hub = SwitchDuringInProgress(), FakeHub()
    channel.permission_answers = [f"{GATE}:0"]  # "yes", picked while still in drive
    hub.turn = HubTurn(reply="One gate.", tool_calls=(), gates=(approval(),), project_id=None)
    agent = build_agent(channel, hub)
    channel.agent = agent
    session_id = await new_session(agent)

    await agent.handle_request(
        "session/prompt", {"sessionId": session_id, "prompt": [text("/gates")]}
    )

    assert hub.tool_calls == []  # no vibey_answer_gate
    gate_updates = [u for u in channel.updates if str(u.get("toolCallId", "")).endswith(GATE)]
    assert gate_updates[-1]["status"] == "failed"
    assert any(t.startswith(f"Nothing was answered for gate {GATE}") for t in channel.said)
    await agent.close()
