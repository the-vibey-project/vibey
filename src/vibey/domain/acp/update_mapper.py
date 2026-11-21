# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The `session/update` payloads vibey sends an ACP client, built in one place (SP-ACP).

Each method returns the `update` member of a `session/update` notification, with the
protocol's camelCase keys, as JSON-ready dicts; `tests/domain/acp/test_update_mapper.py` holds
every shape against the official SDK. A `notice` needs the client's `session.notices`
capability, so without it the same words go out as an ordinary message.

The live updates (`phase_plan`, `ledger_summary`) read what the hub's ledger says. A ledger
event's phase, kind and text are untrusted data written by workers and models; so is any other
hub data shown in a message (a project's name or path, an error the hub sent). `untrusted`
makes such text safe to show, and `ledger_summary` uses it for every span it did not write:

- one line: every character Python does not count as printable (controls, format and bidi
  characters, line and paragraph separators) becomes a space, so it cannot forge a second line
  or reorder the one it is in;
- no Markdown: ACP clients render message text as Markdown, so every character that could make
  a link, an image, emphasis, code, a heading, a table or HTML (`MARKDOWN_SPECIAL`) is
  backslash-escaped and shows as itself;
- at most `limit` characters as written, ending in "..." when it was cut.

vibey's own words (the hub chat's reply, which is vibey's formatted answer) are passed through
as Markdown. Pure: no I/O. Declared by `interfaces/update_mapper_interface.py`.
"""

from collections.abc import Mapping, Sequence
from typing import Any, Final

from vibey.domain.acp.protocol import NoticeSeverity, PlanEntryStatus, ToolCallStatus, ToolKind
from vibey.domain.hub_chat import ChatSlashSpec
from vibey.domain.hub_scope import HubScope
from vibey.domain.phase import Phase

_KIND_FOR_SCOPE: Final[Mapping[HubScope, ToolKind]] = {
    HubScope.VIEW: ToolKind.READ,
    HubScope.RUN: ToolKind.EXECUTE,
}
"""A hub scope's tool kind; every scope not listed is `other`."""

PLAN_PHASES: Final[tuple[tuple[Phase, str, str], ...]] = (
    (Phase.DESIGN, "Design", "high"),
    (Phase.VISUAL_DESIGN, "Visual design", "high"),
    (Phase.BUILD, "Build", "high"),
    (Phase.REVIEW, "Review", "high"),
    (Phase.DEPLOY_DESIGN, "Deploy design", "low"),
    (Phase.DEPLOY_EXECUTE, "Deploy execute", "low"),
    (Phase.DEPLOY_REVIEW, "Deploy review", "low"),
)
"""The plan's entries in order: phase, label and priority. Visual design is shown only once
the project has been in it; the three deploy phases are dropped when a project finished
without them."""
_DEPLOY_PHASES: Final = frozenset(
    {Phase.DEPLOY_DESIGN.value, Phase.DEPLOY_EXECUTE.value, Phase.DEPLOY_REVIEW.value}
)
_RANK: Final[Mapping[str, int]] = {
    phase.value: rank for rank, (phase, _, _) in enumerate(PLAN_PHASES)
}
ELLIPSIS: Final = "..."
MARKDOWN_SPECIAL: Final = frozenset("\\`*_[]()<>!#|~&")
"""Escaped in untrusted text: what opens a link, image, emphasis, code span or fence, heading,
table cell, strikethrough, HTML tag or entity, and the escape character itself."""


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

    def phase_plan(self, phases_seen: Sequence[str], current: str) -> dict[str, Any]:
        seen = {*phases_seen, current}
        shown = [
            entry
            for entry in PLAN_PHASES
            if entry[0] is not Phase.VISUAL_DESIGN or Phase.VISUAL_DESIGN.value in seen
        ]
        if current == Phase.DONE.value:
            if not seen & _DEPLOY_PHASES:
                shown = [entry for entry in shown if entry[0].value not in _DEPLOY_PHASES]
            anchor = len(PLAN_PHASES)  # every entry is behind a finished project
        else:
            # The phase the plan stands at: the current one, or -- for `abandoned`, `intake`,
            # the legacy `deploy` and a phase a newer vibey wrote -- the last plan phase the
            # project was in, so an abandoned project keeps the statuses it had.
            known = [_RANK[phase] for phase in (*phases_seen, current) if phase in _RANK]
            anchor = known[-1] if known else -1
        return {
            "sessionUpdate": "plan",
            "entries": [
                {
                    "content": label,
                    "priority": priority,
                    "status": self._status(_RANK[phase.value], anchor).value,
                }
                for phase, label, priority in shown
            ],
        }

    def ledger_summary(self, event: Mapping[str, Any], *, limit: int) -> dict[str, Any]:
        payload = event.get("payload")
        summary: Any = None
        if isinstance(payload, Mapping):
            summary = payload.get("summary")
            if not isinstance(summary, str):
                summary = payload.get("message")
        segments: list[tuple[str, bool]] = [
            ("[", False),
            (self._one_line(event.get("phase")), True),
            ("] ", False),
            (self._one_line(event.get("kind")), True),
        ]
        if isinstance(summary, str):
            segments += [(": ", False), (self._one_line(summary), True)]
        return self.agent_text(self._render(segments, limit))

    def untrusted(self, value: Any, *, limit: int) -> str:
        return self._render([(self._one_line(value), True)], limit)

    def available_commands(self, specs: Sequence[ChatSlashSpec]) -> dict[str, Any]:
        commands: list[dict[str, Any]] = []
        for spec in specs:
            command: dict[str, Any] = {"name": spec.slash, "description": spec.description}
            _, _, hint = spec.usage.partition(" ")
            if hint.strip():
                command["input"] = {"hint": hint.strip()}
            commands.append(command)
        return {"sessionUpdate": "available_commands_update", "availableCommands": commands}

    def current_mode(self, mode_id: str) -> dict[str, Any]:
        return {"sessionUpdate": "current_mode_update", "currentModeId": mode_id}

    @staticmethod
    def _status(rank: int, anchor: int) -> PlanEntryStatus:
        if rank < anchor:
            return PlanEntryStatus.COMPLETED
        if rank == anchor:
            return PlanEntryStatus.IN_PROGRESS
        return PlanEntryStatus.PENDING

    @staticmethod
    def _render(segments: Sequence[tuple[str, bool]], limit: int) -> str:
        """The segments joined, cut to `limit` characters as written (then "..."), each one
        marked untrusted escaped for Markdown after the cut, so no escape is ever split."""
        total = sum(len(text) for text, _ in segments)
        budget = total if total <= limit else max(limit - len(ELLIPSIS), 0)
        out: list[str] = []
        for text, untrusted in segments:
            piece = text[:budget]
            budget -= len(piece)
            out.append(
                "".join(f"\\{ch}" if ch in MARKDOWN_SPECIAL else ch for ch in piece)
                if untrusted
                else piece
            )
        if total > limit:
            out.append(ELLIPSIS)
        return "".join(out)

    @staticmethod
    def _one_line(value: Any) -> str:
        text = value if isinstance(value, str) else "?" if value is None else str(value)
        return "".join(ch if ch.isprintable() else " " for ch in text)
