# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One ACP session's turn, cancel and permission state (SP-ACP, review focus 2).

A prompt turn begins once and ends with exactly one stop reason. A `session/cancel` that
arrives in the same read as the prompt, while a permission request is out, or after the turn
finished must each end the way the protocol says: `cancelled` when the cancel belongs to that
turn, every pending permission resolved locally, and the next turn untouched. This class is
that rule and nothing else: no I/O, no clock, no async. Declared by
`interfaces/session_state_interface.py`.
"""

from vibey.domain.acp.protocol import StopReason
from vibey.domain.errors import VibeyError


class TurnAlreadyRunning(VibeyError):
    """A prompt turn began while another was still active on the same session."""


class SessionClosed(VibeyError):
    """The session was closed; it takes no new turn."""


class NoActiveTurn(VibeyError):
    """A permission was registered, or a turn finished, with no turn active."""


class AcpSessionState:
    """Declared by `interfaces/session_state_interface.py`."""

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self._turn: str | None = None
        self._cancelled = False
        self._pending: set[str] = set()
        self._closed = False

    @property
    def turn_active(self) -> bool:
        return self._turn is not None

    @property
    def cancel_requested(self) -> bool:
        return self._cancelled

    @property
    def closed(self) -> bool:
        return self._closed

    @property
    def pending_permissions(self) -> frozenset[str]:
        return frozenset(self._pending)

    def begin_turn(self, turn_id: str) -> None:
        if self._closed:
            raise SessionClosed(f"session {self.session_id} is closed")
        if self._turn is not None:
            raise TurnAlreadyRunning(
                f"session {self.session_id} is already running turn {self._turn}"
            )
        self._turn = turn_id
        self._cancelled = False

    def register_permission(self, request_id: str) -> None:
        if self._turn is None:
            raise NoActiveTurn(f"permission {request_id} asked outside a prompt turn")
        self._pending.add(request_id)

    def resolve_permission(self, request_id: str) -> None:
        # A late answer to a permission a cancel already resolved is not an error.
        self._pending.discard(request_id)

    def request_cancel(self) -> tuple[str, ...]:
        if self._turn is None:
            return ()
        self._cancelled = True
        return self._drain()

    def finish_turn(self, proposed: StopReason) -> StopReason:
        if self._turn is None:
            raise NoActiveTurn(f"session {self.session_id} has no turn to finish")
        reason = StopReason.CANCELLED if self._cancelled else proposed
        self._turn = None
        self._cancelled = False
        self._pending.clear()
        return reason

    def close(self) -> tuple[str, ...]:
        self._closed = True
        return self.request_cancel()

    def _drain(self) -> tuple[str, ...]:
        pending = tuple(sorted(self._pending))
        self._pending.clear()
        return pending
