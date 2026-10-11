# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading the wire log back: the records, following them as they land, and the text
`vibey llm tail` shows for each (see `wire_log.py` for what is written).

The wire log also holds one `session` record per engine session (`session_log.py`), naming the
file that session writes its events to. `follow_live` follows the wire log and the newest
session's events together, and moves to the next session by itself when one starts, so the tail
shows DESIGN, DECOMPOSE, BUILD and REVIEW in one stream."""

import json
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from pathlib import Path
from typing import Literal

#: How long the follower waits when the file has nothing new.
POLL_SECONDS = 0.25

WireRecord = dict[str, object]


def parse_line(raw: bytes | str) -> WireRecord | None:
    """One record, or None for a line that is not a JSON object (a torn or foreign line
    must not stop an operator watching)."""
    try:
        value = json.loads(raw)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def snapshot(path: Path) -> tuple[list[WireRecord], int]:
    """Every whole record now in the file, and the offset just past the last whole line,
    which is where following continues so a half-written line is never read twice."""
    data = path.read_bytes()
    end = data.rfind(b"\n") + 1
    records = [r for r in map(parse_line, data[:end].splitlines()) if r is not None]
    return records, end


def start_of_latest_call(records: list[WireRecord]) -> int:
    """Index of the first record of the most recent call: its first attempt's request."""
    for index in range(len(records) - 1, -1, -1):
        if records[index].get("kind") == "request" and records[index].get("attempt") == 1:
            return index
    return 0


class LineTailer:
    """The whole lines appended to one file since an offset. A file that does not exist yet
    has none, and one that shrinks (removed, rotated) is read again from its beginning. A
    half-written last line is held until its newline arrives, so it is never read twice."""

    __slots__ = ("offset", "path", "_pending")

    def __init__(self, path: Path, offset: int = 0) -> None:
        self.path = path
        self.offset = offset
        self._pending = b""

    def read_new(self) -> list[WireRecord]:
        try:
            size = self.path.stat().st_size
        except FileNotFoundError:
            return []
        if size < self.offset:
            self.offset, self._pending = 0, b""
        if size == self.offset:
            return []
        with self.path.open("rb") as handle:
            handle.seek(self.offset)
            data = handle.read()
        self.offset += len(data)
        *lines, self._pending = (self._pending + data).split(b"\n")
        return [record for record in map(parse_line, lines) if record is not None]


def follow_records(
    path: Path,
    offset: int,
    *,
    poll_seconds: float = POLL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[WireRecord]:
    """Records as they are appended, from `offset`, forever. The file may not exist yet,
    and may shrink (the operator removed it, or it was rotated): following then starts over
    from its beginning."""
    tailer = LineTailer(path, offset)
    while True:
        records = tailer.read_new()
        if not records:
            sleep(poll_seconds)
            continue
        yield from records


Source = Literal["wire", "run"]


def follow_live(
    path: Path,
    offset: int,
    *,
    session: WireRecord | None = None,
    session_offset: int = 0,
    poll_seconds: float = POLL_SECONDS,
    sleep: Callable[[float], None] = time.sleep,
) -> Iterator[tuple[Source, WireRecord, WireRecord | None]]:
    """The wire log and the newest engine session's events, together, forever.

    Yields `("wire", record, None)` for each wire-log record and `("run", event, session)` for
    each event of the session it belongs to. A `session` record in the wire log switches the
    follow to that session's file at once; the one being left is read to its end first, so none
    of its last events are lost. `session` and `session_offset` say where to pick up a session
    the caller has already shown."""
    wire = LineTailer(path, offset)
    current = session
    run = LineTailer(Path(str(session["events_path"])), session_offset) if session else None
    while True:
        moved = False
        for record in wire.read_new():
            moved = True
            if record.get("kind") == "session":
                if run is not None:
                    for event in run.read_new():
                        yield "run", event, current
                current = record
                run = LineTailer(Path(str(record["events_path"])))
            yield "wire", record, None
        if run is not None:
            for event in run.read_new():
                moved = True
                yield "run", event, current
        if not moved:
            sleep(poll_seconds)


def session_events(session: WireRecord) -> tuple[list[WireRecord], int]:
    """What a session's event file holds now, and the offset to follow from; nothing yet when
    the runner has not created it."""
    path = Path(str(session["events_path"]))
    return snapshot(path) if path.exists() else ([], 0)


def last_session_index(records: list[WireRecord]) -> int | None:
    """Index of the newest `session` record, if any."""
    for index in range(len(records) - 1, -1, -1):
        if records[index].get("kind") == "session":
            return index
    return None


def _clock(record: Mapping[str, object]) -> str:
    stamp = record.get("ts")
    try:
        return datetime.fromisoformat(str(stamp)).astimezone().strftime("%H:%M:%S")
    except ValueError:
        return "--:--:--"


def _number(value: object) -> float | None:
    return float(value) if isinstance(value, int | float) and not isinstance(value, bool) else None


class WireFormatter:
    """Turns records into text, one `render` at a time.

    Streamed text is appended where the last piece ended, so the answer grows on one line
    of output the way it does in the model; anything else first closes that line. The
    formatter holds that one fact (which stream is open) and nothing else."""

    def __init__(self, *, max_chars: int | None = None) -> None:
        self._max_chars = max_chars
        self._open: tuple[str, int, str] | None = None
        self._streamed: set[tuple[str, int]] = set()

    def close(self) -> str:
        """The newline that ends an answer left open, when output moves to another stream."""
        closing = "\n" if self._open is not None else ""
        self._open = None
        return closing

    def render(self, record: Mapping[str, object]) -> str:
        kind = record.get("kind")
        if kind == "chunk":
            return self._chunk(record)
        closing = "\n" if self._open is not None else ""
        self._open = None
        if kind == "request":
            return closing + self._request(record)
        if kind == "response":
            return closing + self._response(record)
        if kind == "error":
            return closing + self._error(record)
        if kind == "session":
            return closing + self._session(record)
        return closing + json.dumps(record, ensure_ascii=False) + "\n"

    @staticmethod
    def _session(record: Mapping[str, object]) -> str:
        """The banner above an engine session's events: which engine, which work item."""
        item = record.get("work_item")
        where = f" - work item {item}" if item else ""
        run = str(record.get("run_id") or "")[:8]
        return f"[{_clock(record)}] === {record.get('engine')} session{where} - run {run} ===\n"

    def _label(self, record: Mapping[str, object]) -> str:
        return f"{record.get('call')} attempt {record.get('attempt')}"

    def _text(self, text: str, indent: str = "    ") -> str:
        extra = ""
        if self._max_chars is not None and len(text) > self._max_chars:
            extra = f"\n{indent}... [{len(text) - self._max_chars} more characters]"
            text = text[: self._max_chars]
        return "".join(f"{indent}{line}\n" for line in text.splitlines() or [""]) + (
            extra + "\n" if extra else ""
        )

    def _request(self, record: Mapping[str, object]) -> str:
        payload = record.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        options = payload.get("options")
        options = options if isinstance(options, dict) else {}
        form = payload.get("format")
        shape = "json" if form == "json" else "schema" if isinstance(form, dict) else "free text"
        head = (
            f"[{_clock(record)}] >>> request {self._label(record)} - {payload.get('model')}"
            f" - num_ctx {options.get('num_ctx')} - num_predict {options.get('num_predict')}"
            f" - answer as {shape}\n"
        )
        messages = payload.get("messages")
        body = ""
        for message in messages if isinstance(messages, list) else []:
            if isinstance(message, dict):
                body += f"  {message.get('role')}:\n{self._text(str(message.get('content')))}"
        return head + body

    def _chunk(self, record: Mapping[str, object]) -> str:
        call, attempt = str(record.get("call")), record.get("attempt")
        out = ""
        for field, label in (("thinking", "thinking"), ("content", "answer")):
            text = record.get(field)
            if not isinstance(text, str) or not text:
                continue
            key = (call, attempt if isinstance(attempt, int) else 0, field)
            if self._open != key:
                out += ("\n" if self._open is not None else "") + f"  {label}: "
                self._open = key
            self._streamed.add(key[:2])
            out += text
        return out

    def _response(self, record: Mapping[str, object]) -> str:
        body = record.get("body")
        body = body if isinstance(body, dict) else {}
        facts = [f"{_number(record.get('elapsed_s')) or 0:.1f}s"]
        prompt, output = _number(body.get("prompt_eval_count")), _number(body.get("eval_count"))
        if prompt is not None:
            facts.append(f"prompt {prompt:.0f} tokens")
        if output is not None:
            facts.append(f"output {output:.0f} tokens")
        duration = _number(body.get("eval_duration"))
        if output is not None and duration:
            facts.append(f"{output / (duration / 1e9):.1f} tokens/s")
        if body.get("done_reason"):
            facts.append(f"stopped: {body['done_reason']}")
        # Where the time went besides generating: a model reloaded from disk (`load`) or a long
        # prompt read (`prompt eval`) can cost minutes the token rate never shows.
        for key, label in (("load_duration", "load"), ("prompt_eval_duration", "prompt eval")):
            nanoseconds = _number(body.get(key))
            if nanoseconds is not None:
                facts.append(f"{label} {nanoseconds / 1e9:.1f}s")
        out = f"[{_clock(record)}] <<< response {self._label(record)} - " + " - ".join(facts) + "\n"
        attempt = record.get("attempt")
        shown = (str(record.get("call")), attempt if isinstance(attempt, int) else 0)
        message = body.get("message")
        said = message.get("content") if isinstance(message, dict) else None
        if shown not in self._streamed and isinstance(said, str) and said:
            out += "  answer:\n" + self._text(said)
        return out

    def _error(self, record: Mapping[str, object]) -> str:
        return (
            f"[{_clock(record)}] !!! error {self._label(record)} - "
            f"{_number(record.get('elapsed_s')) or 0:.1f}s - "
            f"{record.get('error_type')}: {record.get('error')}\n"
        )


_RESULT_LIMIT = 300
_ARGUMENT_LIMIT = 240


def _brief(value: object, limit: int) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "\u2026"


def _seconds(milliseconds: object) -> str:
    number = _number(milliseconds)
    return "?" if number is None else f"{number / 1000:.1f}s"


class RunEventFormatter:
    """Turns one engine session's events into text: what the model asked for, what came back,
    what it said and how long each turn took.

    The model's answer arrives as many `text_delta` fragments; like `WireFormatter`, this
    appends them where the last one ended so the answer grows on one line of output, and any
    other event first closes that line. It holds that one fact (is an answer open) and nothing
    else."""

    def __init__(self, *, max_chars: int | None = None) -> None:
        self._max = max_chars
        self._streaming = False

    def close(self) -> str:
        """The newline that ends an answer left open, when output moves to another stream."""
        closing = "\n" if self._streaming else ""
        self._streaming = False
        return closing

    def render(self, event: Mapping[str, object]) -> str:
        kind = str(event.get("type") or event.get("event_type") or event.get("kind") or "event")
        if kind == "text_delta":
            opening = "" if self._streaming else "  answer: "
            self._streaming = True
            return opening + str(event.get("text", ""))
        closing = "\n" if self._streaming else ""
        self._streaming = False
        return closing + self._line(kind, event) + "\n"

    def _line(self, kind: str, event: Mapping[str, object]) -> str:
        limit = self._max or _ARGUMENT_LIMIT
        if kind == "reasoning":
            text = str(event.get("text", ""))
            shown = text if self._max is None else text[: self._max]
            return "  thinking: " + shown.strip().replace("\n", "\n    ")
        if kind == "tool.call":
            return (
                f"  turn {event.get('turn')} -> {event.get('name')} "
                f"{_brief(event.get('arguments', {}), limit)}"
            )
        if kind == "tool_result":
            return f"    <- {event.get('name')}: {self._result(event.get('result'))}"
        if kind == "turn.completed":
            return (
                f"  turn {event.get('turn')} done - {_seconds(event.get('duration_ms'))}"
                f" (model {_seconds(event.get('model_ms'))})"
                f" - in {event.get('input_tokens')} tokens - out {event.get('output_tokens')} tokens"
            )
        if kind == "failed":
            return (
                f"  !!! failed: {event.get('reason')} (turn {event.get('turn')} of "
                f"{event.get('max_turns')})"
            )
        if kind == "prompt.received":
            return f"  >>> prompt: {_brief(event.get('text', ''), limit)}"
        return f"  {kind} {_brief({k: v for k, v in event.items() if k != 'type'}, limit)}"

    def _result(self, result: object) -> str:
        limit = self._max or _RESULT_LIMIT
        if not isinstance(result, Mapping):
            return _brief(result, limit)
        if "error" in result:
            return f"error: {_brief(result['error'], limit)}"
        if "exit_code" in result:
            output = str(result.get("output", "")).strip()
            tail = _brief(output[-limit:], limit) if output else ""
            return f"exit {result['exit_code']}" + (f" - {tail}" if tail else "")
        if "matches" in result or "files" in result:
            found = result.get("count", len(result.get("matches") or result.get("files") or []))
            return f"{found} found"
        if "content" in result:
            return f"{len(str(result['content']))} characters"
        if "written" in result:
            return f"wrote {result['written']} characters"
        return _brief(dict(result), limit)
