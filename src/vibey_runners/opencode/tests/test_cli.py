# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from pathlib import Path

from typer.testing import CliRunner

from opencodeloop.cli import app as cli
from opencodeloop.domain.model import RunResult, RunStatus


class _Runner:
    def __init__(self, ready: bool = True, success: bool = True, detail: str = "") -> None:
        self.ready = ready
        self.success = success
        self.detail = detail
        self.calls: list[dict[str, object]] = []

    def doctor(self) -> tuple[bool, str]:
        return self.ready, "ready" if self.ready else "not ready"

    def run(self, **kwargs):  # type: ignore[no-untyped-def]
        self.calls.append(kwargs)
        return RunResult(
            RunStatus.FINISHED if self.success else RunStatus.FAILED,
            0 if self.success else 1,
            detail=self.detail,
        )


def test_cli_version_and_doctor(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    runner = CliRunner()
    assert runner.invoke(cli.app, ["--version"]).exit_code == 0
    assert isinstance(cli._runner(), object)
    ready = _Runner()
    monkeypatch.setattr(cli, "_runner", lambda: ready)
    assert runner.invoke(cli.app, ["doctor"]).exit_code == 0
    not_ready = _Runner(ready=False)
    monkeypatch.setattr(cli, "_runner", lambda: not_ready)
    assert runner.invoke(cli.app, ["doctor"]).exit_code == 1


def test_cli_run_and_resume_propagate_status(tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    plan = tmp_path / "plan.md"
    plan.write_text("prompt", encoding="utf-8")
    runner = _Runner()
    monkeypatch.setattr(cli, "_runner", lambda: runner)
    result = CliRunner().invoke(
        cli.app, ["run", str(plan), "--run-id", "r-1", "--cwd", str(tmp_path)]
    )
    assert result.exit_code == 0
    assert runner.calls[0]["prompt"] == "prompt"
    assert runner.calls[0]["run_id"] == "r-1"
    assert runner.calls[0]["cwd"] == Path(tmp_path).resolve()

    result = CliRunner().invoke(cli.app, ["resume", "s-1", "--cwd", str(tmp_path)])
    assert result.exit_code == 0
    assert runner.calls[1]["session_id"] == "s-1"
    assert runner.calls[1]["prompt"] == cli.RESUME_PROMPT

    failed = _Runner(success=False, detail="failed")
    monkeypatch.setattr(cli, "_runner", lambda: failed)
    assert CliRunner().invoke(cli.app, ["run", str(plan)]).exit_code == 1
    assert CliRunner().invoke(cli.app, ["resume", "s-2"]).exit_code == 1


def test_main_delegates_to_typer_app(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    called: list[bool] = []
    monkeypatch.setattr(cli, "app", lambda: called.append(True))
    cli.main()
    assert called == [True]
