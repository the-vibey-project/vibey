# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading the wire log back: the records, following them as they land, and the text
`vibey llm tail` shows for each (see `wire_log.py` for what is written)."""

import json
import time
from collections.abc import Callable, Iterator, Mapping
from datetime import datetime
from pathlib import Path

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
    pending = b""
    while True:
        try:
            size: int | None = path.stat().st_size
        except FileNotFoundError:
            size = None
        if size is not None and size < offset:
            offset, pending = 0, b""
        if size is None or size == offset:
            sleep(poll_seconds)
            continue
        with path.open("rb") as handle:
            handle.seek(offset)
            data = handle.read()
        offset += len(data)
        *lines, pending = (pending + data).split(b"\n")
        for line in lines:
            record = parse_line(line)
            if record is not None:
                yield record


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
        return closing + json.dumps(record, ensure_ascii=False) + "\n"

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
