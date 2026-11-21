# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An ACP session's own log, as the hub keeps it (SP-ACP, migration 0023).

A session's log is append-only, like the ledger: each event is one row named by the session and
its `seq`, never changed or removed once written; a mode change, a project attach and a close are
new rows. The log keeps what the editor showed of the session -- the operator's messages, vibey's
replies, the tool calls -- so `session/load` can show it again. Live ledger summaries are not
kept: they are re-readable from the ledger itself.

Value types and constants only (ADR-0016 exempts them from the interface rule). Pure.
"""

import re
from enum import StrEnum
from typing import Final

from vibey.domain.errors import VibeyError


class SessionEventKind(StrEnum):
    """What one row of a session's log records. The database holds the same closed set."""

    USER_MESSAGE = "user_message"
    AGENT_MESSAGE = "agent_message"
    TOOL_CALL = "tool_call"
    TOOL_CALL_UPDATE = "tool_call_update"
    PLAN = "plan"
    MODE = "mode"
    ATTACH = "attach"
    TITLE = "title"
    CLOSED = "closed"


SESSION_ID_SHAPE: Final = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)
"""A session id as vibey mints one: a random UUID in its canonical lower-case form. A client
names a session to load, resume or close by it; anything else names no session of vibey's."""

SESSION_PAGE: Final = 200
"""The most sessions, or events, the hub returns in one page; a reader asks again after the
last one it was given."""

STORED_EVENT_BYTES: Final = 48 * 1024
"""The most one event's payload may take as JSON. Module-level because it is not an adopter's
choice: the hub reads no request body over 64 KiB (`infrastructure/hub/app.py::MAX_BODY_BYTES`,
the same for every hub), and an event is sent as one body with its `seq` and `kind` around it.
Text past this is cut, ending in "...", before the event is queued, so no event is ever one the
hub would refuse for its size. `tests/application/acp/test_acp_session_journal.py` holds the two
limits together."""

MAX_CWD_CHARS: Final = 4096
"""The longest folder a session may be kept under: PATH_MAX on Linux and macOS."""


class SessionEventConflict(VibeyError):
    """A session's log already holds another event at that `seq`, or the session was already
    kept under another folder. The log is append-only, so nothing is overwritten."""


class AcpSessionLimitReached(VibeyError):
    """The hub keeps no more for this principal: it holds `[acp] sessions_max` sessions, or the
    session holds `[acp] session_events_max` events. Nothing kept is dropped or changed."""


class SessionWritesThrottled(VibeyError):
    """The hub's rate limit refused a session write for now (429): sent again later, never
    dropped while the agent runs."""


class SessionRequestRefused(VibeyError):
    """The hub refused a session request for good (a 4xx other than 429: a folder it does not
    accept, a body too large, a malformed event). Sending it again cannot help: that session's
    log stops, and every other session's goes on."""


class InvalidSessionCursor(VibeyError):
    """A `session/list` cursor is not one the hub gave out."""


class UnknownAcpSession(VibeyError):
    """No session of this principal's, under this folder, has that id. Said the same way
    whether the session does not exist, belongs to another principal or was kept under another
    folder, so a guessed id learns nothing."""
