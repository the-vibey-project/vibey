# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/application/acp/acp_session_journal.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.session_log import SessionEventKind


@runtime_checkable
class AcpSessionJournalInterface(Protocol):
    """Each session's log, queued in order and written behind to the hub."""

    def open(self, session_id: str, cwd: str) -> None:
        """Start keeping a new session, its events from `seq` 1. Nothing reaches the hub until
        its first prompt (`user_message`): then its create goes first, with what was held; a
        session closed before any prompt is never kept."""
        ...

    def resume(self, session_id: str, last_seq: int) -> None:
        """Keep a session the hub already holds, from `last_seq + 1`. A session this process
        already keeps is left as it is."""
        ...

    def record(self, session_id: str, kind: SessionEventKind, payload: Mapping[str, Any]) -> int:
        """Queue one event with the session's next `seq` and return that `seq`; 0, keeping
        nothing, for a session that is not being kept (never opened, closed, or stopped). A
        `closed` event is the session's last until it is resumed. Past
        `[acp] pending_events_max` queued, the oldest event is dropped and the client told
        once."""
        ...

    def persisted_seq(self, session_id: str) -> int:
        """The newest `seq` the hub has confirmed for the session; 0 before any."""
        ...

    def recording(self, session_id: str) -> bool:
        """Whether the session's events are being kept."""
        ...

    async def flush(self) -> None:
        """Send what is queued, oldest first, stopping at the first failure and keeping the
        rest for the next flush. A conflict or a session the hub does not keep stops that
        session's log, and the client is told once. Never raises for the hub."""
        ...

    async def drain(self) -> None:
        """At the end of the connection: flush, and while the hub's rate limit holds writes
        back, wait (from `[acp] live_poll_seconds`, doubling) and flush again, for at most
        `[acp] probe_seconds` in all. What is still unsent is said once on stderr and in a
        notice to each session."""
        ...
