# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The wire log: what is written, how it is redacted, and that it never fails the work."""

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vibey.infrastructure.engines.interfaces.ollama_chat_interface import WireLogInterface
from vibey.infrastructure.engines.wire_log import (
    WIRE_LOG_ENV,
    WIRE_LOG_VERSION,
    JsonlWireLog,
    NullWireLog,
    StreamRedactor,
    default_wire_log_path,
)

SECRET = "sk-" + "a1B2c3D4e5F6g7H8i9J0"
NOW = datetime(2026, 10, 10, 22, 4, 11, tzinfo=UTC)


def _records(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _log(path: Path) -> JsonlWireLog:
    return JsonlWireLog(path, clock=lambda: NOW)


def test_the_default_path_sits_beside_the_sovereign_fit_record() -> None:
    assert default_wire_log_path() == Path.home() / ".local/state/vibey/llm-wire.jsonl"
    assert WIRE_LOG_ENV == "VIBEY_LLM_WIRE_LOG"


def test_text_is_released_only_up_to_the_last_whitespace() -> None:
    redactor = StreamRedactor()
    assert redactor.feed("Hel") == ""
    assert redactor.feed("lo wor") == "Hello "
    assert redactor.feed("ld\nnext") == "world\n"
    assert redactor.feed("\tend") == "next\t"
    assert redactor.flush() == "end"
    assert redactor.flush() == ""


def test_a_credential_split_across_pieces_is_redacted_whole() -> None:
    redactor = StreamRedactor()
    released = [redactor.feed(piece) for piece in ("key is ", SECRET[:6], SECRET[6:], " ok")]
    released.append(redactor.flush())
    joined = "".join(released)
    assert SECRET not in joined
    assert SECRET[:6] not in joined
    assert joined == "key is [REDACTED] ok"


def test_a_request_is_written_whole_and_redacted(tmp_path: Path) -> None:
    path = tmp_path / "state" / "wire.jsonl"
    log = _log(path)
    log.request("c1", 1, "http://x/api/chat", {"model": "m", "api_key": "hunter2", "text": SECRET})

    (record,) = _records(path)
    assert record["v"] == WIRE_LOG_VERSION
    assert record["ts"] == NOW.isoformat()
    assert (record["kind"], record["call"], record["attempt"]) == ("request", "c1", 1)
    assert record["url"] == "http://x/api/chat"
    assert record["payload"] == {"model": "m", "api_key": "[REDACTED]", "text": "[REDACTED]"}
    assert log.path == path


def test_the_file_is_private_to_its_owner(tmp_path: Path) -> None:
    path = tmp_path / "wire.jsonl"
    _log(path).request("c1", 1, "u", {})
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600


def test_chunks_are_held_to_a_word_and_flushed_before_the_response(tmp_path: Path) -> None:
    path = tmp_path / "wire.jsonl"
    log = _log(path)
    log.chunk("c1", 1, content="The ans", thinking="")
    log.chunk("c1", 1, content="wer is", thinking="hm")
    log.chunk("c1", 1, content=" 42", thinking=" ok ")
    log.chunk("c1", 1, content="", thinking="")
    log.response("c1", 1, {"done_reason": "stop"}, 1.23456)

    records = _records(path)
    chunks = [r for r in records if r["kind"] == "chunk"]
    assert "".join(str(r.get("content", "")) for r in chunks) == "The answer is 42"
    assert "".join(str(r.get("thinking", "")) for r in chunks) == "hm ok "
    assert records[-1]["kind"] == "response"
    assert records[-1]["elapsed_s"] == 1.235
    assert records[-1]["body"] == {"done_reason": "stop"}
    assert records.index(chunks[-1]) < len(records) - 1


def test_a_failure_flushes_the_held_text_and_names_the_error(tmp_path: Path) -> None:
    path = tmp_path / "wire.jsonl"
    log = _log(path)
    log.chunk("c1", 2, content="half a wor", thinking="")
    log.error("c1", 2, TimeoutError("read timed out"), 9.0)

    *chunks, error = _records(path)
    assert [c["content"] for c in chunks] == ["half a ", "wor"]
    assert (error["kind"], error["error_type"], error["error"]) == (
        "error",
        "TimeoutError",
        "read timed out",
    )
    assert error["attempt"] == 2


def test_an_unwritable_log_is_said_once_and_never_stops_the_work(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocked = tmp_path / "is-a-directory"
    blocked.mkdir()
    log = _log(blocked)
    log.request("c1", 1, "u", {})
    log.response("c1", 1, {}, 0.1)

    captured = capsys.readouterr()
    assert captured.err.count("cannot be written") == 1
    assert str(blocked) in captured.err


def test_the_null_log_does_nothing_and_both_logs_keep_the_contract(tmp_path: Path) -> None:
    null = NullWireLog()
    assert null.request("c", 1, "u", {}) is None
    assert null.chunk("c", 1, content="a", thinking="b") is None
    assert null.response("c", 1, {}, 0.0) is None
    assert null.error("c", 1, ValueError("x"), 0.0) is None
    assert isinstance(null, WireLogInterface)
    assert isinstance(_log(tmp_path / "w.jsonl"), WireLogInterface)
