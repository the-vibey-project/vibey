# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The records the ACP agent's seams carry (SP-ACP). Value types only (ADR-0016 exempts them).

Imports only `vibey.domain`, so the `interfaces/` package may name these types.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from vibey.domain.acp.interfaces.session_state_interface import AcpSessionStateInterface

type DoctorMark = Literal["PASS", "WARN", "FAIL", "UNKNOWN"]
"""What a doctor check found: only `FAIL` fails `vibey doctor` and the bootstrap's doctor."""


@dataclass(frozen=True, slots=True)
class DoctorResult:
    """One finding of a doctor check: its mark, the name of what was checked and why.

    `lines` is the text the check printed for this finding, exactly as it printed it (a
    continuation line included), so `vibey doctor` can print it again byte for byte; it is
    empty for a finding the check only implied (a section that failed without a `FAIL`
    line). Every field is the machine's own text, not the operator's: shown to an editor, it
    goes through `UntrustedTextInterface` like any other text vibey did not write itself."""

    mark: DoctorMark
    name: str
    detail: str
    lines: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class PostgresReadiness:
    """Whether a supported local PostgreSQL accepts connections, why not, and which package
    manager (`brew`, `apt-get` or `dnf`) would install it; None when the host has none."""

    ready: bool
    detail: str
    package_manager: str | None


@dataclass(frozen=True, slots=True)
class PostgresInstallOutcome:
    """What an install did. `needs_password` is true when `sudo -n` refused for want of a
    password, which vibey never asks for or types: the operator runs the install instead.
    `still_running` is described at its field."""

    ok: bool
    detail: str
    needs_password: bool
    still_running: bool = False
    """A command overran its bound (`[acp] install_timeout_seconds`) and could not be confirmed
    stopped: the install may still be changing the computer, so it is not reported as failed."""


type UnitAction = Literal[
    "created",
    "unchanged",
    "kept-differing",
    "updated",
    "loaded",
    "already-loaded",
    "restarted",
    "deferred",
    "failed",
]
"""What was done with one supervised unit: its file written (`created`, `updated`), found as
vibey renders it (`unchanged`) or left as the operator edited it (`kept-differing`); the unit
loaded, found loaded, restarted, left for later (`deferred`), or not (`failed`)."""


@dataclass(frozen=True, slots=True)
class UnitOutcome:
    """One supervised unit, what was done with it, and why (ADR-0101). `detail` is the
    machine's text (a service manager's answer, an OS error): shown to an editor, it goes
    through `UntrustedTextInterface`."""

    label: str
    path: str
    action: UnitAction
    detail: str = ""


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


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """What a load needs without reading a session's log: its newest `seq` (0 before any
    event), and the payloads of its newest `mode`, `attach` and `title` events. Untrusted data,
    as every stored event is."""

    newest_seq: int
    mode: Mapping[str, Any] | None
    attach: Mapping[str, Any] | None
    title: Mapping[str, Any] | None


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
