# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `session/update` payloads vibey sends an ACP client, built in one place (SP-ACP).

Each method returns the `update` member of a `session/update` notification, with the
protocol's camelCase keys, as JSON-ready dicts; `tests/domain/acp/test_update_mapper.py` holds
every shape against the official SDK. A `notice` needs the client's `session.notices`
capability, so without it the same words go out as an ordinary message. Pure: no I/O.
Declared by `interfaces/update_mapper_interface.py`.
"""

from collections.abc import Mapping
from typing import Any, Final

from vibey.domain.acp.protocol import NoticeSeverity, ToolCallStatus, ToolKind
from vibey.domain.hub_scope import HubScope

_KIND_FOR_SCOPE: Final[Mapping[HubScope, ToolKind]] = {
    HubScope.VIEW: ToolKind.READ,
    HubScope.RUN: ToolKind.EXECUTE,
}
"""A hub scope's tool kind; every scope not listed is `other`."""


class AcpUpdateMapper:
    """Declared by `interfaces/update_mapper_interface.py`."""

    def agent_text(self, text: str) -> dict[str, Any]:
        return {"sessionUpdate": "agent_message_chunk", "content": {"type": "text", "text": text}}

    def user_text(self, text: str) -> dict[str, Any]:
        return {"sessionUpdate": "user_message_chunk", "content": {"type": "text", "text": text}}

    def tool_call(
        self, tool_call_id: str, title: str, kind: ToolKind, raw_input: Mapping[str, Any]
    ) -> dict[str, Any]:
        return {
            "sessionUpdate": "tool_call",
            "toolCallId": tool_call_id,
            "title": title,
            "kind": kind.value,
            "status": ToolCallStatus.PENDING.value,
            "rawInput": dict(raw_input),
        }

    def tool_call_update(
        self,
        tool_call_id: str,
        status: ToolCallStatus,
        text: str | None = None,
        *,
        title: str | None = None,
        kind: ToolKind | None = None,
    ) -> dict[str, Any]:
        update: dict[str, Any] = {
            "sessionUpdate": "tool_call_update",
            "toolCallId": tool_call_id,
            "status": status.value,
        }
        if title is not None:
            update["title"] = title
        if kind is not None:
            update["kind"] = kind.value
        if text is not None:
            update["content"] = [{"type": "content", "content": {"type": "text", "text": text}}]
        return update

    def notice(
        self, title: str, severity: NoticeSeverity, description: str, *, client_notices: bool
    ) -> dict[str, Any]:
        if not client_notices:
            return self.agent_text(f"{title}: {description}")
        return {
            "sessionUpdate": "notice",
            "severity": severity.value,
            "title": title,
            "description": description,
        }

    def tool_kind_for(self, scope: HubScope) -> ToolKind:
        return _KIND_FOR_SCOPE.get(scope, ToolKind.OTHER)
