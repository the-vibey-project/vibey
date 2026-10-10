# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The wire log: every request to, and every streamed word from, the local model.

`-vvv` has always promised "full payloads", and the sovereign providers' traffic to Ollama
reached no log at all: a DESIGN call that ran for fifteen minutes showed nothing until it
returned. With the wire log on, the client streams the reply and appends one JSON line per
event to a file that `vibey llm tail` follows as it grows.

Records (one JSON object per line, `v` is the format version):

- `request`  -- `call`, `attempt`, `url`, `payload` (the whole body: model, messages, schema).
- `chunk`    -- `call`, `attempt`, `content` and/or `thinking`: what the model produced.
- `response` -- `call`, `attempt`, `elapsed_s`, `body` (the assembled answer and Ollama's
  own counts and timings).
- `error`    -- `call`, `attempt`, `elapsed_s`, `error_type`, `error`.

**Redaction.** Every record passes through the ledger's redactor. Streamed text cannot be
redacted fragment by fragment, since a credential split across two tokens would match no
pattern in either, so a chunk is held back until a whitespace boundary and redacted whole:
a credential (which holds no whitespace) always sits inside one emitted piece. The cost is
that text appears a word at a time, not a token at a time. The file is created readable by
its owner alone and is never replicated anywhere.
"""

import json
import os
import sys
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

from vibey.infrastructure.ledger.redact import redact_payload

WIRE_LOG_ENV: Final[str] = "VIBEY_LLM_WIRE_LOG"
WIRE_LOG_VERSION: Final[int] = 1


def default_wire_log_path() -> Path:
    """Where `-vvv` writes the wire log: beside the sovereign-fit record."""
    return Path.home() / ".local" / "state" / "vibey" / "llm-wire.jsonl"


class StreamRedactor:
    """Releases streamed text only up to the last whitespace, so a redacted piece never
    cuts a credential in two. `flush` releases the remainder when the stream ends."""

    __slots__ = ("_held",)

    def __init__(self) -> None:
        self._held = ""

    def feed(self, text: str) -> str:
        """Adds `text`; returns the part now safe to emit (possibly empty)."""
        self._held += text
        cut = max(self._held.rfind(" "), self._held.rfind("\n"), self._held.rfind("\t")) + 1
        if cut == 0:
            return ""
        released, self._held = self._held[:cut], self._held[cut:]
        return _redacted_text(released)

    def flush(self) -> str:
        released, self._held = self._held, ""
        return _redacted_text(released)


def _redacted_text(text: str) -> str:
    redacted = redact_payload({"text": text})["text"]
    return str(redacted)


class NullWireLog:
    """The wire log when nobody asked for one."""

    def request(self, call: str, attempt: int, url: str, payload: Mapping[str, object]) -> None:
        return None

    def chunk(self, call: str, attempt: int, *, content: str, thinking: str) -> None:
        return None

    def response(
        self, call: str, attempt: int, body: Mapping[str, object], elapsed_seconds: float
    ) -> None:
        return None

    def error(self, call: str, attempt: int, error: BaseException, elapsed_seconds: float) -> None:
        return None


class JsonlWireLog:
    """Appends wire records to one file. Diagnostics never fail the work: the first write
    error is said once on stderr and the log goes quiet for the rest of the process."""

    def __init__(
        self,
        path: Path,
        *,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self._path = path
        self._clock = clock
        self._handle: Any = None
        self._failed = False
        self._open: dict[tuple[str, int], dict[str, StreamRedactor]] = {}

    @property
    def path(self) -> Path:
        return self._path

    def request(self, call: str, attempt: int, url: str, payload: Mapping[str, object]) -> None:
        self._write("request", call, attempt, url=url, payload=dict(payload))

    def chunk(self, call: str, attempt: int, *, content: str, thinking: str) -> None:
        streams = self._open.setdefault((call, attempt), {})
        pieces: dict[str, str] = {}
        for field, text in (("content", content), ("thinking", thinking)):
            if text:
                released = streams.setdefault(field, StreamRedactor()).feed(text)
                if released:
                    pieces[field] = released
        if pieces:
            self._emit("chunk", call, attempt, pieces)

    def response(
        self, call: str, attempt: int, body: Mapping[str, object], elapsed_seconds: float
    ) -> None:
        self._flush(call, attempt)
        self._write("response", call, attempt, elapsed_s=round(elapsed_seconds, 3), body=dict(body))

    def error(self, call: str, attempt: int, error: BaseException, elapsed_seconds: float) -> None:
        self._flush(call, attempt)
        self._write(
            "error",
            call,
            attempt,
            elapsed_s=round(elapsed_seconds, 3),
            error_type=type(error).__name__,
            error=str(error),
        )

    def _flush(self, call: str, attempt: int) -> None:
        streams = self._open.pop((call, attempt), {})
        pieces = {field: text for field, redactor in streams.items() if (text := redactor.flush())}
        if pieces:
            self._emit("chunk", call, attempt, pieces)

    def _write(self, kind: str, call: str, attempt: int, **fields: object) -> None:
        self._emit(kind, call, attempt, redact_payload(fields))

    def _emit(self, kind: str, call: str, attempt: int, fields: Mapping[str, object]) -> None:
        if self._failed:
            return
        record = {
            "v": WIRE_LOG_VERSION,
            "ts": self._clock().isoformat(),
            "kind": kind,
            "call": call,
            "attempt": attempt,
            **fields,
        }
        try:
            if self._handle is None:
                self._path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                descriptor = os.open(self._path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
                self._handle = os.fdopen(descriptor, "a", encoding="utf-8")
            self._handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            self._handle.flush()
        except OSError as exc:
            self._failed = True
            sys.stderr.write(f"vibey: the LLM wire log {self._path} cannot be written ({exc})\n")
