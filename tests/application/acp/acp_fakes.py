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
from vibey.application.acp.acp_journaling_channel import AcpJournalingChannel
from vibey.application.acp.acp_live_feed import AcpLiveFeed
from vibey.application.acp.acp_prompt_turn import AcpPromptTurn
from vibey.application.acp.acp_session_journal import AcpSessionJournal
from vibey.application.acp.dto import (
    AcpSessionContext,
    HubToolResult,
    HubTurn,
    LedgerPage,
    SessionEvent,
    SessionRecord,
)
from vibey.domain.acp.gate_permission import GatePermissionMapper
from vibey.domain.acp.modes import AcpModes
from vibey.domain.acp.protocol import StopReason
from vibey.domain.acp.session_log import SessionEventConflict, UnknownAcpSession
from vibey.domain.acp.session_replay import SESSION_REPLAY
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
        self.hold_before: dict[int, asyncio.Event] = {}
        """The update with this 1-based number waits for the event before it is recorded, as a
        frame waiting for the peer's write lock; cancelled there, it is never sent."""
        self.write_waiting = asyncio.Event()
        """Set once an update is waiting on `hold_before`."""

    async def notify_update(self, session_id: str, update: Mapping[str, Any]) -> None:
        waiting = self.hold_before.pop(len(self.updates) + 1, None)
        if waiting is not None:
            self.write_waiting.set()
            await waiting.wait()
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
    def said(self) -> list[str]:
        """The messages without the blank lines the live feed frames its own with."""
        return [text.strip() for text in self.texts]

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
        self.projects: HubToolResult = HubToolResult(ok=True, status_code=200, text="[]")
        """What `vibey_projects` answers (the session's cwd attach)."""
        self.projects_release: asyncio.Event | None = None
        self.projects_error: Exception | None = None
        self.project_lookups: list[str] = []
        """The request ids of `vibey_projects` calls; they are not in `tool_calls`, which holds
        what a turn runs."""
        self.ledger: list[dict[str, Any]] = []
        """The project's ledger, served by `seq` when `pages` is empty."""
        self.pages: list[LedgerPage | Exception] = []
        """Scripted answers to `ledger_after`, used first and in order."""
        self.ledger_calls: list[tuple[UUID, int, int]] = []
        self.ledger_read = asyncio.Event()
        self.kept: dict[str, tuple[str, list[SessionEvent]]] = {}
        """The sessions the hub keeps: each one's folder and log."""
        self.session_error: Exception | None = None
        """Raised by every session call, as a hub that is away."""
        self.session_calls: list[tuple[str, ...]] = []
        self.listing: tuple[tuple[SessionRecord, ...], str | None] = ((), None)
        self.list_error: Exception | None = None
        self.list_calls: list[tuple[str | None, str | None]] = []

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
        if name == "vibey_projects":
            self.project_lookups.append(request_id)
            if self.projects_release is not None:
                await self.projects_release.wait()
            if self.projects_error is not None:
                raise self.projects_error
            return self.projects
        self.tool_calls.append((name, dict(arguments), request_id))
        self.tool_entered.set()
        if self.tool_release is not None:
            await self.tool_release.wait()
        if self.tool_error is not None:
            raise self.tool_error
        return self.tool_result

    async def ledger_after(self, project_id: UUID, after: int, limit: int) -> LedgerPage:
        self.ledger_calls.append((project_id, after, limit))
        self.ledger_read.set()
        if self.pages:
            scripted = self.pages.pop(0)
            if isinstance(scripted, Exception):
                raise scripted
            return scripted
        events = tuple(event for event in self.ledger if event["seq"] > after)[:limit]
        return LedgerPage(events=events, last_seq=events[-1]["seq"] if events else None)

    async def healthy(self) -> bool:
        return True

    async def create_session(self, session_id: str, cwd: str) -> None:
        self.session_calls.append(("create", session_id))
        if self.session_error is not None:
            raise self.session_error
        self.kept.setdefault(session_id, (cwd, []))

    async def append_event(
        self, session_id: str, seq: int, kind: str, payload: Mapping[str, Any]
    ) -> None:
        self.session_calls.append(("append", session_id, str(seq), kind))
        if self.session_error is not None:
            raise self.session_error
        if session_id not in self.kept:
            raise UnknownAcpSession("no such session")
        log = self.kept[session_id][1]
        held = next((event for event in log if event.seq == seq), None)
        if held is not None:
            if (held.kind, dict(held.payload)) != (kind, dict(payload)):
                raise SessionEventConflict(f"seq {seq} is taken")
            return
        log.append(SessionEvent(seq=seq, kind=kind, payload=dict(payload)))

    async def session_events(
        self, session_id: str, after: int, *, cwd: str
    ) -> tuple[SessionEvent, ...]:
        self.session_calls.append(("events", session_id, cwd))
        if self.session_error is not None:
            raise self.session_error
        kept = self.kept.get(session_id)
        if kept is None or kept[0] != cwd:
            raise UnknownAcpSession("no such session")
        return tuple(sorted((e for e in kept[1] if e.seq > after), key=lambda e: e.seq))

    async def list_sessions(
        self, *, cwd: str | None, cursor: str | None
    ) -> tuple[tuple[SessionRecord, ...], str | None]:
        self.list_calls.append((cwd, cursor))
        if self.list_error is not None:
            raise self.list_error
        return self.listing

    def log(self, session_id: str) -> list[tuple[int, str, dict[str, Any]]]:
        """A kept session's log as `(seq, kind, payload)`."""
        return [(e.seq, e.kind, dict(e.payload)) for e in self.kept[session_id][1]]

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
        GatePermissionMapper(chosen.reject_words),
        HOST_TOOL_CATALOG,
        max_result_chars=max_result_chars,
    )


def event(
    seq: int, phase: str = "build", kind: str = "TurnCompleted", **payload: Any
) -> dict[str, Any]:
    """One ledger event as the hub's live page carries it; its summary names its `seq`."""
    return {"seq": seq, "phase": phase, "kind": kind, "payload": {"summary": f"e{seq}", **payload}}


def page(*events: dict[str, Any]) -> LedgerPage:
    return LedgerPage(events=events, last_seq=events[-1]["seq"] if events else None)


def build_agent(
    channel: FakeChannel,
    hub: FakeHub,
    *,
    settings: AcpSettings | None = None,
    ids: Sequence[str] = ("s", "t1", "s2", "t2", "t3", "t4"),
    journal: AcpSessionJournal | None = None,
) -> AcpAgent:
    """The agent as `bootstrap.build_acp_agent` composes it: its turns write through the
    journaling channel, so what they show is kept in the session's log."""
    chosen = settings or AcpSettings()
    pool = iter(ids)
    kept = journal or AcpSessionJournal(hub, chosen, channel, AcpUpdateMapper())
    journaled = AcpJournalingChannel(channel, kept, SESSION_REPLAY)
    return AcpAgent(
        channel,
        hub,
        chosen,
        AcpModes(chosen),
        AcpUpdateMapper(),
        HUB_CHAT,
        HOST_TOOL_CATALOG,
        lambda: build_turn(journaled, hub, settings=chosen),  # type: ignore[arg-type]
        feed=AcpLiveFeed(hub, channel, AcpUpdateMapper(), chosen, sleep=_yield),
        journal=kept,
        version="9.9.9",
        new_id=lambda: next(pool),
    )


async def _yield(seconds: float) -> None:
    """The live feed's wait in agent tests: it only yields, so a poll never stalls a test."""
    await asyncio.sleep(0)


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


def unfenced(shown: str) -> str:
    """A tool result as it was before vibey fenced it as a code block."""
    lines = shown.split("\n")
    assert lines[0] == lines[-1] and set(lines[0]) == {"`"} and len(lines[0]) >= 3
    return "\n".join(lines[1:-1])


def text(value: str) -> dict[str, Any]:
    return {"type": "text", "text": value}


async def until(predicate: Any, spins: int = 1000) -> None:
    """Yield to the loop until `predicate()` holds; fail loudly if it never does."""
    for _ in range(spins):
        if predicate():
            return
        await asyncio.sleep(0)
    raise AssertionError("condition never became true")
