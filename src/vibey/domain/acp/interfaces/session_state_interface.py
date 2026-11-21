# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/session_state.py` (ADR-0016). Declares only."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.protocol import StopReason


@runtime_checkable
class AcpSessionStateInterface(Protocol):
    """One session's turn, cancel and permission state."""

    session_id: str

    @property
    def turn_active(self) -> bool: ...

    @property
    def cancel_requested(self) -> bool: ...

    @property
    def closed(self) -> bool: ...

    @property
    def pending_permissions(self) -> frozenset[str]: ...

    def begin_turn(self, turn_id: str) -> None:
        """Start a turn; `TurnAlreadyRunning` while one is active, `SessionClosed` once closed."""
        ...

    def register_permission(self, request_id: str) -> None:
        """Record a `session/request_permission` that is out; `NoActiveTurn` outside a turn."""
        ...

    def resolve_permission(self, request_id: str) -> None:
        """The client answered it; an id already resolved by a cancel is ignored."""
        ...

    def request_cancel(self) -> tuple[str, ...]:
        """Mark the active turn cancelled; the pending permission ids, now resolved. `()` and
        no effect with no active turn, so a stray cancel never leaks into the next turn."""
        ...

    def finish_turn(self, proposed: StopReason) -> StopReason:
        """The one stop reason: `CANCELLED` when this turn was cancelled, else `proposed`."""
        ...

    def close(self) -> tuple[str, ...]:
        """Cancel any active turn and refuse new ones. Idempotent."""
        ...
