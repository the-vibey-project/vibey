# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpAgent`: a session's log kept through the hub, and `session/load`, `session/resume`,
`session/list` and `session/close` (SP-ACP Task 6).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

import pytest
from acp.schema import (
    CloseSessionResponse,
    ListSessionsResponse,
    LoadSessionResponse,
    ResumeSessionResponse,
)
from acp_fakes import FakeChannel, FakeHub, build_agent, text, until

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.acp_agent import AcpAgent
from vibey.application.acp.acp_session_journal import UNGRANTED
from vibey.application.acp.dto import AcpSessionContext, HubTurn, SessionEvent, SessionRecord
from vibey.domain.acp.protocol import RESOURCE_NOT_FOUND
from vibey.domain.acp.session_log import InvalidSessionCursor, UnknownAcpSession
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.hub_scope import HubScope
from vibey.domain.jsonrpc_errors import INTERNAL_ERROR, INVALID_PARAMS, INVALID_REQUEST, RpcError
from vibey.infrastructure.mcp.hub_gateway import HubGatewayError

SID = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a01"
OTHER = "0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a02"
PID = UUID("11111111-1111-4111-8111-111111111111")
IDS = (SID, "t1", "t2", "t3", "t4", "t5")
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


class LoggedChannel(FakeChannel):
    """Also logs each update, so a test can place the request's response among them."""

    def __init__(self) -> None:
        super().__init__()
        self.log: list[tuple[str, str]] = []

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        await super().notify_update(session_id, update)
        self.log.append(("update", str(update["sessionUpdate"])))


class SpyFeed:
    """The live feed, as a record of what the agent asked of it."""

    def __init__(self) -> None:
        self.attached: list[AcpSessionContext] = []
        self.detached: list[str] = []

    def attach(self, session: AcpSessionContext) -> None:
        self.attached.append(session)

    async def follow(self, session_id: str, project_id: UUID, *, after: int) -> None: ...

    def watermark(self, session_id: str) -> int:
        return 0

    async def flush(self, session_id: str) -> None: ...

    def detach(self, session_id: str) -> None:
        self.detached.append(session_id)

    async def close(self) -> None: ...


def _ev(seq: int, event_kind: str, /, **payload: Any) -> SessionEvent:
    return SessionEvent(seq=seq, kind=event_kind, payload=payload)


HISTORY = (
    _ev(1, "title", title="ship the greeter"),
    _ev(2, "user_message", text="ship the greeter"),
    _ev(3, "tool_call", toolCallId="t1-1", title="Chat", kind="other", status="pending"),
    _ev(
        4,
        "tool_call_update",
        toolCallId="t1-1",
        status="completed",
        text='{"ok": 1}',
        format="code",
    ),
    _ev(5, "agent_message", text="Done."),
    _ev(6, "mode", modeId="observe"),
    _ev(7, "attach", projectId=str(PID)),
)


def _agent(
    channel: FakeChannel | None = None,
    hub: FakeHub | None = None,
    *,
    feed: SpyFeed | None = None,
    settings: AcpSettings | None = None,
) -> tuple[AcpAgent, FakeChannel, FakeHub]:
    chosen_channel = channel or LoggedChannel()
    chosen_hub = hub or FakeHub()
    agent = build_agent(chosen_channel, chosen_hub, settings=settings, ids=IDS)
    if feed is not None:
        agent._feed = feed  # noqa: SLF001 -- a spy in place of the live feed
    return agent, chosen_channel, chosen_hub


async def _load(agent: AcpAgent, method: str = "session/load", **params: Any) -> Any:
    request = {"sessionId": SID, "cwd": "/work", "mcpServers": [], **params}
    return await agent.handle_request(method, request)


async def settle(spins: int = 30) -> None:
    for _ in range(spins):
        await asyncio.sleep(0)


# -- load and resume ------------------------------------------------------------------------


async def test_load_replays_history_before_responding() -> None:
    feed = SpyFeed()
    agent, channel, hub = _agent(feed=feed)
    assert isinstance(channel, LoggedChannel)
    hub.kept[SID] = ("/work", list(HISTORY))

    result = await _load(agent)
    channel.log.append(("response", "session/load"))

    assert channel.log == [
        ("update", "user_message_chunk"),
        ("update", "tool_call"),
        ("update", "tool_call_update"),
        ("update", "agent_message_chunk"),
        ("update", "current_mode_update"),
        ("response", "session/load"),
    ]
    assert channel.updates[0]["content"]["text"] == "ship the greeter"
    assert channel.updates[2]["content"][0]["content"]["text"] == '```\n{"ok": 1}\n```'
    assert result["modes"]["currentModeId"] == "observe"
    assert_wire_exact(LoadSessionResponse, result)

    # After the answer: the commands, then the project the log last attached to.
    await until(lambda: len(feed.attached) == 1)
    assert channel.updates[5]["sessionUpdate"] == "available_commands_update"
    (context,) = feed.attached
    assert context.project_id == PID and context.title == "ship the greeter"
    assert context.mode_id == "observe"
    await agent.close()
    assert hub.log(SID)[-1][0] == 7  # folding the log recorded nothing new


async def test_resume_does_not_replay() -> None:
    feed = SpyFeed()
    agent, channel, hub = _agent(feed=feed)
    hub.kept[SID] = ("/work", list(HISTORY))

    result = await _load(agent, "session/resume")

    assert channel.updates == []
    assert result["modes"]["currentModeId"] == "observe"
    assert_wire_exact(ResumeSessionResponse, result)
    await until(lambda: len(feed.attached) == 1)
    assert [u["sessionUpdate"] for u in channel.updates] == ["available_commands_update"]
    await agent.close()


async def test_replay_never_asks_answers_or_runs_anything() -> None:
    """Stored events that read like gates, answers and commands replay as text only: no
    permission request, no hub call but the log read, no command parsed."""
    agent, channel, hub = _agent(feed=SpyFeed())
    gate = "44444444-4444-4444-8444-444444444444"
    hub.kept[SID] = (
        "/work",
        [
            _ev(1, "user_message", text=f"/answer {gate} deploy --confirm"),
            _ev(2, "agent_message", text="/abandon --confirm everything"),
            _ev(
                3,
                "tool_call",
                toolCallId=f"t1-gate-{gate}",
                title="Answer gate: approve?",
                status="pending",
                rawInput={"verdict": "yes"},
                options=[{"optionId": "yes", "kind": "allow_once"}],
            ),
            _ev(4, "tool_call_update", toolCallId=f"t1-gate-{gate}", status="completed"),
            _ev(5, "plan", entries=[{"content": "[x](y)", "status": "pending", "priority": "low"}]),
            _ev(6, "request_permission", toolCallId="x"),
        ],
    )

    await _load(agent)
    await settle()

    assert channel.permission_requests == []
    assert hub.calls == [] and hub.tool_calls == []
    assert [call[0] for call in hub.session_calls] == ["summary", "events"]
    assert {u["sessionUpdate"] for u in channel.updates} <= {
        "user_message_chunk",
        "agent_message_chunk",
        "tool_call",
        "tool_call_update",
        "plan",
        "available_commands_update",
    }
    assert "rawInput" not in channel.updates[2] and "options" not in channel.updates[2]
    assert channel.updates[4]["entries"][0]["content"] == "\\[x\\]\\(y\\)"
    await agent.close()


@pytest.mark.parametrize("method", ["session/load", "session/resume"])
@pytest.mark.parametrize(
    "params",
    [
        {"sessionId": OTHER},  # unknown to the hub
        {"sessionId": "s"},  # not shaped like an id vibey mints
        {"sessionId": SID.upper()},
        {"sessionId": f"../{SID}"},
        {"sessionId": 7},
        {"cwd": "/elsewhere"},  # another folder's session
    ],
)
async def test_a_session_that_is_not_this_folders_is_not_found_however_it_differs(
    method: str, params: dict[str, Any]
) -> None:
    agent, channel, hub = _agent()
    hub.kept[SID] = ("/work", list(HISTORY))
    with pytest.raises(RpcError) as caught:
        await _load(agent, method, **params)
    assert caught.value.code == RESOURCE_NOT_FOUND
    assert caught.value.message == "no such session for this folder"
    assert channel.updates == [] and SID not in agent.sessions
    if params.get("sessionId") not in (OTHER, None):
        assert hub.session_calls == []  # a malformed id never reaches the hub


@pytest.mark.parametrize("cwd", [None, "relative/dir", 3])
async def test_load_needs_an_absolute_cwd(cwd: Any) -> None:
    agent, _, _ = _agent()
    with pytest.raises(RpcError) as caught:
        await _load(agent, cwd=cwd)
    assert caught.value.code == INVALID_PARAMS


async def test_a_hub_that_cannot_be_read_is_an_internal_error() -> None:
    agent, _, hub = _agent()
    hub.session_error = HubGatewayError("the hub could not be reached")
    with pytest.raises(RpcError) as caught:
        await _load(agent)
    assert caught.value.code == INTERNAL_ERROR
    assert "the hub could not be reached" in caught.value.message


async def test_a_session_with_no_log_loads_in_the_default_mode_and_looks_up_its_folder() -> None:
    agent, channel, hub = _agent()
    hub.kept[SID] = (
        "/work",
        [
            _ev(1, "mode", modeId="spend"),
            _ev(2, "attach", projectId="x"),
            _ev(3, "title", title=["not", "text"]),
        ],
    )
    result = await _load(agent)
    assert result["modes"]["currentModeId"] == "drive"
    assert agent._contexts[SID].title is None  # noqa: SLF001
    await until(lambda: len(hub.project_lookups) == 1)
    assert hub.project_lookups == [f"acp-{SID}-attach"]
    await agent.close()


async def test_a_loaded_session_continues_its_log_after_the_last_seq() -> None:
    agent, _, hub = _agent(feed=SpyFeed())
    hub.kept[SID] = ("/work", list(HISTORY))
    await _load(agent, "session/resume")
    await agent.handle_request("session/set_mode", {"sessionId": SID, "modeId": "drive"})
    await agent.close()
    assert hub.log(SID)[-1] == (8, "mode", {"modeId": "drive"})


async def test_a_live_session_is_not_found_from_another_folder() -> None:
    agent, channel, hub = _agent(feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.close()
    with pytest.raises(RpcError) as caught:
        await _load(agent, cwd="/elsewhere")
    assert caught.value.code == RESOURCE_NOT_FOUND
    assert hub.session_calls == []  # never prompted: never kept, never read


async def test_a_session_whose_log_stopped_is_still_served_but_not_kept() -> None:
    """The hub refused to keep the session: its mode switch still applies, and nothing more
    is sent for it."""
    agent, _, hub = _agent(feed=SpyFeed())
    hub.session_error = UnknownAcpSession("not kept")
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await settle()
    calls = len(hub.session_calls)
    assert (
        await agent.handle_request("session/set_mode", {"sessionId": SID, "modeId": "observe"})
        == {}
    )
    await agent.close()
    assert agent._contexts[SID].mode_id == "observe"  # noqa: SLF001
    assert len(hub.session_calls) == calls


async def test_load_of_a_live_session_keeps_its_context_and_its_offered_gates_object() -> None:
    feed = SpyFeed()
    agent, channel, hub = _agent(feed=feed)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    context = agent._contexts[SID]  # noqa: SLF001 -- the session as held
    offered = context.offered_gates
    offered.add("gate-1")
    await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("hello")]})
    context.project_id = PID
    agent._follow(context)  # noqa: SLF001 -- a project followed, as after a turn naming it
    attached = len(feed.attached)
    channel.updates.clear()

    result = await _load(agent)

    assert agent._contexts[SID] is context  # noqa: SLF001
    assert context.offered_gates is offered and offered == {"gate-1"}
    assert result["modes"]["currentModeId"] == "drive"
    replayed = [u["sessionUpdate"] for u in channel.updates]
    assert replayed[0] == "user_message_chunk" and "agent_message_chunk" in replayed
    await settle()
    assert len(feed.attached) == attached  # already followed: not attached again
    await agent.close()


# -- what a session's log keeps -------------------------------------------------------------


async def test_a_session_round_trips_through_a_new_process() -> None:
    hub = FakeHub(HubTurn(reply="Two [projects](x).", tool_calls=(), gates=(), project_id=PID))
    first, _, _ = _agent(hub=hub, feed=SpyFeed())
    await first.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await first.handle_request(
        "session/prompt", {"sessionId": SID, "prompt": [text("list\nthe projects")]}
    )
    await first.handle_request("session/set_mode", {"sessionId": SID, "modeId": "observe"})
    await first.close()
    kinds = [kind for _, kind, _ in hub.log(SID)]
    assert kinds[:2] == ["title", "user_message"]
    assert {"tool_call", "tool_call_update", "agent_message", "attach", "mode"} <= set(kinds)

    feed = SpyFeed()
    second, channel, _ = _agent(hub=hub, feed=feed)
    result = await _load(second)

    assert result["modes"]["currentModeId"] == "observe"
    shown = [
        u["content"]["text"]
        for u in channel.updates
        if "content" in u and "text" in u.get("content", {})
    ]
    assert shown[0] == "list\\\nthe projects"
    assert any("Two \\[projects\\]\\(x\\)." in text_ for text_ in shown)
    await until(lambda: len(feed.attached) == 1)
    assert feed.attached[0].project_id == PID and feed.attached[0].title == "list"
    await second.close()


async def test_the_title_is_kept_once_from_the_first_message() -> None:
    agent, _, hub = _agent(feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    for words in ("  \n first words", "second"):
        await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text(words)]})
    await agent.close()
    assert [p for _, kind, p in hub.log(SID) if kind == "title"] == [{"title": "first words"}]
    assert [p["text"] for _, kind, p in hub.log(SID) if kind == "user_message"] == [
        "  \n first words",
        "second",
    ]


async def test_a_prompt_with_no_text_keeps_no_title() -> None:
    agent, _, hub = _agent(feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.handle_request(
        "session/prompt", {"sessionId": SID, "prompt": [{"type": "image", "data": "x"}]}
    )
    await agent.close()
    kinds = [kind for _, kind, _ in hub.log(SID)]
    assert "title" not in kinds and kinds[0] == "user_message"


async def test_an_observe_session_still_keeps_its_own_record() -> None:
    """Keeping the conversation's record is not a run-class action: observe keeps it too."""
    agent, _, hub = _agent(feed=SpyFeed(), settings=AcpSettings(default_mode="observe"))
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("/status")]})
    await agent.close()
    kinds = [kind for _, kind, _ in hub.log(SID)]
    assert kinds[:2] == ["title", "user_message"] and "agent_message" in kinds


async def test_without_the_grant_prompts_work_and_the_session_is_kept_in_memory() -> None:
    hub = FakeHub(scopes=frozenset({HubScope.VIEW, HubScope.ANSWER, HubScope.RUN}))
    agent, channel, _ = _agent(hub=hub, feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    result = await agent.handle_request(
        "session/prompt", {"sessionId": SID, "prompt": [text("hello")]}
    )
    await agent.close()
    assert result == {"stopReason": "end_turn"}
    assert hub.kept == {} and hub.session_calls == []
    assert [said for said in channel.said if said.startswith("Session history")] == [
        f"Session history: {UNGRANTED}"
    ]


# -- close ----------------------------------------------------------------------------------


async def test_close_is_idempotent_and_unknown_close_is_empty_result() -> None:
    feed = SpyFeed()
    agent, _, hub = _agent(feed=feed)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("hi")]})
    for params in ({"sessionId": SID}, {"sessionId": SID}, {"sessionId": OTHER}, {}):
        result = await agent.handle_request("session/close", params)
        assert result == {}
        assert_wire_exact(CloseSessionResponse, result)
    await agent.close()
    assert feed.detached == [SID]
    assert [kind for _, kind, _ in hub.log(SID)].count("closed") == 1
    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("x")]})
    assert caught.value.code == RESOURCE_NOT_FOUND


async def test_close_cancels_the_running_turn_and_withdraws_its_permission_requests() -> None:
    hub = FakeHub()
    hub.release = asyncio.Event()
    agent, channel, _ = _agent(hub=hub, feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    prompt = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("/projects")]})
    )
    await hub.entered.wait()

    assert await agent.handle_request("session/close", {"sessionId": SID}) == {}

    # The close itself ends the turn: nothing else cancels the request that is waiting on it.
    done, _ = await asyncio.wait({prompt}, timeout=5)
    assert prompt in done
    assert prompt.result() == {"stopReason": "cancelled"}
    assert SID in channel.cancelled_permissions
    # The turn is gone: a cancel now finds nothing, and nothing is left running.
    await agent.handle_notification("session/cancel", {"sessionId": SID})
    assert agent._turns == {}  # noqa: SLF001
    hub.release.set()
    await agent.close()
    kinds = [kind for _, kind, _ in hub.log(SID)]
    assert kinds[-1] == "closed"  # what the cancelled turn said after the close is not kept


async def test_close_stops_the_feed_and_forgets_the_followed_project() -> None:
    feed = SpyFeed()
    agent, _, hub = _agent(feed=feed)
    hub.kept[SID] = ("/work", list(HISTORY))
    await _load(agent, "session/resume")
    await until(lambda: len(feed.attached) == 1)

    await agent.handle_request("session/close", {"sessionId": SID})

    assert feed.detached == [SID]
    assert agent._followed == {} and agent._kept_project == {}  # noqa: SLF001
    # Loaded again, it is followed again: the close reopened nothing it should not have.
    await _load(agent, "session/resume")
    await until(lambda: len(feed.attached) == 2)
    await agent.close()


async def test_a_closed_session_is_never_followed_again() -> None:
    """A turn that named a project and ended after the close, or any other late attach, leaves a
    closed session unfollowed and records nothing for it."""
    feed = SpyFeed()
    agent, _, hub = _agent(feed=feed)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("hi")]})
    context = agent._contexts[SID]  # noqa: SLF001 -- the session as held
    await agent.handle_request("session/close", {"sessionId": SID})
    context.project_id = PID

    agent._follow(context)  # noqa: SLF001 -- what the end of a late turn does

    assert feed.attached == [] and agent._followed == {}  # noqa: SLF001
    await agent.close()
    assert [kind for _, kind, _ in hub.log(SID)][-1] == "closed"
    assert "attach" not in [kind for _, kind, _ in hub.log(SID)]


async def test_a_folder_lookup_that_ends_after_the_close_follows_nothing() -> None:
    feed = SpyFeed()
    hub = FakeHub()
    hub.projects_release = asyncio.Event()
    agent, channel, _ = _agent(hub=hub, feed=feed)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await until(lambda: len(hub.project_lookups) == 1)
    await agent.handle_request("session/close", {"sessionId": SID})
    hub.projects = hub.projects.__class__(
        ok=True,
        status_code=200,
        text=f'[{{"project_id": "{PID}", "name": "p", "repo_path": "/work"}}]',
    )
    hub.projects_release.set()
    await settle()
    assert feed.attached == []
    assert not any("Following project" in said for said in channel.said)
    await agent.close()


# -- list -----------------------------------------------------------------------------------


def _record(session_id: str, title: str | None = None, cwd: str = "/work") -> SessionRecord:
    return SessionRecord(session_id=session_id, cwd=cwd, title=title, updated_at=NOW, closed=False)


async def test_list_maps_to_acp_shape_and_validates() -> None:
    agent, _, hub = _agent()
    hub.listing = (
        (
            _record(SID, "fix\nthe [bug](x)‮"),
            _record(OTHER),
            _record("not-a-session"),
            _record("0f6f4c1e-8d6b-4f0e-9a51-6b1f3f1f9a03", cwd="relative"),
        ),
        "next-page",
    )
    result = await agent.handle_request("session/list", {"cwd": "/work", "cursor": "c1"})

    assert hub.list_calls == [("/work", "c1")]
    assert result == {
        "sessions": [
            {
                "sessionId": SID,
                "cwd": "/work",
                "updatedAt": NOW.isoformat(),
                "title": "fix",
            },
            {"sessionId": OTHER, "cwd": "/work", "updatedAt": NOW.isoformat()},
        ],
        "nextCursor": "next-page",
    }
    assert_wire_exact(ListSessionsResponse, result)


async def test_the_last_list_page_has_no_cursor() -> None:
    agent, _, hub = _agent()
    hub.listing = ((_record(SID, "t‮itle"),), None)
    result = await agent.handle_request("session/list", {})
    assert hub.list_calls == [(None, None)]
    assert result["sessions"][0]["title"] == "t itle"
    assert "nextCursor" not in result
    assert_wire_exact(ListSessionsResponse, result)


@pytest.mark.parametrize(
    "params", [{"cwd": "relative"}, {"cwd": 3}, {"cursor": 3}, {"cursor": ["x"]}]
)
async def test_list_refuses_malformed_params(params: dict[str, Any]) -> None:
    agent, _, hub = _agent()
    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/list", params)
    assert caught.value.code == INVALID_PARAMS and hub.list_calls == []


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (InvalidSessionCursor("that cursor is not one the hub gave out"), INVALID_PARAMS),
        (HubGatewayError("the hub could not be reached"), INTERNAL_ERROR),
    ],
)
async def test_a_list_the_hub_refuses_is_an_error(error: Exception, code: int) -> None:
    agent, _, hub = _agent()
    hub.list_error = error
    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/list", {"cursor": "x"})
    assert caught.value.code == code


# -- fix round 1: load and close of one session are never interleaved -----------------------


class SlowHub(FakeHub):
    """A hub whose session reads wait until `release` is set."""

    def __init__(self) -> None:
        super().__init__()
        self.reading = asyncio.Event()
        self.release_reads = asyncio.Event()

    async def session_summary(self, session_id: str, *, cwd: str) -> Any:
        self.reading.set()
        await self.release_reads.wait()
        return await super().session_summary(session_id, cwd=cwd)


async def test_a_close_during_a_load_never_leaves_a_closed_session_installed() -> None:
    hub = SlowHub()
    feed = SpyFeed()
    agent, _, _ = _agent(hub=hub, feed=feed)
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("hi")]})
    await settle()
    loading = asyncio.create_task(_load(agent))
    await hub.reading.wait()
    closing = asyncio.create_task(agent.handle_request("session/close", {"sessionId": SID}))
    await settle()
    assert not closing.done()  # the close waits for the load of the same session
    hub.release_reads.set()
    assert (await loading)["modes"]["currentModeId"] == "drive"
    assert await closing == {}
    assert SID not in agent.sessions
    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("x")]})
    assert caught.value.code == RESOURCE_NOT_FOUND
    await agent.close()


async def test_two_overlapping_loads_end_on_one_context_and_one_offered_gates_object() -> None:
    hub = SlowHub()
    hub.kept[SID] = ("/work", list(HISTORY))
    feed = SpyFeed()
    agent, _, _ = _agent(hub=hub, feed=feed)
    first = asyncio.create_task(_load(agent, "session/resume"))
    second = asyncio.create_task(_load(agent, "session/resume"))
    await hub.reading.wait()
    hub.release_reads.set()
    await asyncio.gather(first, second)
    await until(lambda: len(feed.attached) >= 1)
    await settle()
    held = agent._contexts[SID]  # noqa: SLF001
    assert all(context is held for context in feed.attached)
    assert all(context.offered_gates is held.offered_gates for context in feed.attached)
    await agent.close()


async def test_a_load_while_a_turn_runs_is_refused() -> None:
    hub = FakeHub()
    hub.release = asyncio.Event()
    agent, _, _ = _agent(hub=hub, feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    turn = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": SID, "prompt": [text("/projects")]})
    )
    await hub.entered.wait()
    with pytest.raises(RpcError) as caught:
        await _load(agent)
    assert caught.value.code == INVALID_REQUEST
    hub.release.set()
    await turn
    await agent.close()


async def test_a_load_replays_only_the_newest_events_and_says_the_rest_were_skipped() -> None:
    feed = SpyFeed()
    agent, channel, hub = _agent(feed=feed, settings=AcpSettings(replay_events_max=2))
    hub.kept[SID] = ("/work", list(HISTORY))  # 7 events: mode at 6, attach at 7
    result = await _load(agent)
    shown = [u["sessionUpdate"] for u in channel.updates]
    assert shown[:2] == ["agent_message_chunk", "current_mode_update"]
    assert "newest 2 events; up to 5 before them are kept but not shown" in channel.said[0]
    assert ("events", SID, "/work") in hub.session_calls
    # Folded from the summary, not from what was replayed: the title is at seq 1.
    assert result["modes"]["currentModeId"] == "observe"
    await until(lambda: len(feed.attached) == 1)
    assert feed.attached[0].title == "ship the greeter" and feed.attached[0].project_id == PID
    await agent.close()


async def test_a_resume_reads_only_the_summary() -> None:
    agent, _, hub = _agent(feed=SpyFeed())
    hub.kept[SID] = ("/work", list(HISTORY))
    await _load(agent, "session/resume")
    assert [call[0] for call in hub.session_calls] == ["summary"]
    await agent.close()


async def test_a_live_session_the_hub_does_not_keep_loads_from_its_context() -> None:
    """Never prompted, so never kept: a load in the same process answers from the session as
    it is, with nothing to show."""
    agent, channel, _ = _agent(feed=SpyFeed())
    await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": []})
    await settle()
    channel.updates.clear()
    result = await _load(agent)
    assert result["modes"]["currentModeId"] == "drive"
    assert not any(u["sessionUpdate"].endswith("message_chunk") for u in channel.updates)
    await agent.close()


async def test_a_listed_folder_the_one_line_rule_would_change_is_passed_over() -> None:
    agent, _, hub = _agent()
    hub.listing = ((_record(SID, cwd="/work‮"), _record(OTHER, cwd="/a\nb")), None)
    assert await agent.handle_request("session/list", {}) == {"sessions": []}


async def test_no_lock_outlives_the_loads_and_closes_that_used_it() -> None:
    hub = SlowHub()
    hub.kept[SID] = ("/work", list(HISTORY))
    agent, _, _ = _agent(hub=hub, feed=SpyFeed())
    first = asyncio.create_task(_load(agent, "session/resume"))
    second = asyncio.create_task(_load(agent, "session/resume"))
    await hub.reading.wait()
    assert set(agent._locks) == {SID}  # noqa: SLF001 -- held while the loads run
    hub.release_reads.set()
    await asyncio.gather(first, second)
    assert agent._locks == {} and agent._lock_users == {}  # noqa: SLF001
    await agent.handle_request("session/close", {"sessionId": SID})
    assert agent._locks == {} and agent._lock_users == {}  # noqa: SLF001
    await agent.close()


async def test_a_session_in_a_folder_the_hub_refuses_never_blocks_another_sessions_log() -> None:
    """A folder with a zero-width joiner (an emoji family name) is not printable: that session is
    kept in its window only, and the other session's log reaches the hub in order."""
    bad, good = SID, OTHER
    hub = FakeHub()
    channel = FakeChannel()
    agent = build_agent(channel, hub, ids=(bad, good, "t1", "t2", "t3", "t4"))
    agent._feed = SpyFeed()  # noqa: SLF001
    await agent.handle_request("session/new", {"cwd": "/bad\u200dfolder", "mcpServers": []})
    await agent.handle_request("session/new", {"cwd": "/good", "mcpServers": []})
    for session_id in (bad, good):
        await agent.handle_request(
            "session/prompt", {"sessionId": session_id, "prompt": [text("hello")]}
        )
    await agent.close()
    assert set(hub.kept) == {good}
    assert [kind for _, kind, _ in hub.log(good)][:2] == ["title", "user_message"]
    told = [
        session_id
        for session_id, update in zip(channel.sessions, channel.updates, strict=True)
        if update["sessionUpdate"] == "agent_message_chunk"
        and "its folder holds a character" in update["content"]["text"]
    ]
    assert told == [bad]
