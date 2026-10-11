# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Keeping what a local session sends the model small without taking anything it needs.

Measured on a real 130-turn session: every token of growth was a tool result (search 45%,
open_file 20%, find 15%, shell 14%), the model's own writes were under 1%, and because each
turn resends the whole history the session read 3.8M tokens to make seven writes. Everything
here is pure, makes no model call, and has a switch: `ContextEconomy` holds them all and
`ContextEconomy.off()` restores the old behaviour exactly.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from qwenloop.domain.model import ChatMessage
from qwenloop.domain.session_health import call_signature, estimate_tokens

#: Tools that only read, whose repeated identical answer need not be sent twice.
_READ_ONLY = frozenset({"search", "find", "open_file", "read_file", "outline"})
#: Tools after which an earlier read may no longer be true.
_MUTATING = frozenset({"write_file", "edit_file", "shell"})
_WRITING = frozenset({"write_file", "edit_file"})
STUB_PREFIX = "[earlier "
#: A result this short is not worth a stub: the stub would be about as long.
_MIN_MASKED_CHARS = 300
_MAX_STUBBED_ARGUMENT_CHARS = 200
_FILES_HEADING = "Files you are expected to create or change"


@dataclass(frozen=True, slots=True)
class ContextEconomy:
    """Which ways of keeping the context small are on. Each is a switch; 0 or False is off."""

    #: Tool results kept whole (the newest this many, and the last shell result). Older,
    #: longer ones become a one-line stub. 0 keeps every result whole.
    keep_full_results: int = 4
    #: Replace the body of an older write_file / edit_file call, which is on disk now.
    stub_written_arguments: bool = True
    #: Lines of shell output kept from the start and from the end. 0 keeps all of it.
    shell_head_lines: int = 20
    shell_tail_lines: int = 40
    #: Answer an identical read-only call whose result has not changed with a short note.
    fold_repeats: bool = True
    #: Tell the model each turn which of the item's planned files are written.
    ledger: bool = True

    @classmethod
    def off(cls) -> "ContextEconomy":
        return cls(0, False, 0, 0, False, False)


def fold_shell_output(text: str, head: int, tail: int) -> str:
    """The start and end of long output, with what was cut named. The end carries the verdict
    (a test run's failures, a build's error), so it gets more than the start."""
    lines = text.splitlines()
    if head <= 0 and tail <= 0 or len(lines) <= head + tail + 1:
        return text
    omitted = len(lines) - head - tail
    return "\n".join(
        [*lines[:head], f"... [{omitted} lines omitted from the middle] ...", *lines[-tail:]]
    )


def shape_result(
    name: str, result: Mapping[str, object], economy: ContextEconomy
) -> dict[str, object]:
    """A tool's answer as the model is shown it: shell output folded, the rest as it was."""
    shaped = dict(result)
    output = shaped.get("output")
    if name == "shell" and isinstance(output, str):
        shaped["output"] = fold_shell_output(
            output, economy.shell_head_lines, economy.shell_tail_lines
        )
    return shaped


def tool_name(name: str) -> str:
    """A call's tool, without the namespace some chat templates put in front of it."""
    return name.rpartition(".")[2]


class ResultDeduper:
    """Notices a read-only call asked twice with the same answer both times."""

    def __init__(self) -> None:
        self._seen: dict[str, tuple[int, str]] = {}

    def check(self, name: str, arguments: object, text: str, turn: int) -> str | None:
        """A short note when this call, made before, answered exactly the same; else None."""
        bare = tool_name(name)
        if bare not in _READ_ONLY:
            return None
        key = call_signature(bare, arguments)
        digest = hashlib.sha256(text.encode()).hexdigest()
        previous = self._seen.get(key)
        if previous is not None and previous[1] == digest:
            return f"[same result as turn {previous[0]}: nothing has changed since]"
        self._seen[key] = (turn, digest)
        return None

    def note_call(self, name: str) -> None:
        """A call that can change files makes every earlier read stale."""
        if tool_name(name) in _MUTATING:
            self._seen.clear()


def _arguments(call: Mapping[str, object]) -> dict[str, object]:
    function = call.get("function")
    if not isinstance(function, dict):
        return {}
    try:
        decoded = json.loads(str(function.get("arguments", "{}")))
    except ValueError:
        return {}
    return decoded if isinstance(decoded, dict) else {}


def _call_name(call: Mapping[str, object]) -> str:
    function = call.get("function")
    return tool_name(str(function.get("name", ""))) if isinstance(function, dict) else ""


def _calls(transcript: Sequence[ChatMessage]) -> dict[str, tuple[str, dict[str, object]]]:
    return {
        str(call.get("id")): (_call_name(call), _arguments(call))
        for message in transcript
        for call in message.tool_calls
    }


def _brief(name: str, arguments: Mapping[str, object]) -> str:
    argv = arguments.get("argv")
    if isinstance(argv, list):
        text = " ".join(map(str, argv))
    else:
        text = str(
            arguments.get("path") or arguments.get("query") or arguments.get("pattern") or ""
        )
    return f"{name} {text[:80]}".strip()


def mask_transcript(
    transcript: list[ChatMessage], keep_full: int, stub_writes: bool = True
) -> list[ChatMessage]:
    """The transcript with what the model no longer needs shown in full reduced to stubs.

    A tool result older than the newest `keep_full` becomes a one-line note of what was asked
    and how much came back (the model can ask again), except the last shell result, which is
    the freshest verdict on its work. Short results and notes stay as they are. The body of an
    older write_file / edit_file call goes too, since the file on disk is the truth. The system
    prompt and plan are never touched. 0 returns the transcript unchanged.
    """
    if keep_full <= 0:
        return transcript
    calls = _calls(transcript)
    tool_indexes = [i for i, m in enumerate(transcript) if m.role == "tool"]
    protected = set(tool_indexes[-keep_full:])
    shells = [
        i for i in tool_indexes if calls.get(transcript[i].tool_call_id or "", ("",))[0] == "shell"
    ]
    protected.update(shells[-1:])
    keep_calls = set([i for i, m in enumerate(transcript) if m.tool_calls][-keep_full:])
    failed = {
        m.tool_call_id for m in transcript if m.role == "tool" and "'error'" in m.content[:20]
    }
    masked = list(transcript)
    for index, message in enumerate(transcript):
        if index < 2:
            continue
        if message.role == "tool" and index not in protected:
            name, arguments = calls.get(message.tool_call_id or "", ("tool", {}))
            if len(message.content) >= _MIN_MASKED_CHARS and not message.content.startswith(
                STUB_PREFIX
            ):
                masked[index] = replace(
                    message,
                    content=(
                        f"{STUB_PREFIX}{_brief(name, arguments)}: {len(message.content)} "
                        "characters, not repeated here. Call it again if you need it.]"
                    ),
                )
        elif stub_writes and message.tool_calls and index not in keep_calls:
            masked[index] = replace(message, tool_calls=_stub_arguments(message, failed))
    return masked


def _stub_arguments(message: ChatMessage, failed: set[str | None]) -> tuple[dict[str, object], ...]:
    stubbed: list[dict[str, object]] = []
    for call in message.tool_calls:
        function = call.get("function")
        if (
            _call_name(call) not in _WRITING
            or call.get("id") in failed
            or not isinstance(function, dict)
            or not _arguments(call)
        ):
            stubbed.append(call)
            continue
        arguments = {
            key: (
                f"<{len(value)} characters omitted: the file on disk has them>"
                if isinstance(value, str)
                and len(value) > _MAX_STUBBED_ARGUMENT_CHARS
                and key != "path"
                else value
            )
            for key, value in _arguments(call).items()
        }
        stubbed.append(
            {
                **call,
                "function": {**function, "arguments": json.dumps(arguments, separators=(",", ":"))},
            }
        )
    return tuple(stubbed)


def expected_files(plan: str) -> tuple[str, ...]:
    """The files a work brief lists under its files heading, in order, none twice."""
    lines = plan.splitlines()
    found: list[str] = []
    for position, line in enumerate(lines):
        if not line.startswith(_FILES_HEADING):
            continue
        for item in lines[position + 1 :]:
            if not item.startswith("- "):
                break
            found.append(item[2:].strip())
        break
    return tuple(dict.fromkeys(path for path in found if path))


def ledger_note(
    expected: Sequence[str], written: Sequence[str], last_check: str | None
) -> str | None:
    """A few lines the model is shown at the end of every request: which planned files exist
    and how the last command ended. None when the plan names no files."""
    if not expected:
        return None
    done = [path for path in expected if path in written]
    todo = [path for path in expected if path not in written]
    lines = [f"[Progress: {len(done)} of {len(expected)} planned files written.]"]
    if todo:
        lines.append(f"Still to write: {', '.join(todo)}")
    else:
        lines.append("All planned files are written: run the verification commands.")
    extra = [path for path in written if path not in expected]
    if extra:
        lines.append(f"Also written: {', '.join(extra[-10:])}")
    if last_check:
        lines.append(f"Last command: {last_check}")
    return "\n".join(lines)


def composition(transcript: Sequence[ChatMessage]) -> dict[str, object]:
    """Estimated tokens of a request by what they are, for the event log: the system prompt and
    plan, the model's own turns, and each tool's results. Tuning needs this measured."""
    calls = _calls(transcript)
    results: dict[str, int] = {}
    assistant = 0
    for message in transcript[2:]:
        if message.role == "tool":
            name = calls.get(message.tool_call_id or "", ("tool", {}))[0] or "tool"
            results[name] = results.get(name, 0) + estimate_tokens(message.content)
        else:
            arguments = sum(len(str(call.get("function"))) for call in message.tool_calls)
            assistant += estimate_tokens(message.content) + arguments // 4
    head = sum(estimate_tokens(m.content) for m in transcript[:2])
    total = head + assistant + sum(results.values())
    return {"head": head, "assistant": assistant, "tool_results": results, "total": total}
