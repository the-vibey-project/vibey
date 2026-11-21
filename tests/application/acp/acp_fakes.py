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
from vibey.application.acp.acp_prompt_turn import AcpPromptTurn
from vibey.application.acp.dto import AcpSessionContext, HubToolResult, HubTurn, LedgerPage
from vibey.domain.acp.modes import AcpModes
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
            {"session": session_id, "tool_call": dict(tool_call), "options": list(options)}
        )
        return None

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
        return HubToolResult(ok=True, status_code=200, text="{}")

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
    return AcpSessionContext(
        session_id=session_id,
        state=AcpSessionState(session_id),
        mode_id=mode_id,
        project_id=None,
        offered_gates=set(),
        cwd="/work",
    )


def text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


async def until(predicate: Any, spins: int = 1000) -> None:
    """Yield to the loop until `predicate()` holds; fail loudly if it never does."""
    for _ in range(spins):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition never became true")
