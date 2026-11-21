# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/application/acp/acp_live_feed.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.application.acp.dto import AcpSessionContext


@runtime_checkable
class AcpLiveFeedInterface(Protocol):
    """Streams a project's ledger to one ACP session as a phase plan and summary messages."""

    def attach(self, session: AcpSessionContext) -> None:
        """Follow `session.project_id`'s ledger for `session`, replacing any feed it had.

        In a task of its own: read the ledger up to its newest event (only to learn the phase
        history), send the plan as it stands, then `follow` from that newest `seq`. Gate events
        are messages only, never permission requests; a spend gate's event says, once per
        feed, where to answer it. `session.offered_gates` is read (a gate the prompter already
        refused is not refused again) and never written: ledger data cannot mark a gate.
        """
        ...

    async def follow(self, session_id: str, project_id: UUID, *, after: int) -> None:
        """Send the events after `after` as they arrive, until cancelled.

        The watermark only moves past an event once every update for it was sent. A failed
        read leaves it where it is, is reported once, and is retried after
        `[acp] live_poll_seconds`; an event at or below it is skipped. The plan is re-sent only
        when the phase changes. With `[acp] live_between_turns = false`, events that arrive
        outside a turn are held (at most `pending_events_max`; no more is read until they are
        sent) and sent by `flush`.
        """
        ...

    def watermark(self, session_id: str) -> int:
        """The last `seq` whose updates were all sent for `session_id`; 0 before any."""
        ...

    async def flush(self, session_id: str) -> None:
        """Send the events held for `session_id` between turns, oldest first."""
        ...

    def detach(self, session_id: str) -> None:
        """Stop following for `session_id` (a close, or a move to another project)."""
        ...

    async def close(self) -> None:
        """Stop every feed and wait for each to end, so none outlives the connection."""
        ...
