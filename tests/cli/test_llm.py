# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`vibey llm tail`, and `-vvv` switching the wire log on."""

import json
import os
from collections.abc import Iterator
from pathlib import Path

import pytest
from typer.testing import CliRunner

from vibey.cli.llm import wire_log_path
from vibey.cli.main import app
from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV, default_wire_log_path

runner = CliRunner()
TS = "2026-10-10T22:04:11+00:00"


def _write(path: Path, *records: dict[str, object]) -> Path:
    path.write_text("".join(json.dumps({"ts": TS, **r}) + "\n" for r in records))
    return path


def _two_calls(path: Path) -> Path:
    return _write(
        path,
        {"kind": "request", "call": "olda111", "attempt": 1, "payload": {"model": "m"}},
        {"kind": "response", "call": "olda111", "attempt": 1, "body": {}},
        {"kind": "request", "call": "newb222", "attempt": 1, "payload": {"model": "m"}},
        {"kind": "chunk", "call": "newb222", "attempt": 1, "content": "the answer "},
        {"kind": "response", "call": "newb222", "attempt": 1, "elapsed_s": 2.0, "body": {}},
    )


def test_tail_shows_the_latest_call_and_stops_when_not_following(tmp_path: Path) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")
    result = runner.invoke(app, ["llm", "tail", "--file", str(path), "--no-follow"])
    assert result.exit_code == 0, result.output
    assert "request newb222" in result.output
    assert "answer: the answer" in result.output
    assert "olda111" not in result.output


def test_tail_all_starts_from_the_beginning(tmp_path: Path) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")
    result = runner.invoke(app, ["llm", "tail", "--file", str(path), "--no-follow", "--all"])
    assert "request olda111" in result.output and "request newb222" in result.output


def test_tail_raw_prints_the_lines_as_written(tmp_path: Path) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")
    result = runner.invoke(
        app, ["llm", "tail", "--file", str(path), "--no-follow", "--raw", "--max-chars", "5"]
    )
    kinds = [json.loads(line)["kind"] for line in result.output.splitlines()]
    assert kinds == ["request", "chunk", "response"]


def test_tail_without_a_log_says_how_to_make_one_and_fails_when_not_following(
    tmp_path: Path,
) -> None:
    result = runner.invoke(
        app, ["llm", "tail", "--file", str(tmp_path / "none.jsonl"), "--no-follow"]
    )
    assert result.exit_code == 1
    assert "no wire log at" in result.output and "-vvv" in result.output


def test_tail_following_a_log_that_does_not_exist_yet_waits_for_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def interrupted(
        path: Path, offset: int, **_: object
    ) -> Iterator[tuple[str, dict[str, object], None]]:
        assert offset == 0
        raise KeyboardInterrupt
        yield "wire", {}, None

    monkeypatch.setattr("vibey.cli.llm.follow_live", interrupted)
    result = runner.invoke(app, ["llm", "tail", "--file", str(tmp_path / "later.jsonl")])
    assert result.exit_code == 0
    assert "waiting for" in result.output


def test_tail_follows_new_records_after_the_snapshot_until_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")
    offsets: list[int] = []

    def later(
        file: Path, offset: int, **_: object
    ) -> Iterator[tuple[str, dict[str, object], None]]:
        offsets.append(offset)
        yield (
            "wire",
            {"kind": "chunk", "call": "newb222", "attempt": 1, "content": "and more"},
            None,
        )
        raise KeyboardInterrupt

    monkeypatch.setattr("vibey.cli.llm.follow_live", later)
    result = runner.invoke(app, ["llm", "tail", "--file", str(path)])
    assert result.exit_code == 0
    assert offsets == [path.stat().st_size]
    assert "the answer" in result.output and "and more" in result.output


def test_the_log_is_found_from_the_flag_then_the_environment_then_the_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(WIRE_LOG_ENV, "x")
    monkeypatch.delenv(WIRE_LOG_ENV)
    assert wire_log_path(None) == default_wire_log_path()
    monkeypatch.setenv(WIRE_LOG_ENV, str(tmp_path / "env.jsonl"))
    assert wire_log_path(None) == tmp_path / "env.jsonl"
    assert wire_log_path(tmp_path / "flag.jsonl") == tmp_path / "flag.jsonl"
    monkeypatch.setenv(WIRE_LOG_ENV, "  ")
    assert wire_log_path(None) == default_wire_log_path()


def test_vvv_switches_the_wire_log_on_and_says_where_it_is(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(WIRE_LOG_ENV, "x")
    monkeypatch.delenv(WIRE_LOG_ENV)
    result = runner.invoke(app, ["-vvv", "sabbath"])
    assert os.environ[WIRE_LOG_ENV] == str(default_wire_log_path())
    assert "vibey llm tail" in result.output
    assert str(default_wire_log_path()) in result.output


def test_a_log_the_operator_named_is_never_overridden_and_vv_does_not_switch_it_on(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    chosen = str(tmp_path / "mine.jsonl")
    monkeypatch.setenv(WIRE_LOG_ENV, chosen)
    result = runner.invoke(app, ["-vvv", "sabbath"])
    assert os.environ[WIRE_LOG_ENV] == chosen
    assert "wire log" not in result.output

    monkeypatch.setenv(WIRE_LOG_ENV, "x")
    monkeypatch.delenv(WIRE_LOG_ENV)
    runner.invoke(app, ["-vv", "sabbath"])
    assert WIRE_LOG_ENV not in os.environ


def test_tail_ends_cleanly_if_the_follower_does(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")
    monkeypatch.setattr("vibey.cli.llm.follow_live", lambda file, offset, **_: iter(()))
    result = runner.invoke(app, ["llm", "tail", "--file", str(path)])
    assert result.exit_code == 0


# -- BUILD and REVIEW: the engine sessions the wire log points at ---------------------------


def _session_events(path: Path, *events: dict[str, object]) -> Path:
    path.write_text("".join(json.dumps(event) + "\n" for event in events))
    return path


def _session_record(events: Path, run: str = "fb316537aa", item: str = "ws") -> dict[str, object]:
    return {
        "kind": "session",
        "engine": "gptossloop",
        "run_id": run,
        "events_path": str(events),
        "work_item": item,
    }


TURN = {
    "type": "turn.completed",
    "turn": 1,
    "duration_ms": 3100,
    "model_ms": 2900,
    "input_tokens": 1346,
    "output_tokens": 58,
}


def test_tail_shows_the_build_session_that_follows_the_latest_call(tmp_path: Path) -> None:
    events = _session_events(
        tmp_path / "events.jsonl",
        {"type": "tool.call", "turn": 1, "name": "search", "arguments": {"query": "ministry"}},
        {"type": "tool_result", "name": "search", "result": {"count": 3, "matches": []}},
        {"type": "text_delta", "text": "Looking now."},
        TURN,
    )
    path = _write(
        tmp_path / "wire.jsonl",
        {"kind": "request", "call": "dec1", "attempt": 1, "payload": {"model": "m"}},
        _session_record(events),
    )

    result = runner.invoke(app, ["llm", "tail", "--file", str(path), "--no-follow"])

    assert result.exit_code == 0, result.output
    assert "=== gptossloop session - work item ws - run fb316537 ===" in result.output
    assert 'turn 1 -> search {"query": "ministry"}' in result.output
    assert "<- search: 3 found" in result.output
    assert "answer: Looking now." in result.output
    assert "turn 1 done - 3.1s (model 2.9s) - in 1346 tokens - out 58 tokens" in result.output
    assert "request dec1" not in result.output  # the session is newer than that call


def test_a_call_newer_than_the_last_session_is_what_the_tail_starts_at(tmp_path: Path) -> None:
    events = _session_events(tmp_path / "events.jsonl", TURN)
    path = _write(
        tmp_path / "wire.jsonl",
        _session_record(events),
        {"kind": "request", "call": "later9", "attempt": 1, "payload": {"model": "m"}},
    )

    result = runner.invoke(app, ["llm", "tail", "--file", str(path), "--no-follow"])

    assert "request later9" in result.output and "session" not in result.output


def test_all_shows_every_call_and_every_session_in_order(tmp_path: Path) -> None:
    one = _session_events(tmp_path / "one.jsonl", {"type": "tool.call", "turn": 1, "name": "a"})
    two = _session_events(tmp_path / "two.jsonl", {"type": "tool.call", "turn": 1, "name": "b"})
    path = _write(
        tmp_path / "wire.jsonl",
        {"kind": "request", "call": "first1", "attempt": 1, "payload": {"model": "m"}},
        _session_record(one, "run-one", "ws"),
        _session_record(two, "run-two", "pages"),
    )

    result = runner.invoke(app, ["llm", "tail", "--file", str(path), "--no-follow", "--all"])

    order = [
        result.output.index(marker)
        for marker in ("request first1", "run run-one", "-> a", "run run-two", "-> b")
    ]
    assert order == sorted(order)


def test_a_session_whose_runner_has_not_written_yet_shows_its_banner_and_is_followed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    record = _session_record(tmp_path / "not-yet" / "events.jsonl", "soon1234", "docs")
    path = _write(tmp_path / "wire.jsonl", record)
    got: dict[str, object] = {}

    def follow(file: Path, offset: int, *, session: object, session_offset: int, **_: object):  # type: ignore[no-untyped-def]
        got.update(offset=offset, session=session, session_offset=session_offset)
        raise KeyboardInterrupt
        yield

    monkeypatch.setattr("vibey.cli.llm.follow_live", follow)

    result = runner.invoke(app, ["llm", "tail", "--file", str(path)])

    assert "work item docs - run soon1234" in result.output
    assert got["session"] is not None and got["session_offset"] == 0
    assert got["offset"] == path.stat().st_size


def test_following_carries_on_from_the_end_of_what_the_session_has_already_shown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    events = _session_events(tmp_path / "events.jsonl", TURN)
    path = _write(tmp_path / "wire.jsonl", _session_record(events))
    got: dict[str, object] = {}

    def follow(file: Path, offset: int, *, session: object, session_offset: int, **_: object):  # type: ignore[no-untyped-def]
        got.update(session=session, session_offset=session_offset)
        yield "run", {"type": "tool.call", "turn": 2, "name": "shell", "arguments": {}}, session
        raise KeyboardInterrupt

    monkeypatch.setattr("vibey.cli.llm.follow_live", follow)

    result = runner.invoke(app, ["llm", "tail", "--file", str(path)])

    assert got["session_offset"] == events.stat().st_size
    assert "turn 2 -> shell" in result.output


def test_output_that_moves_between_streams_ends_the_open_answer_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")

    def follow(file: Path, offset: int, **_: object):  # type: ignore[no-untyped-def]
        yield (
            "wire",
            {"kind": "chunk", "call": "newb222", "attempt": 1, "content": "streaming "},
            None,
        )
        yield "run", {"type": "tool.call", "turn": 1, "name": "find", "arguments": {}}, None
        yield "run", {"type": "text_delta", "text": "engine says"}, None
        yield "wire", {"kind": "request", "call": "next3", "attempt": 1, "payload": {}}, None
        raise KeyboardInterrupt

    monkeypatch.setattr("vibey.cli.llm.follow_live", follow)

    result = runner.invoke(app, ["llm", "tail", "--file", str(path)])

    assert "streaming \n  turn 1 -> find {}" in result.output
    assert "answer: engine says\n[" in result.output and "request next3" in result.output


def test_raw_prints_an_engine_event_as_it_was_written(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")

    def follow(file: Path, offset: int, **_: object):  # type: ignore[no-untyped-def]
        yield "run", {"type": "tool.call", "name": "find"}, None
        raise KeyboardInterrupt

    monkeypatch.setattr("vibey.cli.llm.follow_live", follow)

    result = runner.invoke(app, ["llm", "tail", "--file", str(path), "--raw"])

    assert '{"type": "tool.call", "name": "find"}' in result.output
