# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Mirrors `vibey/domain/acp/update_mapper.py` (ADR-0016). Declares only."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.acp.protocol import NoticeSeverity, ToolCallStatus, ToolKind
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
        self, tool_call_id: str, status: ToolCallStatus, text: str | None = None
    ) -> dict[str, Any]:
        """A status change of an announced tool call, with `text` as its content when given."""
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
