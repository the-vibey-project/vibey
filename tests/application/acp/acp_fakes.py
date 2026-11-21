# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Test doubles for the ACP application layer: a recording client channel and a scripted hub.

Neither defines a `VibeyError` subclass: a test-only one would land in the error catalogue
check (`tests/cli/test_error_codes_are_complete.py`) when both run in one worker."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from vibey.application.acp.acp_agent import AcpAgent
from vibey.application.acp.acp_gate_prompter import AcpGatePrompter
from vibey.application.acp.acp_prompt_turn import AcpPromptTurn
from vibey.application.acp.dto import AcpSessionContext, HubToolResult, HubTurn, LedgerPage
from vibey.domain.acp.gate_permission import GatePermissionMapper
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.protocol import StopReason
from vibey.domain.acp.session_state import AcpSessionState
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.acp.update_mapper import AcpUpdateMapper
from vibey.domain.host_tools import HOST_TOOL_CATALOG, MAX_RESPONSE_CHARS
from vibey.domain.hub_chat import HUB_CHAT
from vibey.domain.hub_scope import AGENT_DEFAULT_SCOPES, HubScope
from vibey.domain.interfaces.hub_chat_interface import HubChatInterface


class FakeChannel:
    """Records every update, in order, with the session it named."""

    def __init__(self) -> None:
        self.client_capabilities: Mapping[str, Any] = {}
        self.updates: list[dict[str, Any]] = []
        self.sessions: list[str] = []
        self.permission_requests: list[dict[str, Any]] = []
        self.permission_answers: list[str | None] = []
        """What each permission request answers, in order; None once they run out."""
        self.permission_block = False
        """Leave every permission request unanswered until `cancel_permissions` resolves it."""
        self.permission_asked = asyncio.Event()
        self.cancelled_permissions: list[str] = []
        self._waiting: dict[str, list[asyncio.Future[None]]] = {}
        self.hold_at: dict[int, asyncio.Event] = {}
        """The update with this 1-based number is recorded, then waits for the event."""

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        self.sessions.append(session_id)
        self.updates.append(dict(update))
        gate = self.hold_at.get(len(self.updates))
        if gate is not None:
            await gate.wait()

    async def request_permission(
        self,
        session_id: str,
        tool_call: Mapping[str, Any],
        options: Sequence[Mapping[str, Any]],
        *,
        timeout: float,
    ) -> str | None:
        self.permission_requests.append(
            {
                "session": session_id,
                "tool_call": dict(tool_call),
                "options": list(options),
                "timeout": timeout,
            }
        )
        self.permission_asked.set()
        if self.permission_block:
            waiter: asyncio.Future[None] = asyncio.get_running_loop().create_future()
            self._waiting.setdefault(session_id, []).append(waiter)
            await waiter
            return None
        return self.permission_answers.pop(0) if self.permission_answers else None

    def cancel_permissions(self, session_id: str) -> tuple[str, ...]:
        self.cancelled_permissions.append(session_id)
        waiters = self._waiting.pop(session_id, [])
        for waiter in waiters:
            if not waiter.done():
                waiter.set_result(None)
        return tuple(f"perm-{index}" for index, _ in enumerate(waiters))

    @property
    def texts(self) -> list[str]:
        return [
            update["content"]["text"]
            for update in self.updates
            if update["sessionUpdate"] == "agent_message_chunk"
        ]

    @property
    def kinds(self) -> list[tuple[str, str | None]]:
        return [(update["sessionUpdate"], update.get("status")) for update in self.updates]


@dataclass(frozen=True)
class ChatCall:
    message: str
    project_id: UUID | None
    request_id: str


class FakeHub:
    """Answers `chat` with a canned turn or error, optionally only once `release` is set."""

    def __init__(
        self,
        turn: HubTurn | None = None,
        *,
        error: Exception | None = None,
        scopes: frozenset[HubScope] = AGENT_DEFAULT_SCOPES,
    ) -> None:
        self.turn = turn or HubTurn(reply="Done.", tool_calls=(), gates=(), project_id=None)
        self.error = error
        self.scopes = scopes
        self.calls: list[ChatCall] = []
        self.release: asyncio.Event | None = None
        self.entered = asyncio.Event()
        self.tool_calls: list[tuple[str, dict[str, Any], str]] = []
        self.tool_result = HubToolResult(ok=True, status_code=200, text='{"answered": true}')
        self.tool_error: Exception | None = None
        self.tool_release: asyncio.Event | None = None
        self.tool_entered = asyncio.Event()

    async def chat(self, message: str, *, project_id: UUID | None, request_id: str) -> HubTurn:
        self.calls.append(ChatCall(message, project_id, request_id))
        self.entered.set()
        if self.release is not None:
            await self.release.wait()
        if self.error is not None:
            raise self.error
        return self.turn

    async def call_tool(
        self, name: str, arguments: Mapping[str, Any], *, request_id: str
    ) -> HubToolResult:
        self.tool_calls.append((name, dict(arguments), request_id))
        self.tool_entered.set()
        if self.tool_release is not None:
            await self.tool_release.wait()
        if self.tool_error is not None:
            raise self.tool_error
        return self.tool_result

    async def ledger_after(self, project_id: UUID, after: int, limit: int) -> LedgerPage:
        return LedgerPage(events=(), last_seq=None)

    async def healthy(self) -> bool:
        return True

    def agent_scopes(self) -> frozenset[HubScope]:
        return self.scopes


def build_turn(
    channel: FakeChannel,
    hub: FakeHub,
    *,
    settings: AcpSettings | None = None,
    chat: HubChatInterface = HUB_CHAT,
    max_result_chars: int = MAX_RESPONSE_CHARS,
) -> AcpPromptTurn:
    chosen = settings or AcpSettings()
    return AcpPromptTurn(
        channel,
        hub,
        chosen,
        AcpModes(chosen),
        AcpUpdateMapper(),
        chat,
        HOST_TOOL_CATALOG,
        build_gates(channel, hub, settings=chosen, max_result_chars=max_result_chars),
        max_result_chars=max_result_chars,
    )


def build_gates(
    channel: FakeChannel,
    hub: FakeHub,
    *,
    settings: AcpSettings | None = None,
    max_result_chars: int = MAX_RESPONSE_CHARS,
) -> AcpGatePrompter:
    chosen = settings or AcpSettings()
    return AcpGatePrompter(
        channel,
        hub,
        chosen,
        AcpModes(chosen),
        AcpUpdateMapper(),
        GatePermissionMapper(chosen.reject_words, HUB_CHAT),
        HOST_TOOL_CATALOG,
        max_result_chars=max_result_chars,
    )


def build_agent(
    channel: FakeChannel,
    hub: FakeHub,
    *,
    settings: AcpSettings | None = None,
    ids: Sequence[str] = ("s", "t1", "s2", "t2", "t3", "t4"),
) -> AcpAgent:
    chosen = settings or AcpSettings()
    pool = iter(ids)
    return AcpAgent(
        channel,
        hub,
        chosen,
        AcpModes(chosen),
        AcpUpdateMapper(),
        HUB_CHAT,
        HOST_TOOL_CATALOG,
        lambda: build_turn(channel, hub, settings=chosen),
        version="9.9.9",
        new_id=lambda: next(pool),
    )


def context(session_id: str = "s", *, mode_id: str = "drive") -> AcpSessionContext:
    """A session with turn `t1` begun, as the agent hands it to a prompt turn."""
    state = AcpSessionState(session_id)
    state.begin_turn("t1")
    return AcpSessionContext(
        session_id=session_id,
        state=state,
        mode_id=mode_id,
        project_id=None,
        offered_gates=set(),
        cwd="/work",
    )


def next_turn(session: AcpSessionContext, turn_id: str) -> AcpSessionContext:
    """End the session's turn and begin `turn_id`, as the agent does between prompts."""
    session.state.finish_turn(StopReason.END_TURN)
    session.state.begin_turn(turn_id)
    return session


def text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


async def until(predicate: Any, spins: int = 1000) -> None:
    """Yield to the loop until `predicate()` holds; fail loudly if it never does."""
    for _ in range(spins):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition never became true")
