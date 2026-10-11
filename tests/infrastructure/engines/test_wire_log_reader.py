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
                "load_duration": 120_157_747_041,
                "prompt_eval_duration": 11_228_865_000,
                "done_reason": "stop",
                "message": {"content": "42"},
            },
        }
    )
    assert out.startswith("\n[")
    assert "<<< response c1 attempt 1 - 46.8s - prompt 1234 tokens - output 600 tokens" in out
    assert "20.0 tokens/s - stopped: stop - load 120.2s - prompt eval 11.2s" in out
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


# -- following the wire log and the engine sessions together --------------------------------

import json as _json  # noqa: E402

from vibey.infrastructure.engines.wire_log_reader import (  # noqa: E402
    LineTailer,
    RunEventFormatter,
    follow_live,
    last_session_index,
    session_events,
)


def _append(path: Path, *records: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        for record in records:
            handle.write(_json.dumps(record) + "\n")


def _session(events: Path, run: str = "fb316537aa", item: str | None = "ws") -> dict[str, object]:
    return {
        "v": 1,
        "ts": "2026-10-11T02:35:00+00:00",
        "kind": "session",
        "engine": "gptossloop",
        "run_id": run,
        "events_path": str(events),
        "work_item": item,
    }


def test_the_tailer_reads_whole_lines_once_and_holds_a_half_written_one(tmp_path: Path) -> None:
    path = tmp_path / "f.jsonl"
    tailer = LineTailer(path)
    assert tailer.read_new() == []  # not there yet

    path.write_text('{"a": 1}\n{"b"')
    assert tailer.read_new() == [{"a": 1}]
    assert tailer.read_new() == []  # nothing new, and the half line is not re-read

    with path.open("a") as handle:
        handle.write(': 2}\nnot json\n[1]\n{"c": 3}\n')
    assert tailer.read_new() == [{"b": 2}, {"c": 3}]


def test_a_file_that_shrinks_is_read_again_from_its_start(tmp_path: Path) -> None:
    path = tmp_path / "f.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n')
    tailer = LineTailer(path)
    tailer.read_new()

    path.write_text('{"z": 9}\n')

    assert tailer.read_new() == [{"z": 9}]


def test_the_newest_session_in_a_list_is_found_or_none() -> None:
    records = [{"kind": "request"}, {"kind": "session"}, {"kind": "chunk"}, {"kind": "session"}]

    assert last_session_index(records) == 3
    assert last_session_index([{"kind": "request"}]) is None
    assert last_session_index([]) is None


def test_a_session_whose_runner_has_not_started_writing_has_no_events_yet(tmp_path: Path) -> None:
    session = _session(tmp_path / "missing" / "events.jsonl")

    assert session_events(session) == ([], 0)


def test_a_session_that_has_begun_gives_what_it_wrote_and_where_to_follow_on(
    tmp_path: Path,
) -> None:
    events = tmp_path / "events.jsonl"
    _append(events, {"type": "tool.call", "name": "search"})

    got, offset = session_events(_session(events))

    assert got == [{"type": "tool.call", "name": "search"}] and offset == events.stat().st_size


def test_the_wire_log_and_a_session_are_followed_together(tmp_path: Path) -> None:
    wire, events = tmp_path / "wire.jsonl", tmp_path / "events.jsonl"
    seen: list[tuple[str, str]] = []
    ticks = iter(
        [
            lambda: _append(wire, _session(events)),
            lambda: _append(events, {"type": "tool.call", "name": "find"}),
            lambda: _append(wire, {"kind": "request", "call": "c1", "attempt": 1}),
        ]
    )

    def sleep(_: float) -> None:
        next(ticks)()

    sessions: list[object] = []
    for source, record, session in follow_live(wire, 0, sleep=sleep):
        seen.append((source, str(record.get("kind") or record.get("type"))))
        sessions.append(session["run_id"] if session else None)
        if len(seen) == 3:
            break

    assert seen == [("wire", "session"), ("run", "tool.call"), ("wire", "request")]
    assert sessions == [None, "fb316537aa", None]


def test_a_new_session_takes_over_and_the_one_it_replaces_is_read_to_its_end_first(
    tmp_path: Path,
) -> None:
    wire = tmp_path / "wire.jsonl"
    first, second = tmp_path / "one.jsonl", tmp_path / "two.jsonl"
    _append(wire, _session(first, "run-one"))
    _append(first, {"type": "turn.completed", "turn": 1})
    shown: list[tuple[str, object]] = []
    moves = iter(
        [
            # the first session writes its last events, then the next session begins
            lambda: (
                _append(first, {"type": "failed", "reason": "turn_limit"}),
                _append(wire, _session(second, "run-two")),
                _append(second, {"type": "tool.call", "name": "shell"}),
            ),
        ]
    )

    def sleep(_: float) -> None:
        next(moves)()

    for source, record, session in follow_live(wire, 0, sleep=sleep):
        shown.append((source, session["run_id"] if session else record.get("kind")))
        if record.get("name") == "shell":
            break

    assert shown == [
        ("wire", "session"),
        ("run", "run-one"),
        ("run", "run-one"),  # its last event, drained before the switch
        ("wire", "session"),
        ("run", "run-two"),
    ]


def test_a_session_the_caller_already_showed_is_picked_up_where_it_left_off(
    tmp_path: Path,
) -> None:
    wire, events = tmp_path / "wire.jsonl", tmp_path / "events.jsonl"
    _append(wire, _session(events))
    _append(events, {"type": "tool.call", "n": 1}, {"type": "tool.call", "n": 2})
    shown_so_far = events.stat().st_size
    _append(events, {"type": "tool.call", "n": 3})

    follower = follow_live(
        wire, wire.stat().st_size, session=_session(events), session_offset=shown_so_far
    )
    source, record, _ = next(follower)

    assert (source, record["n"]) == ("run", 3)


def test_with_nothing_new_the_follower_waits_by_sleeping(tmp_path: Path) -> None:
    sleeps: list[float] = []

    def sleep(seconds: float) -> None:
        sleeps.append(seconds)
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt):
        next(follow_live(tmp_path / "never.jsonl", 0, poll_seconds=0.5, sleep=sleep))

    assert sleeps == [0.5]


# -- how an engine session reads ----------------------------------------------------------


def test_a_session_banner_names_the_engine_the_work_item_and_the_run() -> None:
    text = WireFormatter().render(_session(Path("/x/events.jsonl")))

    assert text.endswith("=== gptossloop session - work item ws - run fb316537 ===\n")
    assert "[" in text and "--:--:--" not in text


def test_a_session_with_no_work_item_says_no_work_item() -> None:
    text = WireFormatter().render(_session(Path("/x"), item=None))

    assert "work item" not in text and "gptossloop session - run fb316537" in text


def test_the_model_s_answer_grows_on_one_line_and_any_other_event_closes_it() -> None:
    fmt = RunEventFormatter()

    out = [
        fmt.render({"type": "text_delta", "text": "Hello"}),
        fmt.render({"type": "text_delta", "text": " world"}),
        fmt.render({"type": "tool.call", "turn": 2, "name": "search", "arguments": {"query": "x"}}),
    ]

    assert "".join(out) == '  answer: Hello world\n  turn 2 -> search {"query": "x"}\n'


def test_a_stream_left_open_is_closed_when_output_moves_elsewhere() -> None:
    fmt = RunEventFormatter()

    assert fmt.close() == ""
    fmt.render({"type": "text_delta", "text": "partial"})
    assert fmt.close() == "\n"
    assert fmt.close() == ""

    wire = WireFormatter()
    assert wire.close() == ""
    wire.render({"kind": "chunk", "call": "c", "attempt": 1, "content": "words"})
    assert wire.close() == "\n" and wire.close() == ""


def test_the_models_reasoning_is_indented_under_its_label() -> None:
    fmt = RunEventFormatter()

    assert fmt.render({"type": "reasoning", "turn": 1, "text": " first\nsecond "}) == (
        "  thinking: first\n    second\n"
    )
    assert RunEventFormatter(max_chars=5).render({"type": "reasoning", "text": "abcdefghij"}) == (
        "  thinking: abcde\n"
    )


def test_a_turn_says_how_long_it_took_and_what_it_cost_in_tokens() -> None:
    line = RunEventFormatter().render(
        {
            "type": "turn.completed",
            "turn": 3,
            "duration_ms": 14448,
            "model_ms": 12712,
            "input_tokens": 21890,
            "output_tokens": 30,
        }
    )

    assert line == ("  turn 3 done - 14.4s (model 12.7s) - in 21890 tokens - out 30 tokens\n")
    assert "done - ? (model ?)" in RunEventFormatter().render({"type": "turn.completed"})


@pytest.mark.parametrize(
    ("result", "expected"),
    [
        ({"error": "no such file or directory: tests"}, "error: no such file or directory: tests"),
        ({"exit_code": 0, "output": ""}, "exit 0"),
        ({"exit_code": 1, "output": "x" * 50 + "\n boom"}, "exit 1 - " + "x" * 50 + " boom"),
        ({"count": 33, "matches": ["a"]}, "33 found"),
        ({"files": ["a", "b"]}, "2 found"),
        ({"content": "abcd"}, "4 characters"),
        ({"written": 120}, "wrote 120 characters"),
        ({"odd": 1}, '{"odd": 1}'),
        ("plain text", "plain text"),
    ],
)
def test_each_kind_of_tool_result_is_summarised_not_dumped(result: object, expected: str) -> None:
    line = RunEventFormatter().render({"type": "tool_result", "name": "t", "result": result})

    assert line == f"    <- t: {expected}\n"


def test_a_long_shell_output_shows_its_tail_where_the_failure_is() -> None:
    result = {"exit_code": 1, "output": "start " + "." * 600 + " TypeError: boom"}

    line = RunEventFormatter().render({"type": "tool_result", "name": "shell", "result": result})

    assert line.endswith("TypeError: boom\n") and "start" not in line and len(line) < 400


def test_failure_prompts_and_unknown_events_still_read_plainly() -> None:
    fmt = RunEventFormatter()

    assert fmt.render({"type": "failed", "reason": "turn_limit", "turn": 16, "max_turns": 16}) == (
        "  !!! failed: turn_limit (turn 16 of 16)\n"
    )
    assert fmt.render({"type": "prompt.received", "text": "go on"}) == "  >>> prompt: go on\n"
    assert fmt.render({"type": "weird", "a": 1}) == '  weird {"a": 1}\n'
    assert fmt.render({"event_type": "tool.call", "turn": 1, "name": "x", "arguments": {}}) == (
        "  turn 1 -> x {}\n"
    )
    assert fmt.render({"kind": "k", "v": 2}) == '  k {"kind": "k", "v": 2}\n'
    assert fmt.render({}) == "  event {}\n"


def test_an_argument_limit_follows_max_chars() -> None:
    line = RunEventFormatter(max_chars=20).render(
        {"type": "tool.call", "turn": 1, "name": "x", "arguments": {"q": "y" * 100}}
    )

    assert len(line.split("-> x ")[1].strip()) <= 20
