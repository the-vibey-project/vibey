# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The CLI side of backend profiles: `--profile` on run / resume / doctor, the
shared exit-status mapping (75 wind-down, 78 backend misconfigured), and resume's
refusal to cross backends."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from claudeloop.application.dto import RunResult
from claudeloop.application.usecases.doctor import DoctorCheck
from claudeloop.cli.app import app
from claudeloop.cli.interfaces import RunOutcomeReporterInterface
from claudeloop.cli.outcome import RunOutcomeReporter
from claudeloop.domain.errors import BackendProfileError

runner = CliRunner()
_ENV = {"NO_COLOR": "1", "TERM": "dumb"}

_LOCAL_TABLE = """
[profiles.local]
base_url = "http://127.0.0.1:11434"
model_low = "qwen2.5-coder:14b"
model_medium = "qwen2.5-coder:14b"
model_high = "qwen2.5-coder:32b"
"""


def _result(success: bool, reason: str) -> RunResult:
    return RunResult(
        success=success, reason=reason, session_id="s", turns_spent=1, dollars_spent=0.0
    )


# --- RunOutcomeReporter ---


class TestRunOutcomeReporter:
    def _report(self, tmp_path: Path, result: RunResult) -> int:
        try:
            RunOutcomeReporter().report(
                result,
                handoff_marker=tmp_path / "handoff.json",
                stop_summary=tmp_path / "stop-summary.md",
                profile="local",
            )
        except typer.Exit as exc:
            return int(exc.exit_code)
        return 0

    def test_it_satisfies_its_interface(self) -> None:
        assert isinstance(RunOutcomeReporter(), RunOutcomeReporterInterface)

    def test_done_is_zero(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        assert self._report(tmp_path, _result(True, "all done")) == 0
        assert "Done: all done" in capsys.readouterr().out

    def test_wind_down_is_75_and_names_the_handoff(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "handoff.json").write_text("{}")
        assert self._report(tmp_path, _result(False, "wind-down: operator")) == 75
        err = capsys.readouterr().err
        assert "Wound down: wind-down: operator" in err
        assert "Handoff:" in err

    def test_wind_down_without_a_marker_on_disk(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert self._report(tmp_path, _result(False, "wind-down: deadline")) == 75
        assert "Handoff:" not in capsys.readouterr().err

    def test_backend_misconfigured_is_78_and_points_at_doctor(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        code = self._report(
            tmp_path, _result(False, "backend misconfigured (unreachable): Connection refused")
        )
        assert code == 78
        assert "claudeloop doctor --profile local" in capsys.readouterr().err

    def test_stopped_is_130_with_its_summary(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        (tmp_path / "stop-summary.md").write_text("stopped")
        assert self._report(tmp_path, _result(False, "stopped by operator")) == 130
        assert "Stop summary:" in capsys.readouterr().err

    def test_stopped_without_a_summary(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        assert self._report(tmp_path, _result(False, "stopped by operator")) == 130
        assert "Stop summary:" not in capsys.readouterr().err

    def test_any_other_failure_is_1(self, tmp_path: Path) -> None:
        assert self._report(tmp_path, _result(False, "budget exhausted")) == 1


# --- run ---


def _run_invoke(tmp_path: Path, args: list[str], result: RunResult) -> tuple[object, MagicMock]:
    plan = tmp_path / "plan.md"
    plan.write_text("- [ ] do it\n", encoding="utf-8")
    context = MagicMock()
    context.run_id = "r1"
    context.trace_id = "t1"
    context.run_dir.root = tmp_path
    context.run_dir.stop_summary_path = tmp_path / "stop-summary.md"
    with (
        patch("claudeloop.cli.commands.run.configure_logging"),
        patch("claudeloop.cli.commands.run.bootstrap") as bootstrap,
        patch("claudeloop.cli.commands.run.run_from_plan_file", new_callable=AsyncMock) as run,
    ):
        bootstrap.build_runner.return_value = context
        run.return_value = result
        outcome = runner.invoke(
            app,
            ["run", str(plan), "--cwd", str(tmp_path), *args],
            env={**_ENV, "HOME": str(tmp_path)},
        )
    return outcome, bootstrap


def test_run_with_a_local_profile_builds_against_it(tmp_path: Path) -> None:
    (tmp_path / "claudeloop.toml").write_text(_LOCAL_TABLE)
    outcome, bootstrap = _run_invoke(tmp_path, ["--profile", "local"], _result(True, "ok"))
    assert outcome.exit_code == 0, outcome.output
    config = bootstrap.build_runner.call_args.kwargs["config"]
    assert config.backend.name == "local"
    assert config.resolved_profile().model == "qwen2.5-coder:14b"


def test_run_with_an_unknown_profile_is_a_usage_error(tmp_path: Path) -> None:
    outcome, bootstrap = _run_invoke(tmp_path, ["--profile", "nope"], _result(True, "ok"))
    assert outcome.exit_code == 2
    assert "Invalid configuration: unknown profile 'nope'" in outcome.output
    bootstrap.build_runner.assert_not_called()


def test_run_refuses_web_search_on_a_local_profile(tmp_path: Path) -> None:
    (tmp_path / "claudeloop.toml").write_text(_LOCAL_TABLE)
    outcome, _bootstrap = _run_invoke(
        tmp_path, ["--profile", "local", "--web-search"], _result(True, "ok")
    )
    assert outcome.exit_code == 2
    assert "server-side tools" in outcome.output


def test_run_exits_78_when_the_backend_is_misconfigured(tmp_path: Path) -> None:
    (tmp_path / "claudeloop.toml").write_text(_LOCAL_TABLE)
    outcome, _bootstrap = _run_invoke(
        tmp_path,
        ["--profile", "local"],
        _result(False, "backend misconfigured (model_not_found): no such model"),
    )
    assert outcome.exit_code == 78
    assert "claudeloop doctor --profile local" in outcome.output


# --- resume ---


def _resume_invoke(
    tmp_path: Path,
    args: list[str],
    result: RunResult,
    *,
    check_error: Exception | None = None,
) -> tuple[object, MagicMock]:
    context = MagicMock()
    context.run_id = "r1"
    context.trace_id = "t1"
    context.run_dir.root = tmp_path
    context.run_dir.stop_summary_path = tmp_path / "stop-summary.md"
    with (
        patch("claudeloop.cli.commands.resume.configure_logging"),
        patch("claudeloop.cli.commands.resume.bootstrap") as bootstrap,
        patch("claudeloop.cli.commands.resume.resume_explicit", new_callable=AsyncMock) as run,
    ):
        bootstrap.build_runner.return_value = context
        if check_error is not None:
            bootstrap.check_resume_backend.side_effect = check_error
        run.return_value = result
        outcome = runner.invoke(
            app,
            ["resume", "--session-id", "sess-1", "--cwd", str(tmp_path), *args],
            env={**_ENV, "HOME": str(tmp_path)},
        )
    return outcome, bootstrap


def test_resume_exits_75_on_a_wind_down_like_run_does(tmp_path: Path) -> None:
    """It used to print "Run failed" and exit 1 — a supervisor could not tell a
    deliberate handoff from a failure without parsing the text."""
    (tmp_path / "handoff.json").write_text("{}")
    outcome, _bootstrap = _resume_invoke(tmp_path, [], _result(False, "wind-down: operator"))
    assert outcome.exit_code == 75
    assert "Wound down" in outcome.output
    assert "Handoff:" in outcome.output


def test_resume_checks_the_backend_before_building_a_runner(tmp_path: Path) -> None:
    (tmp_path / "claudeloop.toml").write_text(_LOCAL_TABLE)
    outcome, bootstrap = _resume_invoke(tmp_path, ["--profile", "local"], _result(True, "ok"))
    assert outcome.exit_code == 0, outcome.output
    kwargs = bootstrap.check_resume_backend.call_args.kwargs
    assert kwargs["session_id"] == "sess-1"
    assert kwargs["config"].backend.name == "local"


def test_resume_across_backends_is_refused_as_a_usage_error(tmp_path: Path) -> None:
    refusal = BackendProfileError("refusing to resume sess-1: last run against anthropic")
    outcome, bootstrap = _resume_invoke(tmp_path, [], _result(True, "ok"), check_error=refusal)
    assert outcome.exit_code == 2
    assert "refusing to resume sess-1" in outcome.output
    bootstrap.build_runner.assert_not_called()


def test_resume_with_an_invalid_profile_is_a_usage_error(tmp_path: Path) -> None:
    outcome, _bootstrap = _resume_invoke(tmp_path, ["--profile", "nope"], _result(True, "ok"))
    assert outcome.exit_code == 2
    assert "Invalid configuration" in outcome.output


def test_resume_exits_78_when_the_backend_is_misconfigured(tmp_path: Path) -> None:
    outcome, _bootstrap = _resume_invoke(
        tmp_path, [], _result(False, "backend misconfigured (unreachable): refused")
    )
    assert outcome.exit_code == 78


# --- doctor ---


def test_doctor_checks_the_selected_profile(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    (tmp_path / "claudeloop.toml").write_text(_LOCAL_TABLE)
    import claudeloop.cli.commands.doctor as doctor_mod

    seen: dict[str, object] = {}

    def _fake_run_doctor(env, *, cwd, backend, auth_token):  # type: ignore[no-untyped-def]
        seen.update(backend=backend, auth_token=auth_token)
        return [DoctorCheck(name="backend", passed=True, detail="ok")]

    monkeypatch.setattr(doctor_mod.bootstrap, "build_doctor_environment", lambda: object())
    monkeypatch.setattr(doctor_mod, "run_doctor", _fake_run_doctor)
    result = runner.invoke(
        app, ["doctor", "--profile", "local"], env={**_ENV, "HOME": str(tmp_path)}
    )
    assert result.exit_code == 0, result.output
    assert seen["backend"].name == "local"  # type: ignore[attr-defined]
    assert seen["auth_token"] == "ollama"


def test_doctor_with_an_unknown_profile_is_a_usage_error(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.chdir(tmp_path)
    result = runner.invoke(
        app, ["doctor", "--profile", "nope"], env={**_ENV, "HOME": str(tmp_path)}
    )
    assert result.exit_code == 2
    assert "unknown profile 'nope'" in result.output


def test_man_page_documents_profiles_and_exit_78() -> None:
    from claudeloop.cli.man_page import render_man_page

    page = render_man_page()
    assert "--profile NAME" in page
    assert "78" in page
    assert "CLAUDELOOP_PROFILE" in page
