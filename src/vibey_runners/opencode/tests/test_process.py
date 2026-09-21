# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from types import SimpleNamespace

import pytest

from opencodeloop.infrastructure.opencode_process import OpenCodeProcess

_HELP_WITH_FLAGS = "--format json --auto --dir --session\n"
_AUTH_WITH_CREDENTIAL = '{"openai":{"type":"api","key":"redacted"}}\n'
_AUTH_WITHOUT_CREDENTIAL = "{}\n"


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _doctor_runs(*results: SimpleNamespace) -> object:
    iterator = iter(results)
    return lambda *args, **kwargs: next(iterator)


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


def test_doctor_rejects_version_failure(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: _completed(1))
    assert OpenCodeProcess().doctor() == (False, "OpenCode --version failed")


def test_doctor_never_requires_a_flag_the_real_cli_lacks(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(_completed(0, "1.2.3\n"), _completed(0, "run --help\n")),
    )
    # `--standalone` was never a real OpenCode option; the missing set is only
    # the flags the real CLI has and this adapter needs.
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode run does not advertise required flags: --format, --auto, --dir, --session",
    )


def test_doctor_rejects_a_run_help_that_exits_nonzero(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(_completed(0, "1.2.3\n"), _completed(2, _HELP_WITH_FLAGS)),
    )
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode run does not advertise required flags: --format json",
    )


def test_doctor_names_a_missing_json_format_when_flags_are_present(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(_completed(0, "1.2.3\n"), _completed(0, "--format --auto --dir --session\n")),
    )
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode run does not advertise required flags: --format json",
    )


def test_doctor_rejects_an_auth_probe_that_itself_fails(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(
            _completed(0, "1.2.3\n"),
            _completed(0, _HELP_WITH_FLAGS),
            _completed(1, _AUTH_WITH_CREDENTIAL),
        ),
    )
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode has no configured provider; run `opencode auth login`",
    )


def test_doctor_rejects_an_auth_probe_exception(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    results = iter([_completed(0, "1.2.3\n"), _completed(0, _HELP_WITH_FLAGS)])

    def run(*args, **kwargs):  # type: ignore[no-untyped-def]
        try:
            return next(results)
        except StopIteration:
            raise OSError("auth exploded") from None

    monkeypatch.setattr("subprocess.run", run)
    ready, detail = OpenCodeProcess().doctor()
    assert not ready
    assert "auth exploded" in detail


def test_doctor_requires_a_configured_provider(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(
            _completed(0, "1.2.3\n"),
            _completed(0, _HELP_WITH_FLAGS),
            _completed(0, _AUTH_WITHOUT_CREDENTIAL),
        ),
    )
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode has no configured provider; run `opencode auth login`",
    )


def test_doctor_accepts_an_authenticated_json_run_surface(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(
            _completed(0, "opencode 1.2.3\n"),
            _completed(0, _HELP_WITH_FLAGS),
            _completed(0, _AUTH_WITH_CREDENTIAL),
        ),
    )
    assert OpenCodeProcess().doctor() == (True, "opencode 1.2.3; run --format json available")


def test_doctor_reports_unknown_version_without_failing(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(
            _completed(0, ""),
            _completed(0, _HELP_WITH_FLAGS),
            _completed(0, _AUTH_WITH_CREDENTIAL),
        ),
    )
    assert OpenCodeProcess().doctor() == (True, "unknown; run --format json available")


class _FakeStream:
    def __init__(self, text: str) -> None:
        self._lines = text.splitlines(keepends=True)

    def __iter__(self):  # type: ignore[no-untyped-def]
        return iter(self._lines)


class _FakeProcess:
    def __init__(self, returncode: int, stdout: str | None, stderr: str | None = "") -> None:
        self.returncode = returncode
        self.stdout = _FakeStream(stdout) if stdout is not None else None
        self.stderr = _FakeStream(stderr) if stderr is not None else None

    def wait(self) -> int:
        return self.returncode


def test_execute_streams_normalized_events_before_exit(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
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
    # The provider session boundary is passed through unmapped, never as
    # `run.started`: only the application seeds a run, exactly once.
    assert [event["event_type"] for event in events] == [
        "session.created",
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
    # No fabricated `--standalone`, and `--dir`/`--session` are real flags.
    assert seen[0] == [
        "/bin/opencode",
        "run",
        "--format",
        "json",
        "--auto",
        "--dir",
        str(tmp_path),
        "--session",
        "s-2",
        "plan",
    ]
    assert events[-1]["event_type"] == "failed"


def test_execute_reports_an_exit_code_when_stderr_is_empty(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: _FakeProcess(2, ""))
    events: list[dict[str, object]] = []
    result = OpenCodeProcess().execute(
        prompt="plan", cwd=tmp_path, session_id=None, emit=events.append
    )
    assert result.detail == "OpenCode exited with 2"
    assert events[-1]["detail"] == "OpenCode exited with 2"


def test_execute_survives_missing_streams(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: _FakeProcess(0, None, None))
    events: list[dict[str, object]] = []
    result = OpenCodeProcess().execute(
        prompt="plan", cwd=tmp_path, session_id=None, emit=events.append
    )
    assert result.succeeded
    assert events == [{"event_type": "finished", "success": True, "session_id": None}]


def test_execute_rejects_missing_binary(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: None)
    with pytest.raises(OSError, match="not found"):
        OpenCodeProcess().execute(prompt="plan", cwd=tmp_path, session_id=None, emit=lambda _: None)


def test_execute_surfaces_a_capacity_rejection_event(monkeypatch, tmp_path) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    process = _FakeProcess(
        1,
        '{"type":"error","error":{"name":"APIError",'
        '"data":{"statusCode":429,"message":"rate limited"}}}\n',
    )
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: process)
    events: list[dict[str, object]] = []
    OpenCodeProcess().execute(prompt="plan", cwd=tmp_path, session_id=None, emit=events.append)
    assert events[0]["event_type"] == "capacity.rejected"
    assert events[0]["capacity_state"] == "window_exhausted"
    assert events[0]["detail"] == "rate limited"
    assert events[-1]["event_type"] == "failed"


def test_normalize_maps_every_real_event_shape() -> None:
    normalize = OpenCodeProcess._normalize
    assert normalize('{"type":"message_start"}')["event_type"] == "turn.starting"
    assert normalize('{"type":"message_finish"}')["event_type"] == "turn.completed"
    assert normalize('{"type":"turn_start"}')["event_type"] == "turn.starting"
    assert normalize('{"type":"turn_finish"}')["event_type"] == "turn.completed"
    assert normalize('{"type":"tool_use"}')["event_type"] == "tool_result"
    assert normalize('{"type":"tool_call"}')["event_type"] == "tool_result"
    assert normalize('{"type":"session.error"}')["event_type"] == "failed"
    assert normalize('{"type":"session_started"}')["event_type"] == "session_started"
    assert normalize('{"type":"text","part":{"text":"hi"}}')["event_type"] == "text_delta"
    assert normalize("plain")["event_type"] == "text_delta"
    assert normalize("null")["event_type"] == "text_delta"


def test_normalize_falls_back_to_the_error_name_when_no_message_exists() -> None:
    event = OpenCodeProcess._normalize(
        '{"type":"error","error":{"name":"APIError","data":{"statusCode":402}}}'
    )
    assert event["event_type"] == "capacity.rejected"
    assert event["capacity_state"] == "credits_exhausted"
    assert event["detail"] == "APIError"


@pytest.mark.parametrize(
    ("status_code", "capacity_state"),
    [(429, "window_exhausted"), (402, "credits_exhausted"), (401, "auth_failed")],
)
def test_normalize_maps_official_api_error_statuses(status_code: int, capacity_state: str) -> None:
    event = OpenCodeProcess._normalize(
        json.dumps(
            {
                "type": "error",
                "error": {
                    "name": "APIError",
                    "data": {"statusCode": status_code, "message": "provider response"},
                },
            }
        )
    )
    assert event["event_type"] == "capacity.rejected"
    assert event["capacity_state"] == capacity_state


def test_normalize_leaves_non_capacity_api_errors_as_failures() -> None:
    event = OpenCodeProcess._normalize(
        '{"type":"error","error":{"name":"APIError",'
        '"data":{"statusCode":500,"message":"server error"}}}'
    )
    assert event["event_type"] == "failed"


def test_doctor_rejects_non_json_auth_output(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(
            _completed(0, "1.2.3\n"),
            _completed(0, _HELP_WITH_FLAGS),
            _completed(0, "credentials exist\n"),
        ),
    )
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode has no configured provider; run `opencode auth login`",
    )


def test_doctor_rejects_an_unexpected_json_auth_shape(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("shutil.which", lambda _: "/bin/opencode")
    monkeypatch.setattr(
        "subprocess.run",
        _doctor_runs(
            _completed(0, "1.2.3\n"),
            _completed(0, _HELP_WITH_FLAGS),
            _completed(0, '"credential"\n'),
        ),
    )
    assert OpenCodeProcess().doctor() == (
        False,
        "OpenCode has no configured provider; run `opencode auth login`",
    )


def test_normalize_leaves_unrecognized_provider_errors_as_failures() -> None:
    event = OpenCodeProcess._normalize('{"type":"error","error":{"name":"SomethingElse"}}')
    assert event["event_type"] == "failed"
    assert "capacity_state" not in event


def test_normalize_handles_an_error_event_without_the_provider_envelope() -> None:
    event = OpenCodeProcess._normalize('{"type":"error"}')
    assert event == {"event_type": "failed", "raw": {"type": "error"}}


def test_error_helpers_cover_non_mapping_inputs() -> None:
    assert OpenCodeProcess._error_detail({"error": "nope"}) == ""
    assert OpenCodeProcess._error_detail({"error": {"name": ""}}) == ""
    assert OpenCodeProcess._error_detail({"error": {"data": {"message": ""}, "name": "N"}}) == "N"
    assert OpenCodeProcess._capacity_state({"error": "nope"}) is None
    assert OpenCodeProcess._capacity_state({"error": {"name": 7}}) is None


def test_session_id_reads_every_documented_field() -> None:
    assert OpenCodeProcess._session_id({"raw": {"sessionID": "s"}}) == "s"
    assert OpenCodeProcess._session_id({"raw": {"sessionId": "s"}}) == "s"
    assert OpenCodeProcess._session_id({"raw": {"session_id": "s"}}) == "s"
    assert OpenCodeProcess._session_id({"raw": {"sessionID": ""}}) is None
    assert OpenCodeProcess._session_id({"raw": {}}) is None
    assert OpenCodeProcess._session_id({}) is None
    assert OpenCodeProcess._session_id({"raw": "not-a-mapping"}) is None


def test_clean_strips_ansi_so_help_checks_see_plain_flags() -> None:
    assert OpenCodeProcess._clean("\x1b[1m--format\x1b[0m") == "--format"
