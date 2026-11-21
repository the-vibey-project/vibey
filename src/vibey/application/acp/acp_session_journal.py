# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Each ACP session's log, written behind to the hub in order (SP-ACP, Task 6).

`record` is synchronous and never waits on the hub: it gives the event the session's next `seq`
and queues it, so a prompt turn is never slowed by its own log. A new session costs the hub
nothing until its first prompt: what is recorded before it (a mode, the folder's project) is held
here, and the session's create goes out with that first prompt. A session closed before any
prompt is never kept at all, so `session/new` calls that are never used spend no slot of
`[acp] sessions_max`. `flush` sends the queue oldest
first -- a new session's create before any of its events -- and stops at the first failure,
keeping that event and everything after it, so the next flush sends again from there. An event
the hub already holds is answered as stored (its `(session_id, seq)` is its idempotency key),
so a resend after a lost answer writes nothing twice.

Two failures cannot be cured by sending again, and stop the session's log instead of the
queue: another event already at that `seq` (another `vibey acp` is writing the same session --
two windows that loaded it), and a session the hub does not keep for this principal. The
session's queued events are dropped and the client is told once.

A session is kept only when the hub grants the agent principal `acp_sessions` (`[hub]
agent_scopes`). Without it -- an operator narrowed the grant -- the session still works, in this
process only: nothing is sent, and the client is told once. That holds in every mode: keeping a
session's own record is not a run-class action, so observe keeps it as drive does. A hub that
keeps no more for this principal (`[acp] sessions_max`, `session_events_max`) also stops the
session's log, said once; what was kept stays as it was.

A write the hub's rate limit refused (429) is kept and sent again by the next flush. At the end
of the connection `drain` sends what is left, backing off from `[acp] live_poll_seconds`,
doubling, for at most `[acp] probe_seconds` in all; anything still unsent is said once on
stderr and, while the client can still hear it, in a notice -- never lost without a word.

The queue holds at most `[acp] pending_events_max` events. Past that, the oldest event that is
not being sent is dropped -- never a session's create, which every later event of it needs --
and the client is told once per session. Nothing that would grow without bound is kept while
the hub is away.

Declared by `interfaces/acp_session_journal_interface.py`.
"""

import asyncio
import logging
from collections import Counter, deque
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Final

from vibey.application.acp.interfaces.acp_hub_port_interface import AcpHubPortInterface
from vibey.application.acp.interfaces.client_channel_interface import ClientChannelInterface
from vibey.domain.acp.interfaces.update_mapper_interface import AcpUpdateMapperInterface
from vibey.domain.acp.protocol import NoticeSeverity
from vibey.domain.acp.session_log import (
    AcpSessionLimitReached,
    SessionEventConflict,
    SessionEventKind,
    SessionWritesThrottled,
    UnknownAcpSession,
)
from vibey.domain.acp.settings import AcpSettings
from vibey.domain.errors import VibeyError
from vibey.domain.hub_scope import HubScope

_LOG: Final = logging.getLogger(__name__)
NOTICE_TITLE: Final = "Session history"
OVERFLOW: Final = (
    "The hub has not taken this session's history for a while, so the oldest events waiting "
    "to be kept were dropped; loading this session later shows it without them."
)
FORKED: Final = (
    "Another `vibey acp` is keeping this session's history too, so this one stopped: what "
    "this window shows from here on is not kept."
)
FULL: Final = (
    "The hub keeps no more sessions, or no more of this session, for vibey's agent principal "
    "(`[acp] sessions_max`, `session_events_max`), so this session's history is not kept from "
    "here on. What was kept stays as it was."
)
UNGRANTED: Final = (
    "This session's history is kept only in this window: `[hub] agent_scopes` does not grant "
    "`acp_sessions`, so the hub cannot keep it and it cannot be loaded later."
)
UNSENT: Final = (
    "The hub's rate limit held back the last of this session's history as the connection "
    "ended, so it was not kept; loading this session later shows it without them."
)
UNKEPT: Final = (
    "The hub does not keep this session for vibey's agent principal, so its history is not "
    "kept from here on."
)


@dataclass(slots=True, eq=False)
class _Pending:
    """One write waiting for the hub: a session's create (`seq` 0), or one of its events."""

    session_id: str
    seq: int
    kind: str = ""
    payload: Mapping[str, Any] = field(default_factory=dict)
    cwd: str = ""


class AcpSessionJournal:
    """Declared by `interfaces/acp_session_journal_interface.py::AcpSessionJournalInterface`."""

    def __init__(
        self,
        hub: AcpHubPortInterface,
        settings: AcpSettings,
        channel: ClientChannelInterface,
        mapper: AcpUpdateMapperInterface,
        *,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
    ) -> None:
        self._sleep = sleep
        self._hub = hub
        self._settings = settings
        self._channel = channel
        self._mapper = mapper
        self._queue: deque[_Pending] = deque()
        self._next: dict[str, int] = {}
        self._persisted: dict[str, int] = {}
        self._open: set[str] = set()
        self._told: set[str] = set()
        self._notices: list[tuple[str, str]] = []
        self._sending: _Pending | None = None
        self._lock = asyncio.Lock()
        self._unprompted: dict[str, tuple[str, list[_Pending]]] = {}
        """New sessions not yet prompted: each one's folder and what was recorded so far."""
        self._throttled = False

    def open(self, session_id: str, cwd: str) -> None:
        if session_id in self._next or not self._granted(session_id):
            return
        self._start(session_id, 0)
        self._unprompted[session_id] = (cwd, [])

    def resume(self, session_id: str, last_seq: int) -> None:
        if session_id in self._open or not self._granted(session_id):
            return  # already kept by this process (its own seq is the newer), or not keepable
        self._start(session_id, last_seq)

    def record(self, session_id: str, kind: SessionEventKind, payload: Mapping[str, Any]) -> int:
        if session_id not in self._open:
            return 0
        seq = self._next[session_id]
        self._next[session_id] = seq + 1
        item = _Pending(session_id, seq, kind.value, dict(payload))
        waiting = self._unprompted.get(session_id)
        if waiting is not None:
            cwd, held = waiting
            if kind is SessionEventKind.CLOSED:
                # Closed before any prompt: there is nothing worth keeping, and no slot is spent.
                del self._unprompted[session_id]
                self._open.discard(session_id)
                return 0
            held.append(item)
            if kind is not SessionEventKind.USER_MESSAGE:
                if len(held) > self._settings.pending_events_max:
                    held.pop(0)
                    self._notice(session_id, OVERFLOW)
                return seq
            # The first prompt: the session is kept from here, its create first.
            del self._unprompted[session_id]
            self._queue.append(_Pending(session_id, 0, cwd=cwd))
            self._queue.extend(held)
        else:
            self._queue.append(item)
        if kind is SessionEventKind.CLOSED:
            self._open.discard(session_id)
        while len(self._queue) > self._settings.pending_events_max and self._drop_oldest():
            pass
        return seq

    def persisted_seq(self, session_id: str) -> int:
        return self._persisted.get(session_id, 0)

    def recording(self, session_id: str) -> bool:
        return session_id in self._open

    async def flush(self) -> None:
        async with self._lock:
            try:
                await self._send_queue()
            finally:
                self._sending = None
                await self._tell()

    async def drain(self) -> None:
        wait = self._settings.live_poll_seconds
        waited = 0.0
        while True:
            self._throttled = False
            await self.flush()
            if not self._queue or not self._throttled or waited >= self._settings.probe_seconds:
                break
            await self._sleep(wait)
            waited += wait
            wait = min(wait * 2, self._settings.probe_seconds)
        unsent = Counter(item.session_id for item in self._queue if item.seq)
        if unsent:
            _LOG.warning(
                "%d ACP session event(s) were not kept: the hub did not take them before the "
                "connection ended (%s)",
                sum(unsent.values()),
                ", ".join(f"session {sid}: {count}" for sid, count in sorted(unsent.items())),
            )
            for session_id in unsent:
                self._notice(session_id, UNSENT)
            await self._tell()

    async def _send_queue(self) -> None:
        while self._queue:
            item = self._sending = self._queue[0]
            try:
                await self._send(item)
            except (SessionEventConflict, UnknownAcpSession, AcpSessionLimitReached) as exc:
                self._stop(item.session_id, self._why(exc))
                continue
            except SessionWritesThrottled:
                self._throttled = True
                return  # the rate limit: kept, and sent again from here by the next flush
            except VibeyError:
                return  # the hub is away: kept, and sent again from here by the next flush
            except Exception:
                _LOG.exception("keeping session %s's history failed", item.session_id)
                return
            # Still the head: only a flush removes the event in flight, and one flush runs.
            self._queue.popleft()
            if item.seq:
                self._persisted[item.session_id] = max(
                    self.persisted_seq(item.session_id), item.seq
                )

    async def _send(self, item: _Pending) -> None:
        if item.seq == 0:
            await self._hub.create_session(item.session_id, item.cwd)
        else:
            await self._hub.append_event(item.session_id, item.seq, item.kind, item.payload)

    def _granted(self, session_id: str) -> bool:
        """Whether the hub lets the agent principal keep sessions; said once when it does not."""
        if HubScope.ACP_SESSIONS in self._hub.agent_scopes():
            return True
        self._notice(session_id, UNGRANTED)
        return False

    @staticmethod
    def _why(error: VibeyError) -> str:
        if isinstance(error, SessionEventConflict):
            return FORKED
        return FULL if isinstance(error, AcpSessionLimitReached) else UNKEPT

    def _start(self, session_id: str, last_seq: int) -> None:
        # Never lowered: events this process already numbered past the hub's newest (queued,
        # not yet sent) keep their seq, and the next one follows them.
        self._open.add(session_id)
        self._next[session_id] = max(last_seq + 1, self._next.get(session_id, 1))
        self._persisted[session_id] = max(last_seq, self.persisted_seq(session_id))

    def _drop_oldest(self) -> bool:
        """Drop the oldest event that is neither a create nor in flight; False when none is
        (the queue then holds only creates, one per session, past the cap)."""
        victim = next(
            (item for item in self._queue if item.seq and item is not self._sending), None
        )
        if victim is None:
            return False
        self._queue.remove(victim)
        self._notice(victim.session_id, OVERFLOW)
        return True

    def _stop(self, session_id: str, why: str) -> None:
        self._open.discard(session_id)
        self._queue = deque(item for item in self._queue if item.session_id != session_id)
        self._notice(session_id, why)

    def _notice(self, session_id: str, text: str) -> None:
        key = f"{session_id}:{text}"
        if key not in self._told:
            self._told.add(key)
            self._notices.append((session_id, text))

    async def _tell(self) -> None:
        notices, self._notices = self._notices, []
        session = self._channel.client_capabilities.get("session")
        client_notices = isinstance(session, Mapping) and isinstance(
            session.get("notices"), Mapping
        )
        for session_id, text in notices:
            update = self._mapper.notice(
                NOTICE_TITLE, NoticeSeverity.WARNING, text, client_notices=client_notices
            )
            # A client gone (the connection ending) does not stop the log: logged, not raised.
            try:
                await self._channel.notify_update(session_id, update)
            except Exception:
                _LOG.warning("could not tell session %s: %s", session_id, text, exc_info=True)
