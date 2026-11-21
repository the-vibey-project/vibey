# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`AcpAgent`: initialize, authenticate, session/new, session/prompt dispatch and cancel (SP-ACP).

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from typing import Any

import pytest
from acp.schema import InitializeResponse, NewSessionResponse, PromptResponse
from acp_fakes import FakeChannel, FakeHub, build_agent, text, until

from tests.domain.acp.acp_wire import assert_wire_exact
from vibey.application.acp.acp_agent import AcpAgent
from vibey.application.acp.acp_live_feed import AcpLiveFeed
from vibey.application.acp.dto import AcpSessionContext
from vibey.application.acp.interfaces.acp_agent_interface import AcpAgentInterface
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.protocol import RESOURCE_NOT_FOUND, StopReason
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.domain.host_tools import HOST_TOOL_CATALOG
from vibey.domain.hub_chat import HUB_CHAT
from vibey.domain.jsonrpc_errors import INVALID_PARAMS, INVALID_REQUEST, METHOD_NOT_FOUND, RpcError

INITIALIZE_RESULT = {
    "protocolVersion": 1,
    "agentCapabilities": {
        "loadSession": True,
        "promptCapabilities": {"image": False, "audio": False, "embeddedContext": True},
        "mcpCapabilities": {"http": False, "sse": False},
        "sessionCapabilities": {"list": {}, "close": {}, "resume": {}},
    },
    "agentInfo": {"name": "vibey", "title": "vibey", "version": "9.9.9"},
    "authMethods": [],
}


async def _new_session(agent: AcpAgent, **params: Any) -> Mapping[str, Any]:
    return await agent.handle_request("session/new", {"cwd": "/work", "mcpServers": [], **params})


def test_the_agent_satisfies_its_interface() -> None:
    assert isinstance(build_agent(FakeChannel(), FakeHub()), AcpAgentInterface)


async def test_initialize_advertises_v1_and_the_capability_set() -> None:
    agent = build_agent(FakeChannel(), FakeHub())

    result = await agent.handle_request(
        "initialize", {"protocolVersion": 7, "clientCapabilities": {}}
    )

    assert result["protocolVersion"] == 1 and result["authMethods"] == []
    assert result == INITIALIZE_RESULT
    InitializeResponse.model_validate(result)


async def test_initialize_stores_the_client_capabilities_on_the_channel() -> None:
    channel = FakeChannel()
    capabilities = {"fs": {"readTextFile": True}, "session": {"notices": {}}}

    await build_agent(channel, FakeHub()).handle_request(
        "initialize", {"protocolVersion": 1, "clientCapabilities": capabilities}
    )

    assert channel.client_capabilities == capabilities


async def test_initialize_without_client_capabilities_stores_none() -> None:
    channel = FakeChannel()
    channel.client_capabilities = {"stale": True}

    await build_agent(channel, FakeHub()).handle_request(
        "initialize", {"protocolVersion": 1, "clientCapabilities": "nonsense"}
    )

    assert channel.client_capabilities == {}


async def test_authenticate_answers_empty() -> None:
    assert await build_agent(FakeChannel(), FakeHub()).handle_request("authenticate", {}) == {}


async def test_an_unknown_method_is_method_not_found() -> None:
    with pytest.raises(RpcError) as caught:
        await build_agent(FakeChannel(), FakeHub()).handle_request("session/fly", {})
    assert caught.value.code == METHOD_NOT_FOUND


@pytest.mark.parametrize("cwd", ["relative/dir", "", None, 3])
async def test_session_new_refuses_a_relative_cwd(cwd: object) -> None:
    agent = build_agent(FakeChannel(), FakeHub())

    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/new", {"cwd": cwd, "mcpServers": []})

    assert caught.value.code == INVALID_PARAMS
    assert "absolute" in caught.value.message
    assert agent.sessions == {}


async def test_session_new_returns_modes_with_the_default_mode() -> None:
    channel = FakeChannel()
    agent = build_agent(channel, FakeHub())

    result = await _new_session(agent)

    NewSessionResponse.model_validate(result)
    assert_wire_exact(NewSessionResponse, dict(result))
    assert result["sessionId"] == "s"
    assert result["modes"]["currentModeId"] == "drive"
    assert [mode["id"] for mode in result["modes"]["availableModes"]] == ["observe", "drive"]
    assert list(agent.sessions) == ["s"]
    assert not agent.sessions["s"].turn_active
    await until(lambda: len(channel.updates) == 1)
    await asyncio.sleep(0)
    # The `/` commands, and no message: no MCP server was offered and no project matched.
    assert [u["sessionUpdate"] for u in channel.updates] == ["available_commands_update"]


async def test_session_new_honours_a_configured_default_mode() -> None:
    agent = build_agent(FakeChannel(), FakeHub(), settings=AcpSettings(default_mode="observe"))

    result = await _new_session(agent)

    assert result["modes"]["currentModeId"] == "observe"


async def test_client_mcp_servers_are_ignored_with_one_message() -> None:
    channel = FakeChannel()
    agent = build_agent(channel, FakeHub())
    servers = [
        {"name": "fs", "command": "/bin/fs", "args": [], "env": []},
        {"name": "git", "command": "/bin/git", "args": [], "env": []},
    ]

    result = await _new_session(agent, mcpServers=servers)
    await until(lambda: len(channel.updates) == 2)
    await asyncio.sleep(0)

    assert result["sessionId"] == "s"
    assert len(channel.texts) == 1
    assert channel.sessions == ["s", "s"]
    message = channel.texts[0]
    assert "2 MCP server(s)" in message
    assert "hub" in message


async def test_a_non_list_mcp_servers_value_is_not_counted() -> None:
    channel = FakeChannel()

    await _new_session(build_agent(channel, FakeHub()), mcpServers="fs")
    await until(lambda: len(channel.updates) == 1)
    await asyncio.sleep(0)

    assert channel.texts == []


async def test_unknown_session_is_resource_not_found() -> None:
    agent = build_agent(FakeChannel(), FakeHub())

    for session_id in ("nope", 7):
        with pytest.raises(RpcError) as caught:
            await agent.handle_request(
                "session/prompt", {"sessionId": session_id, "prompt": [text("/projects")]}
            )
        assert caught.value.code == RESOURCE_NOT_FOUND


@pytest.mark.parametrize("prompt", [None, "hello", [text("a"), "b"]])
async def test_a_malformed_prompt_is_invalid_params_and_opens_no_turn(prompt: object) -> None:
    agent = build_agent(FakeChannel(), FakeHub())
    await _new_session(agent)

    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/prompt", {"sessionId": "s", "prompt": prompt})

    assert caught.value.code == INVALID_PARAMS
    assert not agent.sessions["s"].turn_active


async def test_a_prompt_ends_the_turn_with_its_stop_reason() -> None:
    channel, hub = FakeChannel(), FakeHub()
    agent = build_agent(channel, hub)
    await _new_session(agent)

    result = await agent.handle_request(
        "session/prompt", {"sessionId": "s", "prompt": [text("/projects")]}
    )

    assert_wire_exact(PromptResponse, dict(result))
    assert result == {"stopReason": "end_turn"}
    assert hub.calls[0].request_id == "acp-s-t1"
    assert not agent.sessions["s"].turn_active


async def test_second_prompt_while_running_is_invalid_request() -> None:
    hub = FakeHub()
    hub.release = asyncio.Event()
    agent = build_agent(FakeChannel(), hub)
    await _new_session(agent)
    params = {"sessionId": "s", "prompt": [text("/projects")]}
    first = asyncio.create_task(agent.handle_request("session/prompt", params))
    await asyncio.wait_for(hub.entered.wait(), 5)

    with pytest.raises(RpcError) as caught:
        await agent.handle_request("session/prompt", params)

    assert caught.value.code == INVALID_REQUEST
    assert caught.value.message == "a turn is already running in this session"
    hub.release.set()
    assert await first == {"stopReason": "end_turn"}
    assert len(hub.calls) == 1


async def test_sessions_are_independent() -> None:
    hub = FakeHub()
    hub.release = asyncio.Event()
    agent = build_agent(FakeChannel(), hub)
    await _new_session(agent)
    first = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("/projects")]})
    )
    await asyncio.wait_for(hub.entered.wait(), 5)
    await _new_session(agent)

    agent_task = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s2", "prompt": [text("/projects")]})
    )
    await until(lambda: agent.sessions["s2"].turn_active and len(hub.calls) == 2)
    await agent.handle_notification("session/cancel", {"sessionId": "s2"})
    hub.release.set()

    assert await agent_task == {"stopReason": "cancelled"}
    assert await first == {"stopReason": "end_turn"}


async def test_cancel_with_no_turn_running_is_harmless() -> None:
    agent = build_agent(FakeChannel(), FakeHub())
    await _new_session(agent)

    await agent.handle_notification("session/cancel", {"sessionId": "s"})
    await agent.handle_notification("session/cancel", {"sessionId": "unknown"})
    await agent.handle_notification("session/cancel", {"sessionId": ["not", "a", "string"]})
    result = await agent.handle_request(
        "session/prompt", {"sessionId": "s", "prompt": [text("/projects")]}
    )

    assert result == {"stopReason": "end_turn"}


async def test_other_notifications_are_ignored() -> None:
    channel = FakeChannel()
    agent = build_agent(channel, FakeHub())

    await agent.handle_notification("session/unknown", {"sessionId": "s"})

    assert channel.updates == []


# -- how a turn task ends ------------------------------------------------------------------


class _ScriptedTurn:
    """A turn whose `run` is the given coroutine function."""

    def __init__(self, body: Any) -> None:
        self._body = body

    async def run(
        self, session: AcpSessionContext, prompt: Sequence[Mapping[str, Any]], *, turn_id: str
    ) -> StopReason:
        result: StopReason = await self._body()
        return result


def _agent_with(turn: _ScriptedTurn) -> AcpAgent:
    settings = AcpSettings()
    ids = iter(["s", "t1", "t2"])
    return AcpAgent(
        FakeChannel(),
        FakeHub(),
        settings,
        AcpModes(settings),
        AcpUpdateMapper(),
        HUB_CHAT,
        HOST_TOOL_CATALOG,
        lambda: turn,
        feed=AcpLiveFeed(FakeHub(), FakeChannel(), AcpUpdateMapper(), settings),
        version="9.9.9",
        new_id=lambda: next(ids),
    )


async def test_a_turn_that_fails_ends_the_turn_and_raises() -> None:
    async def boom() -> StopReason:
        raise RuntimeError("bug in a turn")

    agent = _agent_with(_ScriptedTurn(boom))
    await _new_session(agent)

    with pytest.raises(RuntimeError, match="bug in a turn"):
        await agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("x")]})

    assert not agent.sessions["s"].turn_active


async def test_a_turn_that_proposes_a_reason_keeps_it() -> None:
    async def refuse() -> StopReason:
        return StopReason.REFUSAL

    agent = _agent_with(_ScriptedTurn(refuse))
    await _new_session(agent)

    result = await agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("x")]})

    assert result == {"stopReason": "refusal"}


async def test_the_agent_itself_being_cancelled_ends_the_turn_and_propagates() -> None:
    started = asyncio.Event()

    async def wait_forever() -> StopReason:
        started.set()
        await asyncio.Event().wait()
        return StopReason.END_TURN

    agent = _agent_with(_ScriptedTurn(wait_forever))
    await _new_session(agent)
    handler = asyncio.create_task(
        agent.handle_request("session/prompt", {"sessionId": "s", "prompt": [text("x")]})
    )
    await asyncio.wait_for(started.wait(), 5)

    handler.cancel()
    with pytest.raises(asyncio.CancelledError):
        await handler

    assert not agent.sessions["s"].turn_active
    assert not agent.sessions["s"].cancel_requested
