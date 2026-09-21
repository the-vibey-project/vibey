# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

from opencodeloop.application.runner import OpencodeRunner
from opencodeloop.domain.model import RunResult, RunStatus


class _Process:
    def __init__(self, result: RunResult | None = None, error: OSError | None = None) -> None:
        self.result = result
        self.error = error

    def doctor(self) -> tuple[bool, str]:
        return True, "ready"

    def execute(self, *, prompt, cwd, session_id, emit):  # type: ignore[no-untyped-def]
        if self.error is not None:
            raise self.error
        emit({"event_type": "turn.completed"})
        assert prompt == "prompt"
        assert cwd == Path("/work")
        assert session_id is None
        return self.result or RunResult(RunStatus.FINISHED, 0)


class _Store:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def begin(self, run_dir, run_id, cwd, session_id) -> None:  # type: ignore[no-untyped-def]
        self.calls.append(("begin", run_dir))

    def append_event(self, run_dir, event) -> None:  # type: ignore[no-untyped-def]
        self.calls.append(("event", event))

    def finish(self, run_dir, result) -> None:  # type: ignore[no-untyped-def]
        self.calls.append(("finish", result))


def test_runner_delegates_doctor_and_persists_success() -> None:
    store = _Store()
    runner = OpencodeRunner(_Process(), store)
    assert runner.doctor() == (True, "ready")
    result = runner.run(prompt="prompt", run_id="run-1", cwd=Path("/work"))
    assert result.succeeded
    assert [call[0] for call in store.calls] == ["begin", "event", "event", "finish"]


def test_runner_persists_process_error_as_failed_result() -> None:
    store = _Store()
    runner = OpencodeRunner(_Process(error=OSError("missing")), store)
    result = runner.run(prompt="prompt", run_id="run-2", cwd=Path("/work"))
    assert result.status is RunStatus.FAILED
    assert result.detail == "missing"
    assert store.calls[-1][0] == "finish"
