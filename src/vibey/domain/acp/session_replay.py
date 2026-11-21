# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""What an ACP session's log keeps of each update, and the update each kept event replays as.

**Recording.** Only what a prompt turn showed is kept: the operator's message, vibey's messages,
its tool calls and their outcomes, a plan. Each is kept as plain data -- the text as it read, not
the Markdown it was sent as -- with the fields a replay needs and nothing else (`recordable`). A
tool call's input is not kept. A payload whose JSON would pass `STORED_EVENT_BYTES` is cut, so
the hub never refuses one for its size.

**Replaying.** A kept event is untrusted data on its way back out. The hub stores what any holder
of the agent principal's key sent it, so nothing in a stored event is taken as structure, a
command, or a gate. `replay` builds each update from the closed set of fields it knows, checks
each value against what the protocol allows (an id's shape, a status, a kind, a mode this vibey
offers) and drops an event that fails; every piece of text goes through `UntrustedTextInterface`
-- a message as a `block`, a title as a `line`, a tool's result as `code` -- exactly as live
output does. Nothing a replay produces is a permission request, and nothing in it is parsed.

Pure: no I/O. Declared by `interfaces/session_replay_interface.py`.
"""

import json
import re
from collections.abc import Mapping, Sequence
from typing import Any, Final
from uuid import UUID

from vibey.domain.acp.interfaces.untrusted_text_interface import UntrustedTextInterface
from vibey.domain.acp.protocol import PlanEntryStatus, ToolCallStatus, ToolKind
from vibey.domain.acp.session_log import SESSION_ID_SHAPE, STORED_EVENT_BYTES, SessionEventKind
from vibey.domain.acp.untrusted_text import ELLIPSIS, UNTRUSTED_TEXT

TOOL_CALL_ID_SHAPE: Final = re.compile(r"[A-Za-z0-9._:-]{1,256}")
"""A tool call id as vibey makes one (`<turn>-1`, `<turn>-gate-<gate>`)."""
PLAN_PRIORITIES: Final = frozenset({"high", "medium", "low"})
REPLAY_CHARS: Final = STORED_EVENT_BYTES
"""The most characters of one stored text a replay shows: no more than recording keeps."""
_UNESCAPE: Final = re.compile(r"\\(\n|[\\`*_\[\]()<>!#|~&\-+=:.])")
"""A backslash `UntrustedText` put before a Markdown character, a line marker or a line break
(its hard break)."""
_FENCE: Final = re.compile(r"(`{3,})\n(.*)\n\1", re.DOTALL)
_KINDS: Final = frozenset(kind.value for kind in ToolKind)
_STATUSES: Final = frozenset(status.value for status in ToolCallStatus)
_PLAN_STATUSES: Final = frozenset(status.value for status in PlanEntryStatus)
CODE: Final = "code"
"""A stored tool result's format when it was shown as a code block."""


class AcpSessionReplay:
    """Declared by `interfaces/session_replay_interface.py::AcpSessionReplayInterface`."""

    def __init__(self, text: UntrustedTextInterface = UNTRUSTED_TEXT) -> None:
        self._text = text

    # -- what is kept ---------------------------------------------------------------------

    def recordable(
        self, update: Mapping[str, Any]
    ) -> tuple[SessionEventKind, dict[str, Any]] | None:
        kind = update.get("sessionUpdate")
        if kind == "agent_message_chunk":
            content = update.get("content")
            if not isinstance(content, Mapping) or not isinstance(content.get("text"), str):
                return None
            return SessionEventKind.AGENT_MESSAGE, self.fit({"text": self.plain(content["text"])})
        if kind in ("tool_call", "tool_call_update"):
            return self._tool_call(update)
        if kind == "plan":
            entries = update.get("entries")
            if not isinstance(entries, list):
                return None
            kept = [self._plan_entry(entry, as_shown=True) for entry in entries]
            return SessionEventKind.PLAN, self.fit({"entries": [e for e in kept if e is not None]})
        return None

    def user_message(self, text: str) -> dict[str, Any]:
        return self.fit({"text": text})

    def title(self, text: str, *, limit: int) -> str | None:
        first = next((line for line in text.splitlines() if line.strip()), "")
        shown = self._text.one_line(first).strip()
        if not shown:
            return None
        return shown if len(shown) <= limit else shown[: max(limit - len(ELLIPSIS), 0)] + ELLIPSIS

    def plain(self, text: str) -> str:
        fenced = _FENCE.fullmatch(text)
        body = fenced.group(2) if fenced is not None else text
        return _UNESCAPE.sub(lambda match: match.group(1), body)

    def fit(self, payload: dict[str, Any]) -> dict[str, Any]:
        """`payload` cut until its JSON fits `STORED_EVENT_BYTES`: its longest text first, and
        a plan's last entries."""
        fitted = dict(payload)
        while (size := self._size(fitted)) > STORED_EVENT_BYTES:
            texts = [key for key in ("text", "title") if isinstance(fitted.get(key), str)]
            key = max(texts, key=lambda name: len(fitted[name]), default=None)
            if key is not None and len(fitted[key]) > len(ELLIPSIS):
                value: str = fitted[key]
                keep = max(len(value) * STORED_EVENT_BYTES // size - 64, 0)
                fitted[key] = value[:keep] + ELLIPSIS
            elif isinstance(fitted.get("entries"), list) and fitted["entries"]:
                fitted["entries"] = fitted["entries"][: len(fitted["entries"]) // 2]
            else:
                return {}  # nothing left to cut: kept as an empty event, never refused
        return fitted

    # -- what a kept event replays as -----------------------------------------------------

    def replay(self, kind: str, payload: Any, *, modes: Sequence[str]) -> dict[str, Any] | None:
        if not isinstance(payload, Mapping):
            return None
        if kind in (SessionEventKind.USER_MESSAGE, SessionEventKind.AGENT_MESSAGE):
            text = payload.get("text")
            if not isinstance(text, str):
                return None
            shown = self._text.block(text, limit=REPLAY_CHARS)
            chunk = (
                "user_message_chunk"
                if kind == SessionEventKind.USER_MESSAGE
                else ("agent_message_chunk")
            )
            return {"sessionUpdate": chunk, "content": {"type": "text", "text": shown}}
        if kind == SessionEventKind.TOOL_CALL:
            return self._replay_call(payload)
        if kind == SessionEventKind.TOOL_CALL_UPDATE:
            return self._replay_update(payload)
        if kind == SessionEventKind.PLAN:
            entries = payload.get("entries")
            if not isinstance(entries, list):
                return None
            kept = [self._replay_entry(entry) for entry in entries]
            return {"sessionUpdate": "plan", "entries": [e for e in kept if e is not None]}
        if kind == SessionEventKind.MODE:
            mode_id = self.mode(payload, modes=modes)
            if mode_id is None:
                return None
            return {"sessionUpdate": "current_mode_update", "currentModeId": mode_id}
        return None  # attach, title and closed change the session; they show nothing

    def mode(self, payload: Any, *, modes: Sequence[str]) -> str | None:
        mode_id = payload.get("modeId") if isinstance(payload, Mapping) else None
        return mode_id if isinstance(mode_id, str) and mode_id in modes else None

    def project(self, payload: Any) -> UUID | None:
        raw = payload.get("projectId") if isinstance(payload, Mapping) else None
        if not isinstance(raw, str):
            return None
        try:
            project = UUID(raw)
        except ValueError:
            return None
        return project if str(project) == raw else None

    def folder(self, value: Any) -> str | None:
        """A stored folder as a session picker may show it: through the one-line rule (no
        control, format, bidi or line-separator character), and absolute. A folder the rule
        would change is None: shown changed, a load naming it would never find the session."""
        if not isinstance(value, str) or not value.startswith("/"):
            return None
        shown = self._text.one_line(value)
        return shown if shown == value else None

    def valid_session_id(self, value: Any) -> bool:
        return isinstance(value, str) and SESSION_ID_SHAPE.fullmatch(value) is not None

    # -- helpers --------------------------------------------------------------------------

    def _tool_call(
        self, update: Mapping[str, Any]
    ) -> tuple[SessionEventKind, dict[str, Any]] | None:
        call_id, status = update.get("toolCallId"), update.get("status")
        if not self._call_id(call_id) or status not in _STATUSES:
            return None
        kept: dict[str, Any] = {"toolCallId": call_id, "status": status}
        if isinstance(update.get("title"), str):
            kept["title"] = self.plain(update["title"])
        if update.get("kind") in _KINDS:
            kept["kind"] = update["kind"]
        if update.get("sessionUpdate") == "tool_call":
            return SessionEventKind.TOOL_CALL, self.fit(kept)
        content = update.get("content")
        if isinstance(content, list) and content:
            first = content[0]
            inner = first.get("content") if isinstance(first, Mapping) else None
            shown = inner.get("text") if isinstance(inner, Mapping) else None
            if isinstance(shown, str):
                kept["text"] = self.plain(shown)
                if _FENCE.fullmatch(shown) is not None:
                    kept["format"] = CODE
        return SessionEventKind.TOOL_CALL_UPDATE, self.fit(kept)

    def _replay_call(self, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        call_id, title = payload.get("toolCallId"), payload.get("title")
        if not self._call_id(call_id) or not isinstance(title, str):
            return None
        update: dict[str, Any] = {
            "sessionUpdate": "tool_call",
            "toolCallId": call_id,
            "title": self._text.line(title, limit=REPLAY_CHARS),
        }
        if payload.get("kind") in _KINDS:
            update["kind"] = payload["kind"]
        if payload.get("status") in _STATUSES:
            update["status"] = payload["status"]
        return update

    def _replay_update(self, payload: Mapping[str, Any]) -> dict[str, Any] | None:
        call_id, status = payload.get("toolCallId"), payload.get("status")
        if not self._call_id(call_id) or status not in _STATUSES:
            return None
        update: dict[str, Any] = {
            "sessionUpdate": "tool_call_update",
            "toolCallId": call_id,
            "status": status,
        }
        if isinstance(payload.get("title"), str):
            update["title"] = self._text.line(payload["title"], limit=REPLAY_CHARS)
        if payload.get("kind") in _KINDS:
            update["kind"] = payload["kind"]
        text = payload.get("text")
        if isinstance(text, str):
            shown = (
                self._text.code(text, limit=REPLAY_CHARS)
                if payload.get("format") == CODE
                else self._text.line(text, limit=REPLAY_CHARS)
            )
            update["content"] = [{"type": "content", "content": {"type": "text", "text": shown}}]
        return update

    def _plan_entry(self, entry: Any, *, as_shown: bool) -> dict[str, Any] | None:
        """One plan entry's content, status and priority, or None when one is missing or not
        a value the protocol allows. `as_shown`: the content is Markdown as it was sent, so it
        is kept as the text it read."""
        if not isinstance(entry, Mapping) or not isinstance(entry.get("content"), str):
            return None
        if (
            entry.get("status") not in _PLAN_STATUSES
            or entry.get("priority") not in PLAN_PRIORITIES
        ):
            return None
        content: str = entry["content"]
        return {
            "content": self.plain(content) if as_shown else content,
            "status": entry["status"],
            "priority": entry["priority"],
        }

    def _replay_entry(self, entry: Any) -> dict[str, Any] | None:
        kept = self._plan_entry(entry, as_shown=False)
        if kept is None:
            return None
        return {**kept, "content": self._text.line(kept["content"], limit=REPLAY_CHARS)}

    @staticmethod
    def _call_id(value: Any) -> bool:
        return isinstance(value, str) and TOOL_CALL_ID_SHAPE.fullmatch(value) is not None

    @staticmethod
    def _size(payload: Mapping[str, Any]) -> int:
        return len(json.dumps(payload).encode())


SESSION_REPLAY: Final = AcpSessionReplay()
