# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ACP v1 vocabulary: method names, the enums the wire carries, and the error codes.

Every spelling here is held against the official `agent-client-protocol` SDK's schema by
`tests/domain/acp/test_protocol.py`, so a drift on either side fails a test instead of an
editor. Value types and constants only (ADR-0016 exempts them from the interface rule).
"""

from enum import StrEnum
from typing import Final

PROTOCOL_VERSION: Final = 1
"""The one ACP major version vibey speaks, sent as `protocolVersion`."""

INITIALIZE: Final = "initialize"
AUTHENTICATE: Final = "authenticate"
SESSION_NEW: Final = "session/new"
SESSION_LOAD: Final = "session/load"
SESSION_RESUME: Final = "session/resume"
SESSION_LIST: Final = "session/list"
SESSION_CLOSE: Final = "session/close"
SESSION_PROMPT: Final = "session/prompt"
SESSION_CANCEL: Final = "session/cancel"
SESSION_SET_MODE: Final = "session/set_mode"
SESSION_UPDATE: Final = "session/update"
REQUEST_PERMISSION: Final = "session/request_permission"

RESOURCE_NOT_FOUND: Final = -32002
"""A session, or another resource the request named, does not exist."""
AUTH_REQUIRED: Final = -32000
"""The agent needs the client to authenticate first."""
REQUEST_CANCELLED: Final = -32800
"""The request was cancelled before it completed."""


class StopReason(StrEnum):
    """Why a prompt turn ended. Exactly one is returned per turn."""

    END_TURN = "end_turn"
    MAX_TOKENS = "max_tokens"
    MAX_TURN_REQUESTS = "max_turn_requests"
    REFUSAL = "refusal"
    CANCELLED = "cancelled"


class ToolCallStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolKind(StrEnum):
    READ = "read"
    EDIT = "edit"
    DELETE = "delete"
    MOVE = "move"
    SEARCH = "search"
    EXECUTE = "execute"
    THINK = "think"
    FETCH = "fetch"
    SWITCH_MODE = "switch_mode"
    OTHER = "other"


class PlanEntryStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class PermissionKind(StrEnum):
    """The `kind` hint on a `session/request_permission` option."""

    ALLOW_ONCE = "allow_once"
    ALLOW_ALWAYS = "allow_always"
    REJECT_ONCE = "reject_once"
    REJECT_ALWAYS = "reject_always"


class NoticeSeverity(StrEnum):
    """The severity hint on a `notice` update (the client's `session.notices` capability)."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
