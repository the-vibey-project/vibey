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
    def interrupted(path: Path, offset: int) -> Iterator[dict[str, object]]:
        assert offset == 0
        raise KeyboardInterrupt
        yield {}

    monkeypatch.setattr("vibey.cli.llm.follow_records", interrupted)
    result = runner.invoke(app, ["llm", "tail", "--file", str(tmp_path / "later.jsonl")])
    assert result.exit_code == 0
    assert "waiting for" in result.output


def test_tail_follows_new_records_after_the_snapshot_until_interrupted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _two_calls(tmp_path / "wire.jsonl")
    offsets: list[int] = []

    def later(file: Path, offset: int) -> Iterator[dict[str, object]]:
        offsets.append(offset)
        yield {"kind": "chunk", "call": "newb222", "attempt": 1, "content": "and more"}
        raise KeyboardInterrupt

    monkeypatch.setattr("vibey.cli.llm.follow_records", later)
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
    monkeypatch.setattr("vibey.cli.llm.follow_records", lambda file, offset: iter(()))
    result = runner.invoke(app, ["llm", "tail", "--file", str(path)])
    assert result.exit_code == 0
