# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Telling the wire log that an engine session started, so the tail can follow it."""

import json
import os
import stat
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vibey.infrastructure.engines.interfaces import SessionLogInterface
from vibey.infrastructure.engines.session_log import SessionLog
from vibey.infrastructure.engines.wire_log import WIRE_LOG_ENV

NOW = datetime(2026, 10, 11, 2, 35, tzinfo=UTC)


def _log(path: Path | None) -> SessionLog:
    return SessionLog(path, clock=lambda: NOW)


def test_the_session_log_satisfies_its_seam() -> None:
    assert isinstance(_log(None), SessionLogInterface)


def test_a_session_is_one_line_naming_its_events_file_and_the_work_item(tmp_path: Path) -> None:
    path = tmp_path / "state" / "wire.jsonl"
    events = tmp_path / "wt" / ".qwenloop" / "runs" / "abc" / "events.jsonl"

    _log(path).started(engine="gptossloop", run_id="abc", events_path=events, work_item="ws")

    (line,) = path.read_text().splitlines()
    assert json.loads(line) == {
        "v": 1,
        "ts": NOW.isoformat(),
        "kind": "session",
        "engine": "gptossloop",
        "run_id": "abc",
        "events_path": str(events),
        "work_item": "ws",
    }
    assert stat.S_IMODE(os.stat(path).st_mode) == 0o600
    assert stat.S_IMODE(os.stat(path.parent).st_mode) == 0o700


def test_sessions_append_after_whatever_the_wire_log_already_holds(tmp_path: Path) -> None:
    path = tmp_path / "wire.jsonl"
    path.write_text('{"kind": "request"}\n')
    log = _log(path)

    log.started(engine="a", run_id="1", events_path=tmp_path / "1", work_item=None)
    log.started(engine="b", run_id="2", events_path=tmp_path / "2", work_item="x")

    kinds = [json.loads(line)["kind"] for line in path.read_text().splitlines()]
    assert kinds == ["request", "session", "session"]


def test_nothing_is_written_when_the_wire_log_is_not_on(tmp_path: Path) -> None:
    _log(None).started(engine="a", run_id="1", events_path=tmp_path / "e", work_item="ws")

    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(("environ", "expected"), [({}, None), ({WIRE_LOG_ENV: "  "}, None)])
def test_it_is_off_without_a_wire_log_path(environ: dict[str, str], expected: None) -> None:
    assert SessionLog.from_environment(environ)._path is expected


def test_it_is_on_where_the_environment_says_and_expands_the_home_directory() -> None:
    log = SessionLog.from_environment({WIRE_LOG_ENV: "~/state/wire.jsonl"})

    assert log._path == Path("~/state/wire.jsonl").expanduser()


def test_a_write_that_fails_is_said_once_and_never_stops_the_work(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "file"
    blocker.write_text("not a directory")
    log = _log(blocker / "wire.jsonl")

    log.started(engine="a", run_id="1", events_path=tmp_path / "e", work_item=None)
    log.started(engine="a", run_id="2", events_path=tmp_path / "e", work_item=None)

    err = capsys.readouterr().err
    assert err.count("cannot be written") == 1
