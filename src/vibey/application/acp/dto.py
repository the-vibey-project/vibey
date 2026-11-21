# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The records the ACP agent's seams carry (SP-ACP). Value types only (ADR-0016 exempts them).

Imports only `vibey.domain`, so the `interfaces/` package may name these types.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface


@dataclass(frozen=True, slots=True)
class HubTurn:
    """One chat turn the hub ran (`POST /api/v1/chat/messages`)."""

    reply: str
    tool_calls: tuple[Mapping[str, Any], ...]
    gates: tuple[Mapping[str, Any], ...]
    project_id: UUID | None


@dataclass(frozen=True, slots=True)
class HubToolResult:
    """One host tool the hub ran, as the hub answered it."""

    ok: bool
    status_code: int
    text: str


@dataclass(frozen=True, slots=True)
class LedgerPage:
    """Ledger events after a `seq`, oldest first; `last_seq` is None when the page is empty."""

    events: tuple[Mapping[str, Any], ...]
    last_seq: int | None


@dataclass(frozen=True, slots=True)
class SessionRecord:
    """One ACP session as the hub keeps it: `updated_at` is when its newest event was
    recorded (when it was created, before any), `title` its newest title event's and `closed`
    whether its newest event is a close."""

    session_id: str
    cwd: str
    title: str | None
    updated_at: datetime
    closed: bool


@dataclass(frozen=True, slots=True)
class SessionEvent:
    """One event of an ACP session's log, as stored: untrusted data on its way back out."""

    seq: int
    kind: str
    payload: Mapping[str, Any]


@dataclass(slots=True)
class AcpSessionContext:
    """One ACP session as the agent holds it. Mutable: the agent owns it and a turn updates it."""

    session_id: str
    state: AcpSessionStateInterface
    mode_id: str
    project_id: UUID | None = None
    offered_gates: set[str] = field(default_factory=set)
    """Gates already put to the client in this session (asked, or refused with a reason), so
    none is asked twice."""
    cwd: str = ""
    open_gates: tuple[Mapping[str, Any], ...] = ()
    """The open gates the hub listed with its last turn, oldest first. The local parse reads
    them, as the hub's does, so `/answer 1` and a bare number mean here what they mean there."""
    title: str | None = None
    """The session's title, from its first message; None before one."""
