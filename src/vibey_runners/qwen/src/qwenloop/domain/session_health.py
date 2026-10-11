# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeping one long local session useful: renewing its context and noticing a stall.

A local model's answers degrade as its context fills: a 20B model that had read ninety
thousand tokens of its own history was, by turn 100, writing "Cannot finish" into a file and
reporting that a file it had written itself was "corrupted". Both functions here are pure and
make no model call.
"""

import json
from collections import deque
from collections.abc import Iterable, Sequence

from qwenloop.domain.model import ChatMessage

#: How many of the newest messages survive a renewal untouched, so the model still sees the
#: last thing it did and what came back.
KEEP_RECENT_MESSAGES = 6
#: The most entries one section of the work summary lists.
_MAX_LISTED = 30
#: The most characters of an earlier summary carried into the next one.
_MAX_CARRIED_CHARS = 2000
#: The most characters of a shell result shown in the summary.
_MAX_RESULT_CHARS = 120
#: How many shell commands the summary lists, newest last.
_MAX_COMMANDS = 8
RENEWAL_NOTE_PREFIX = "[This session was renewed to keep your context short."
_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def call_signature(name: str, arguments: object) -> str:
    """One tool call as a comparable string: the tool and exactly what it was given."""
    return f"{name}:{json.dumps(arguments, sort_keys=True, default=str)}"


def _arguments_of(call: dict[str, object]) -> dict[str, object]:
    function = call.get("function")
    if not isinstance(function, dict):
        return {}
    try:
        decoded = json.loads(str(function.get("arguments", "{}")))
    except ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _name_of(call: dict[str, object]) -> str:
    function = call.get("function")
    return str(function.get("name", "")) if isinstance(function, dict) else ""


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(value for value in values if value))[-_MAX_LISTED:]


def work_summary(dropped: Sequence[ChatMessage]) -> str:
    """What the dropped messages did, read off their tool calls: files written, edited and
    read, and the last shell commands with how each ended."""
    written: list[str] = []
    edited: list[str] = []
    read: list[str] = []
    commands: list[tuple[str, str]] = []
    results = {m.tool_call_id: m.content for m in dropped if m.role == "tool" and m.tool_call_id}
    carried = ""
    for message in dropped:
        if message.role == "user" and message.content.startswith(RENEWAL_NOTE_PREFIX):
            carried = "\n".join(message.content.splitlines()[1:])[:_MAX_CARRIED_CHARS]
        for call in message.tool_calls:
            name, arguments = _name_of(call), _arguments_of(call)
            path = str(arguments.get("path", ""))
            if name == "write_file":
                written.append(path)
            elif name == "edit_file":
                edited.append(path)
            elif name == "read_file":
                read.append(path)
            elif name == "shell":
                argv = arguments.get("argv")
                text = " ".join(map(str, argv)) if isinstance(argv, list) else str(argv or "")
                outcome = results.get(str(call.get("id")), "")[:_MAX_RESULT_CHARS]
                commands.append((text, outcome.replace("\n", " ")))
    lines = [
        f"{RENEWAL_NOTE_PREFIX} Your earlier turns are summarised here. The files on disk "
        "are the truth: read one again before you change it.]"
    ]
    for label, values in (
        ("Files you wrote", _unique(written)),
        ("Files you edited", _unique(edited)),
        ("Files you read", _unique(read)),
    ):
        if values:
            lines.append(f"{label}: {', '.join(values)}")
    for text, outcome in commands[-_MAX_COMMANDS:]:
        lines.append(f"Ran `{text}` -> {outcome}" if outcome else f"Ran `{text}`")
    if carried:
        lines.append(f"Before that: {carried}")
    return "\n".join(lines)


def renew_transcript(
    transcript: list[ChatMessage], threshold_tokens: int
) -> tuple[list[ChatMessage], int]:
    """The transcript, with everything but its head and newest messages replaced by a summary
    once it passes `threshold_tokens`; and how many messages that replaced (0 when it did not).

    The system prompt and plan (the first two messages) stay. The kept tail starts at an
    assistant message, never at a tool result whose call was dropped. 0 turns renewal off.
    """
    total = sum(estimate_tokens(message.content) for message in transcript)
    if threshold_tokens <= 0 or total <= threshold_tokens:
        return transcript, 0
    rest = transcript[2:]
    split = len(rest) - KEEP_RECENT_MESSAGES
    while split > 0 and rest[split].role == "tool":
        split -= 1
    if split <= 0:
        return transcript, 0
    note = ChatMessage("user", work_summary(rest[:split]))
    return [*transcript[:2], note, *rest[split:]], split


class StallDetector:
    """Notices a session that has stopped finding anything new to do.

    A turn is novel when it makes a tool call this session has not made in its last `memory`
    calls. `limit` consecutive turns with no novel call (text only, or the same calls over
    again) is a stall; `limit` 0 never stalls. Judged on the calls, not on what the model says,
    so it needs no list of phrases."""

    def __init__(self, limit: int, memory: int = 20) -> None:
        self._limit = limit
        self._seen: deque[str] = deque(maxlen=memory)
        self.stalled_turns = 0

    def observe(self, signatures: Sequence[str]) -> bool:
        novel = any(signature not in self._seen for signature in signatures)
        self._seen.extend(signatures)
        self.stalled_turns = 0 if novel else self.stalled_turns + 1
        return 0 < self._limit <= self.stalled_turns
