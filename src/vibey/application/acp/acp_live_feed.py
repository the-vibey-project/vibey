# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A project's ledger, streamed to one ACP session as a phase plan and messages (SP-ACP).

The hub's live page (`GET /api/v1/projects/{id}/ledger/after`) is polled from a watermark, as
sub-doctrine 10.g lays down: the watermark is a position in the ledger (`seq`), never a time,
and it moves past an event only once every update for that event was sent. A read that fails
leaves it where it is; the next read starts from it again, and an event the hub sends twice (a
restart, an overlapping page) is at or below it and skipped. A failure is reported once, and
retried after `[acp] live_poll_seconds`, the wait doubling with each failure in a row up to
`[acp] probe_seconds` (never longer than the keep-alive's own interval); a short page is
followed by `live_poll_seconds`, and a full page that moved the cursor is read again at once.

Every message the feed sends is its own paragraph (a blank line before and after), so it never
runs into the next one or into the agent's own reply: ACP clients join consecutive message
chunks and render them as Markdown.

Attaching reads the whole ledger first, only to learn the phases the project has been in, and
sends the plan as it stands; it then follows from the newest `seq` it read. History is never
replayed as messages: `/ledger` reads it.

Ledger text is untrusted data. Every event becomes one message
(`AcpUpdateMapperInterface.ledger_summary`: one line, Markdown escaped) and nothing else: a gate
event is never a permission request (gates are offered only by the prompt turn's
`AcpGatePrompterInterface`, under the session's mode). A gate event that says its gate spends
money adds one notice, worded as what the ledger reports rather than as fact (the event could
be forged), naming only a canonical UUID and a known spend kind: answer it on the host. The
feed never writes the session's `offered_gates`: that record belongs to the prompter, and an
event a worker wrote must not be able to mark a real gate as already offered and so hide it.
The notices the feed has said are its own set, at most `pending_events_max`.

Declared by `interfaces/acp_live_feed_interface.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import math
from collections.abc import Awaitable, Callable, Mapping
from collections.abc import Set as AbstractSet
from dataclasses import dataclass, field
from typing import Any, Final
from uuid import UUID

from vibey.application.acp.dto import AcpSessionContext, LedgerPage
from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.gate_permission import GatePermissionMapper
from vibey.domain.acp.interfaces.gate_permission_interface import GatePermissionMapperInterface
from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import SPEND_GATE_KINDS
from vibey.domain.phase import Phase

LIVE_PAGE: Final = 200
"""The most events one read asks for: the hub's own bound on a live page."""
ABANDONED_TEXT: Final = "Project abandoned."
RESUMED_TEXT: Final = "Live updates resumed."
_LOG: Final = logging.getLogger(__name__)

type Sleep = Callable[[float], Awaitable[None]]


@dataclass(slots=True)
class _Follow:
    """One session's feed: where it stands in the ledger and what it still holds."""

    session_id: str
    project_id: UUID
    state: AcpSessionStateInterface | None
    """The session's turn state; None follows live whatever `live_between_turns` says."""
    offered_gates: AbstractSet[str]
    """The prompter's record of the gates put to the session: read, never written."""
    watermark: int = 0
    history: list[str] = field(default_factory=list)
    """The phases the project has been in, oldest first, each change once."""
    held: list[tuple[int, Mapping[str, Any]]] = field(default_factory=list)
    """Events read but not yet sent (between turns), by `seq`, oldest first."""
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    failures: int = 0
    """Failed reads in a row; the retry waits longer with each."""
    task: asyncio.Task[None] | None = None
    refused: dict[str, None] = field(default_factory=dict)
    """The gates whose spend refusal this feed said, oldest first (an ordered set), at most
    `pending_events_max`; past that the oldest is forgotten, at worst saying one again."""

    @property
    def cursor(self) -> int:
        """Where the next read starts: after what is held, or after the watermark."""
        return self.held[-1][0] if self.held else self.watermark


class AcpLiveFeed:
    """Declared by `interfaces/acp_live_feed_interface.py::AcpLiveFeedInterface`."""

    def __init__(
        self,
        hub: AcpHubPortInterface,
        channel: ClientChannelInterface,
        mapper: AcpUpdateMapperInterface,
        settings: AcpSettings,
        *,
        gates: GatePermissionMapperInterface | None = None,
        sleep: Sleep = asyncio.sleep,
    ) -> None:
        self._hub = hub
        self._channel = channel
        self._mapper = mapper
        self._settings = settings
        self._gates = gates if gates is not None else GatePermissionMapper(settings.reject_words)
        self._sleep = sleep
        self._follows: dict[str, _Follow] = {}
        self._tasks: set[asyncio.Task[None]] = set()

    def attach(self, session: AcpSessionContext) -> None:
        if session.project_id is None:
            raise ValueError(f"session {session.session_id} has no project to follow")
        self.detach(session.session_id)
        follow = _Follow(
            session.session_id, session.project_id, session.state, session.offered_gates
        )
        self._follows[session.session_id] = follow
        follow.task = asyncio.create_task(self._run(follow), name=f"acp-live-{session.session_id}")
        self._tasks.add(follow.task)
        follow.task.add_done_callback(self._tasks.discard)

    async def follow(self, session_id: str, project_id: UUID, *, after: int) -> None:
        follow = self._follows.get(session_id)
        if follow is not None and follow.task is not None:
            # A second loop over an attached feed could move its watermark backwards.
            raise ValueError(f"session {session_id} is already followed; detach it first")
        if follow is None or follow.project_id != project_id:
            follow = _Follow(session_id, project_id, None, set())
            self._follows[session_id] = follow
        follow.watermark = after
        await self._poll(follow)

    def watermark(self, session_id: str) -> int:
        follow = self._follows.get(session_id)
        return follow.watermark if follow is not None else 0

    async def flush(self, session_id: str) -> None:
        follow = self._follows.get(session_id)
        if follow is not None:
            await self._drain(follow)

    def detach(self, session_id: str) -> None:
        follow = self._follows.pop(session_id, None)
        if follow is not None and follow.task is not None:
            follow.task.cancel()

    async def close(self) -> None:
        self._follows.clear()
        tasks = list(self._tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    # -- the feed's task ------------------------------------------------------------------

    async def _run(self, follow: _Follow) -> None:
        try:
            await self._catch_up(follow)
            await self._poll(follow)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # A defect, or a client that went away: hub failures are `VibeyError`s and are
            # retried in the loop, so whatever reaches here would only fail again. It is logged
            # with its traceback and the feed stops, rather than retrying it in a loop.
            _LOG.exception("the live feed for session %s stopped", follow.session_id)
            with contextlib.suppress(Exception):
                await self._say(
                    follow,
                    f"Live updates stopped: {type(exc).__name__}. The agent's log on stderr "
                    "has the details; reopen the session to start them again.",
                )

    async def _catch_up(self, follow: _Follow) -> None:
        """Read to the ledger's newest event for the phase history; send the plan as it is."""
        newest = 0
        while True:
            read = await self._read(follow, newest, LIVE_PAGE)
            if read is None:
                await self._sleep(self._retry_wait(follow))
                continue
            moved = self._after(read, newest)
            for seq, event in moved:
                phase = self._next_phase(follow, event)
                if phase is not None:
                    follow.history.append(phase)
                newest = seq
            if len(read.events) < LIVE_PAGE or not moved:
                break  # the end, or a page that does not advance: never loop on it
        if follow.history:
            current = follow.history[-1]
            await self._notify(follow, self._mapper.phase_plan(follow.history, current))
            if current == Phase.ABANDONED.value:
                await self._say(follow, ABANDONED_TEXT)
        follow.watermark = newest

    async def _poll(self, follow: _Follow) -> None:
        while True:
            full = False
            wait = self._settings.live_poll_seconds
            room = self._settings.pending_events_max - len(follow.held)
            if room > 0:
                limit = min(LIVE_PAGE, room)
                read = await self._read(follow, follow.cursor, limit)
                if read is None:
                    wait = self._retry_wait(follow)
                else:
                    moved = self._after(read, follow.cursor)
                    follow.held.extend(moved)
                    # Full only when it also advanced: a page that does not is never re-read
                    # without a wait.
                    full = len(read.events) >= limit and bool(moved)
            if self._live(follow):
                await self._drain(follow)
            if not full:
                await self._sleep(wait)

    async def _read(self, follow: _Follow, after: int, limit: int) -> LedgerPage | None:
        try:
            read = await self._hub.ledger_after(follow.project_id, after, limit)
        except VibeyError as exc:
            follow.failures += 1
            if follow.failures == 1:
                why = self._mapper.untrusted(str(exc), limit=self._settings.live_message_chars)
                await self._say(
                    follow,
                    f"Live updates paused: the project's ledger could not be read ({why}). "
                    f"Retrying, waiting longer each time, up to {self._cap():g} s.",
                )
            return None
        if follow.failures:
            follow.failures = 0
            await self._say(follow, RESUMED_TEXT)
        return read

    def _cap(self) -> float:
        return max(float(self._settings.probe_seconds), self._settings.live_poll_seconds)

    def _retry_wait(self, follow: _Follow) -> float:
        """`live_poll_seconds` after the first failure, doubling with each one in a row, never
        more than `_cap`."""
        doublings = min(max(follow.failures - 1, 0), 32)
        return min(math.ldexp(self._settings.live_poll_seconds, doublings), self._cap())

    def _live(self, follow: _Follow) -> bool:
        if self._settings.live_between_turns:
            return True
        return follow.state is not None and follow.state.turn_active

    async def _drain(self, follow: _Follow) -> None:
        # One drain at a time per session: the loop and a turn's `flush` never send one event
        # twice, and the watermark moves past an event only after all its updates were sent.
        async with follow.lock:
            # A feed detached or replaced (another project) while this drain waited sends no
            # more of the old project's events.
            while follow.held and self._follows.get(follow.session_id) is follow:
                seq, event = follow.held[0]
                await self._deliver(follow, event)
                follow.held.pop(0)
                follow.watermark = seq

    async def _deliver(self, follow: _Follow, event: Mapping[str, Any]) -> None:
        phase = self._next_phase(follow, event)
        if phase is not None:
            # The history takes the phase only once its plan was sent: an event redelivered
            # after a cancel sends that plan again rather than never.
            history = [*follow.history, phase]
            await self._notify(follow, self._mapper.phase_plan(history, phase))
            follow.history.append(phase)
        limit = self._settings.live_message_chars
        await self._say_update(follow, self._mapper.ledger_summary(event, limit=limit))
        if phase == Phase.ABANDONED.value:
            await self._say(follow, ABANDONED_TEXT)
        notice = self._spend_notice(follow, event)
        if notice is not None:
            await self._say(follow, notice)

    # -- reading events -------------------------------------------------------------------

    @staticmethod
    def _after(read: LedgerPage, after: int) -> list[tuple[int, Mapping[str, Any]]]:
        """The page's events past `after`, in order, each with its `seq`; an event without a
        whole-number `seq` cannot be placed in the ledger and is skipped."""
        events: list[tuple[int, Mapping[str, Any]]] = []
        for event in read.events:
            seq = event.get("seq")
            if isinstance(seq, int) and not isinstance(seq, bool) and seq > after:
                events.append((seq, event))
                after = seq
        return events

    @staticmethod
    def _next_phase(follow: _Follow, event: Mapping[str, Any]) -> str | None:
        """The event's phase when it differs from the last one in the history; else None."""
        phase = event.get("phase")
        if not isinstance(phase, str) or (follow.history and follow.history[-1] == phase):
            return None
        return phase

    def _spend_notice(self, follow: _Follow, event: Mapping[str, Any]) -> str | None:
        """The host notice for an event that says its gate spends, once per feed; else None."""
        payload = event.get("payload")
        if not isinstance(payload, Mapping) or "gate_kind" not in payload:
            return None
        gate = {
            "gate_id": payload.get("gate_id"),
            "kind": payload.get("gate_kind"),
            "is_spend": payload.get("is_spend"),
            "requires_scope": payload.get("requires_scope"),
        }
        gate_id = self._gates.gate_id(gate)
        if gate_id is None or not self._gates.spends(gate):
            return None
        if gate_id in follow.refused or gate_id in follow.offered_gates:
            return None  # said already, here or by the prompter
        follow.refused[gate_id] = None
        if len(follow.refused) > self._settings.pending_events_max:
            del follow.refused[next(iter(follow.refused))]
        kind = gate["kind"]
        known = f", {kind}" if isinstance(kind, str) and kind in SPEND_GATE_KINDS else ""
        return (
            f"The ledger reports a gate that may spend money ({gate_id}{known}). If it is "
            f"open, answer it on the host (`vibey answer {gate_id}`) or in the desktop or "
            "mobile app; I cannot answer it from here."
        )

    # -- output ---------------------------------------------------------------------------

    async def _say(self, follow: _Follow, text: str) -> None:
        await self._say_update(follow, self._mapper.agent_text(text))

    async def _say_update(self, follow: _Follow, update: Mapping[str, Any]) -> None:
        """A message as its own paragraph: blank lines keep it apart from what is around it."""
        content = update["content"]
        framed = {**update, "content": {**content, "text": f"\n\n{content['text']}\n\n"}}
        await self._notify(follow, framed)

    async def _notify(self, follow: _Follow, update: Mapping[str, Any]) -> None:
        await self._channel.notify_update(follow.session_id, update)
