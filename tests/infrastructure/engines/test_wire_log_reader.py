# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Reading the wire log back: following a growing file, and the text shown for each record."""

import json
from pathlib import Path

import pytest

from vibey.infrastructure.engines.wire_log_reader import (
    WireFormatter,
    follow_records,
    parse_line,
    snapshot,
    start_of_latest_call,
)

TS = "2026-10-10T22:04:11+00:00"


def _line(**fields: object) -> str:
    return json.dumps({"ts": TS, **fields}) + "\n"


def test_a_line_that_is_not_a_json_object_is_skipped_not_fatal() -> None:
    assert parse_line(b'{"kind": "chunk"}') == {"kind": "chunk"}
    assert parse_line("not json") is None
    assert parse_line(b"[1, 2]") is None


def test_a_snapshot_stops_at_the_last_whole_line(tmp_path: Path) -> None:
    path = tmp_path / "w.jsonl"
    whole = _line(kind="request", call="a", attempt=1) + "garbage\n"
    path.write_bytes(whole.encode() + b'{"kind": "chu')
    records, offset = snapshot(path)
    assert [r["kind"] for r in records] == ["request"]
    assert offset == len(whole.encode())


def test_the_latest_call_starts_at_its_first_attempt() -> None:
    records = [
        {"kind": "request", "call": "a", "attempt": 1},
        {"kind": "response", "call": "a", "attempt": 1},
        {"kind": "request", "call": "b", "attempt": 1},
        {"kind": "request", "call": "b", "attempt": 2},
        {"kind": "chunk", "call": "b", "attempt": 2},
    ]
    assert start_of_latest_call(records) == 2
    assert start_of_latest_call([{"kind": "chunk"}]) == 0
    assert start_of_latest_call([]) == 0


class _Done(Exception):
    pass


def test_following_yields_what_is_appended_and_waits_when_idle(tmp_path: Path) -> None:
    path = tmp_path / "w.jsonl"
    path.write_text(_line(kind="request", call="a", attempt=1))
    _, offset = snapshot(path)
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        if len(sleeps) == 1:
            with path.open("a") as handle:
                handle.write(_line(kind="chunk", call="a", attempt=1, content="hi "))
                handle.write('{"kind": "resp')
        elif len(sleeps) == 2:
            with path.open("a") as handle:
                handle.write('onse", "call": "a", "attempt": 1}\n')
                handle.write("garbage\n")
        else:
            raise _Done

    seen: list[str] = []
    with pytest.raises(_Done):
        for record in follow_records(path, offset, poll_seconds=0.5, sleep=sleep):
            seen.append(str(record["kind"]))
    assert seen == ["chunk", "response"]
    assert sleeps == [0.5, 0.5, 0.5]


def test_following_waits_for_a_file_that_does_not_exist_yet(tmp_path: Path) -> None:
    path = tmp_path / "later.jsonl"
    calls = 0

    def sleep(_: float) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            path.write_text(_line(kind="request", call="a", attempt=1))
        elif calls > 2:
            raise _Done

    seen = []
    with pytest.raises(_Done):
        for record in follow_records(path, 0, sleep=sleep):
            seen.append(record["kind"])
    assert seen == ["request"]


def test_a_file_that_shrinks_is_followed_again_from_its_start(tmp_path: Path) -> None:
    path = tmp_path / "w.jsonl"
    path.write_text(_line(kind="request", call="old", attempt=1) * 3)
    _, offset = snapshot(path)
    calls = 0

    def sleep(_: float) -> None:
        nonlocal calls
        calls += 1
        if calls == 1:
            path.write_text(_line(kind="request", call="new", attempt=1))
        else:
            raise _Done

    seen = []
    with pytest.raises(_Done):
        for record in follow_records(path, offset, sleep=sleep):
            seen.append(record["call"])
    assert seen == ["new"]


def _request(**payload: object) -> dict[str, object]:
    return {
        "ts": TS,
        "kind": "request",
        "call": "c1",
        "attempt": 1,
        "payload": {
            "model": "gpt-oss:20b",
            "options": {"num_ctx": 8192, "num_predict": 2048},
            "format": "json",
            "messages": [
                {"role": "system", "content": "be terse"},
                {"role": "user", "content": "line one\nline two"},
            ],
            **payload,
        },
    }


def test_a_request_shows_the_model_the_limits_and_every_message() -> None:
    text = WireFormatter().render(_request())
    assert "request c1 attempt 1 - gpt-oss:20b - num_ctx 8192 - num_predict 2048" in text
    assert "answer as json" in text
    assert "  system:\n    be terse\n" in text
    assert "  user:\n    line one\n    line two\n" in text


@pytest.mark.parametrize(("form", "shape"), [({"type": "object"}, "schema"), (None, "free text")])
def test_the_answer_shape_is_named(form: object, shape: str) -> None:
    assert f"answer as {shape}" in WireFormatter().render(_request(format=form))


def test_a_request_with_no_payload_still_renders() -> None:
    text = WireFormatter().render({"ts": TS, "kind": "request", "call": "c", "attempt": 1})
    assert "request c attempt 1" in text


def test_long_messages_are_cut_on_request() -> None:
    text = WireFormatter(max_chars=5).render(_request())
    assert "    line " in text
    assert "... [12 more characters]" in text
    assert "line two" not in text


def test_a_message_that_is_not_an_object_is_ignored() -> None:
    assert "request" in WireFormatter().render(_request(messages=["odd", 3]))
    assert "request" in WireFormatter().render(_request(messages="odd"))


def test_streamed_text_grows_in_place_and_labels_each_stream() -> None:
    formatter = WireFormatter()
    out = formatter.render({"kind": "chunk", "call": "c1", "attempt": 1, "thinking": "hmm "})
    out += formatter.render({"kind": "chunk", "call": "c1", "attempt": 1, "thinking": "ok "})
    out += formatter.render({"kind": "chunk", "call": "c1", "attempt": 1, "content": "42 "})
    out += formatter.render({"kind": "chunk", "call": "c1", "attempt": 1, "content": "now"})
    out += formatter.render({"kind": "chunk", "call": "c1", "attempt": 1, "content": ""})
    assert out == "  thinking: hmm ok \n  answer: 42 now"


def test_a_chunk_with_both_streams_labels_both() -> None:
    out = WireFormatter().render(
        {"kind": "chunk", "call": "c", "attempt": 1, "thinking": "a ", "content": "b "}
    )
    assert out == "  thinking: a \n  answer: b "


def test_a_response_closes_the_stream_and_reports_speed_and_counts() -> None:
    formatter = WireFormatter()
    formatter.render({"kind": "chunk", "call": "c1", "attempt": 1, "content": "42"})
    out = formatter.render(
        {
            "ts": TS,
            "kind": "response",
            "call": "c1",
            "attempt": 1,
            "elapsed_s": 46.84,
            "body": {
                "prompt_eval_count": 1234,
                "eval_count": 600,
                "eval_duration": 30_000_000_000,
                "done_reason": "stop",
                "message": {"content": "42"},
            },
        }
    )
    assert out.startswith("\n[")
    assert "<<< response c1 attempt 1 - 46.8s - prompt 1234 tokens - output 600 tokens" in out
    assert "20.0 tokens/s - stopped: stop" in out
    assert "answer:" not in out


def test_a_response_that_was_never_streamed_shows_its_answer() -> None:
    out = WireFormatter().render(
        {
            "ts": TS,
            "kind": "response",
            "call": "c",
            "attempt": 1,
            "body": {"message": {"content": "hi"}},
        }
    )
    assert "  answer:\n    hi\n" in out
    assert "0.0s" in out
    assert "tokens/s" not in out


def test_a_response_with_no_body_still_renders() -> None:
    out = WireFormatter().render(
        {"ts": "nonsense", "kind": "response", "call": "c", "attempt": "x"}
    )
    assert out.startswith("[--:--:--] <<< response c attempt x - 0.0s")


def test_an_error_names_the_type_and_the_time_spent() -> None:
    out = WireFormatter().render(
        {
            "ts": TS,
            "kind": "error",
            "call": "c1",
            "attempt": 2,
            "elapsed_s": 900.0,
            "error_type": "TimeoutError",
            "error": "timed out",
        }
    )
    assert "!!! error c1 attempt 2 - 900.0s - TimeoutError: timed out" in out


def test_a_record_of_a_kind_it_does_not_know_is_shown_as_it_is() -> None:
    assert WireFormatter().render({"kind": "future", "x": 1}) == '{"kind": "future", "x": 1}\n'
