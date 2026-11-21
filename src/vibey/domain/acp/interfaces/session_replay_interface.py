# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/session_replay.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable
from uuid import UUID

if TYPE_CHECKING:
    from vibey.domain.acp.session_log import SessionEventKind


@runtime_checkable
class AcpSessionReplayInterface(Protocol):
    """What a session's log keeps of an update, and what a kept event shows again."""

    def recordable(
        self, update: Mapping[str, Any]
    ) -> tuple[SessionEventKind, dict[str, Any]] | None:
        """The event to keep for an update a prompt turn sent: a message, a tool call or its
        outcome, a plan, as plain text and the fields a replay needs; None for anything else
        (commands, modes, notices) and for an update missing what it needs."""
        ...

    def user_message(self, text: str) -> dict[str, Any]:
        """The payload kept for what the operator typed."""
        ...

    def title(self, text: str, *, limit: int) -> str | None:
        """A session's title from its first message: the first line that is not blank, as one
        line of at most `limit` characters; None when there is none."""
        ...

    def plain(self, text: str) -> str:
        """Text vibey sent, as it read: the body of a code block, or the text with the
        backslashes `UntrustedText` added taken out."""
        ...

    def fit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """`payload`, its text cut until its JSON fits `STORED_EVENT_BYTES`."""
        ...

    def replay(self, kind: str, payload: Any, *, modes: Sequence[str]) -> dict[str, Any] | None:
        """The `session/update` a kept event shows as, built from the fields it knows, each
        checked, every text through `UntrustedTextInterface`; None for an event that shows
        nothing (attach, title, closed) or fails a check. Never a permission request."""
        ...

    def mode(self, payload: Any, *, modes: Sequence[str]) -> str | None:
        """A kept mode event's mode, when it is one of `modes`."""
        ...

    def project(self, payload: Any) -> UUID | None:
        """A kept attach event's project, when it is a canonical UUID."""
        ...

    def valid_session_id(self, value: Any) -> bool:
        """Whether `value` is shaped like a session id vibey mints (`SESSION_ID_SHAPE`)."""
        ...
