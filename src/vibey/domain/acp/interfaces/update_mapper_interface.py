# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/update_mapper.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.protocol import NoticeSeverity, ToolCallStatus, ToolKind
    from vibey.domain.hub_chat import ChatSlashSpec
    from vibey.domain.hub_scope import HubScope


@runtime_checkable
class AcpUpdateMapperInterface(Protocol):
    """Builds the `update` member of a `session/update` notification."""

    def agent_text(self, text: str) -> dict[str, Any]:
        """An `agent_message_chunk` carrying `text`."""
        ...

    def user_text(self, text: str) -> dict[str, Any]:
        """A `user_message_chunk` carrying `text` (replaying what the user sent)."""
        ...

    def tool_call(
        self, tool_call_id: str, title: str, kind: ToolKind, raw_input: Mapping[str, Any]
    ) -> dict[str, Any]:
        """A new tool call, status `pending`."""
        ...

    def tool_call_update(
        self,
        tool_call_id: str,
        status: ToolCallStatus,
        text: str | None = None,
        *,
        title: str | None = None,
        kind: ToolKind | None = None,
    ) -> dict[str, Any]:
        """A status change of an announced tool call, with `text` as its content when given,
        and a new `title` and `kind` when what ran is not what was announced."""
        ...

    def notice(
        self, title: str, severity: NoticeSeverity, description: str, *, client_notices: bool
    ) -> dict[str, Any]:
        """A `notice`, or an `agent_message_chunk` "title: description" when the client
        did not advertise `session.notices`."""
        ...

    def tool_kind_for(self, scope: HubScope) -> ToolKind:
        """`read` for `view`, `execute` for `run`, `other` for every other scope."""
        ...

    def phase_plan(self, phases_seen: Sequence[str], current: str) -> dict[str, Any]:
        """A `plan` with one entry per phase: design, visual design (only once seen), build,
        review and the three deploy phases (dropped when the project is `done` without them).

        `phases_seen` is the project's phase history, oldest first; repeats are allowed, so a
        review that sent the work back to build reads `build` last. An entry before the phase
        the plan stands at is `completed`, that phase is `in_progress` and the rest `pending`.
        `done` completes every entry; `abandoned`, `intake` and any phase outside the plan
        stand at the last plan phase in the history (none: everything pending).
        """
        ...

    def ledger_summary(self, event: Mapping[str, Any], *, limit: int) -> dict[str, Any]:
        """An `agent_message_chunk` "[phase] kind: summary" for one ledger event, the summary
        being the payload's `summary` or else its `message` when either is a string (omitted
        otherwise); phase, kind and summary shown as `untrusted` text, the whole at most
        `limit` characters as written with a trailing "..." when cut."""
        ...

    def untrusted(self, value: Any, *, limit: int) -> str:
        """Hub or ledger data made safe to show in a message: one line (every non-printable
        character a space), every Markdown special character escaped, and at most `limit`
        characters as written, ending in "..." when cut."""
        ...

    def available_commands(self, specs: Sequence[ChatSlashSpec]) -> dict[str, Any]:
        """An `available_commands_update` naming every `/` command, each with its usage after
        the command word as the input hint when it takes one."""
        ...

    def current_mode(self, mode_id: str) -> dict[str, Any]:
        """A `current_mode_update` naming `mode_id`."""
        ...
