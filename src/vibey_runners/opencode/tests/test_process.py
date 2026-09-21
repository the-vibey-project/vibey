# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from types import SimpleNamespace

import pytest

from opencodeloop.infrastructure.opencode_process import OpenCodeProcess


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_doctor_rejects_missing_binary(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: None)
    assert OpenCodeProcess().doctor() == (False, "'opencode' was not found on PATH")


def test_doctor_rejects_probe_exception(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")

    def fail(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("permission denied")

    monkeypatch.setattr("subprocess.run", fail)
    ready, detail = OpenCodeProcess().doctor()
    assert not ready
    assert "permission denied" in detail


def test_doctor_rejects_version_failure_and_missing_json_flag(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: _completed(1))
    assert OpenCodeProcess().doctor() == (False, "OpenCode --version failed")

    results = iter([_completed(0, "1.2.3\n"), _completed(0, "run --help\n")])
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: next(results))
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode run does not advertise required flags: --format, --standalone, --auto, --dir, --session",
    )


def test_doctor_accepts_documented_json_run_surface(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    results = iter(
        [
            _completed(0, "opencode 1.2.3\n"),
            _completed(0, "--format json --standalone --auto --dir --session\n"),
        ]
    )
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: next(results))
    assert OpenCodeProcess().doctor() == (True, "opencode 1.2.3; run --format json available")


class _FakeProcess:
    def __init__(self, returncode: int, stdout: str, stderr: str = "") -> None:
        self.returncode = returncode
        self._stdout = stdout
        self._stderr = stderr

    def communicate(self) -> tuple[str, str]:
        return self._stdout, self._stderr


def test_execute_normalizes_json_and_plain_text_success(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    process = _FakeProcess(
        0,
        '{"type":"session.created","sessionID":"s-1"}\n'
        '{"type":"step_start"}\n'
        '{"type":"tool_result"}\n'
        '{"type":"step_finish"}\n'
        '{"type":"message"}\n'
        "not-json\n"
        "\n"
        "[]\n",
    )
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: process)
    events: list[dict[str, object]] = []
    result = OpenCodeProcess().execute(
        prompt="plan", cwd=tmp_path, session_id=None, emit=events.append
    )
    assert result.succeeded
    assert result.session_id == "s-1"
    assert [event["event_type"] for event in events] == [
        "run.started",
        "turn.starting",
        "tool_result",
        "turn.completed",
        "text_delta",
        "text_delta",
        "text_delta",
        "finished",
    ]


def test_execute_reports_failure_and_uses_existing_session(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    process = _FakeProcess(3, '{"type":"error"}\n', "bad provider")
    seen: list[list[str]] = []

    def popen(args, **kwargs):  # type: ignore[no-untyped-def]
        seen.append(args)
        return process

    monkeypatch.setattr("subprocess.Popen", popen)
    events: list[dict[str, object]] = []
    result = OpenCodeProcess().execute(
        prompt="plan", cwd=tmp_path, session_id="s-2", emit=events.append
    )
    assert result.status.value == "failed"
    assert result.returncode == 3
    assert result.detail == "bad provider"
    assert seen[0][1:9] == [
        "run",
        "--format",
        "json",
        "--standalone",
        "--auto",
        "--dir",
        str(tmp_path),
        "--session",
    ]
    assert seen[0][-3:] == ["--session", "s-2", "plan"]
    assert events[-1]["event_type"] == "failed"


def test_execute_rejects_missing_binary_and_normalizer_shapes(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(OSError, match="not found"):
        OpenCodeProcess().execute(prompt="plan", cwd=tmp_path, session_id=None, emit=lambda _: None)

    normalize = OpenCodeProcess._normalize
    assert normalize('{"type":"message_start"}')["event_type"] == "turn.starting"
    assert normalize('{"type":"message_finish"}')["event_type"] == "turn.completed"
    assert normalize('{"type":"tool_use"}')["event_type"] == "tool_result"
    assert normalize('{"type":"session.error"}')["event_type"] == "failed"
    assert normalize('{"type":"session_started"}')["event_type"] == "run.started"
    assert normalize("plain")["event_type"] == "text_delta"
    assert normalize("null")["event_type"] == "text_delta"
    assert OpenCodeProcess._session_id({"raw": {"sessionId": "s"}}) == "s"
    assert OpenCodeProcess._session_id({"raw": {"session_id": "s"}}) == "s"
    assert OpenCodeProcess._session_id({"raw": {}}) is None
    assert OpenCodeProcess._session_id({}) is None
