# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A wound-down run exits 75, so a supervisor can tell a handoff from a failure (#208).

vibey's BUILD handler starts its no-loss handoff pipeline only when the engine's
process exit code is exactly 75. agyloop printed "Run failed" and exited 1 for
every unsuccessful result, a deliberate wind-down included, so that pipeline could
never fire for it. These tests pin the mapping at every level it can break: the
reporter, the two commands in-process, the real process exit status, and the
runner's own wind-down result fed through the reporter.
"""

from __future__ import annotations

import ast
import os
import subprocess  # nosec B404 -- runs this interpreter on a fixed script, no shell
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import agyloop.cli.interfaces as cli_interfaces
from agyloop.application.dto import RunResult
from agyloop.cli.interfaces import FinishedRun, RunOutcomeReporterInterface
from agyloop.cli.run_outcome import RunOutcomeReporter
from agyloop.domain.budget import Budget
from agyloop.domain.forecast import WindDownPolicy
from agyloop.domain.handoff_marker import EXIT_WIND_DOWN, WIND_DOWN_REASON_PREFIX
from tests.application.fakes import CONTINUE_VERDICT, ScriptedTurn, available_signals
from tests.application.test_runner import make_runner
from tests.test_cli import _invoke

WIND_DOWN_REASON = f"{WIND_DOWN_REASON_PREFIX} headroom:rpd"


def _result(*, success: bool, reason: str) -> RunResult:
    return RunResult(
        success=success, reason=reason, session_id="s1", turns_spent=3, dollars_spent=0.25
    )


def _plan(tmp_path: Path) -> Path:
    plan_file = tmp_path / "plan.md"
    plan_file.write_text("# Plan\n\n- [ ] do the thing\n", encoding="utf-8")
    return plan_file


def _context() -> MagicMock:
    context = MagicMock()
    context.run_id = "r-wind-down"
    context.runner = AsyncMock()
    return context


# -- the exit code a supervisor gates on ------------------------------------------------


def test_the_wind_down_exit_code_is_the_one_vibey_gates_on() -> None:
    """vibey's `EXIT_CODE_WIND_DOWN` is 75; the two sides share no import, only this value."""
    assert EXIT_WIND_DOWN == 75


@pytest.mark.parametrize(
    ("success", "reason", "expected"),
    [
        (True, "completed", 0),
        # Success outranks the prefix: a finished plan is never a handoff.
        (True, WIND_DOWN_REASON, 0),
        (False, WIND_DOWN_REASON, EXIT_WIND_DOWN),
        (False, "budget blown", 1),
        (False, "stopped by operator", 1),
        # Only the prefix counts -- a reason that merely mentions it is a failure.
        (False, f"session dead after {WIND_DOWN_REASON}", 1),
    ],
)
def test_exit_code_for_each_kind_of_result(success: bool, reason: str, expected: int) -> None:
    assert RunOutcomeReporter().exit_code_for(_result(success=success, reason=reason)) == expected


def test_codes_and_prefix_are_substitutable() -> None:
    reporter = RunOutcomeReporter(
        wind_down_prefix="handoff:", wind_down_exit_code=42, failure_exit_code=9
    )

    assert reporter.exit_code_for(_result(success=False, reason="handoff: soon")) == 42
    assert reporter.exit_code_for(_result(success=False, reason=WIND_DOWN_REASON)) == 9
    assert reporter.is_wind_down(_result(success=False, reason="handoff: soon")) is True


def test_the_reporter_and_run_result_satisfy_the_declared_seams() -> None:
    assert isinstance(RunOutcomeReporter(), RunOutcomeReporterInterface)
    assert isinstance(_result(success=False, reason=WIND_DOWN_REASON), FinishedRun)


def test_cli_interfaces_import_only_the_standard_library() -> None:
    """ADR-0016: an interface imports the stdlib and other interfaces, nothing else.

    The tenant's import-linter contract says the same, but the root CI job does not
    run agyloop's `lint-imports`, so this is the check that actually gates it.
    """
    package_dir = Path(cli_interfaces.__file__).parent
    offenders: list[str] = []
    for source in sorted(package_dir.glob("*.py")):
        for node in ast.walk(ast.parse(source.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                names = [node.module]
            else:
                continue
            for name in names:
                root = name.split(".")[0]
                own = name.startswith(f"{cli_interfaces.__name__}.")
                if not own and root != "__future__" and root not in sys.stdlib_module_names:
                    offenders.append(f"{source.name}: {name}")
    assert offenders == []


# -- the two commands, in-process ---------------------------------------------------------


def test_run_exits_75_and_says_wound_down(tmp_path: Path) -> None:
    with (
        patch("agyloop.bootstrap.build_runner", return_value=_context()),
        patch(
            "agyloop.cli.commands.run.run_from_plan_file",
            new_callable=AsyncMock,
            return_value=_result(success=False, reason=WIND_DOWN_REASON),
        ),
    ):
        res = _invoke("run", str(_plan(tmp_path)), "--cwd", str(tmp_path))

    assert res.exit_code == EXIT_WIND_DOWN == 75
    assert f"Wound down: {WIND_DOWN_REASON}" in res.output
    assert "Run failed" not in res.output


def test_resume_exits_75_and_says_wound_down(tmp_path: Path) -> None:
    with (
        patch("agyloop.bootstrap.build_runner", return_value=_context()),
        patch(
            "agyloop.cli.commands.resume.resume_explicit",
            new_callable=AsyncMock,
            return_value=_result(success=False, reason=WIND_DOWN_REASON),
        ),
    ):
        res = _invoke("resume", "--conversation", "c123", "--cwd", str(tmp_path))

    assert res.exit_code == EXIT_WIND_DOWN
    assert f"Wound down: {WIND_DOWN_REASON}" in res.output
    assert "Run failed" not in res.output


# -- the real process exit status ------------------------------------------------------

# Runs the installed console entry point in a fresh interpreter with only the use case
# replaced, so the exit status is the one the operating system reports -- what vibey's
# LoopProcessAdapter reads -- rather than CliRunner's in-process view of a SystemExit.
_ENTRY_POINT_SCRIPT = """
import sys
from unittest.mock import AsyncMock, patch

from agyloop.application.dto import RunResult
from agyloop.cli.app import main

target, reason = sys.argv[1], sys.argv[2]
del sys.argv[1:3]
result = RunResult(
    success=False, reason=reason, session_id="s1", turns_spent=1, dollars_spent=0.0
)
with patch(target, new_callable=AsyncMock, return_value=result):
    main()
"""


def _entry_point(
    tmp_path: Path, target: str, reason: str, *argv: str
) -> subprocess.CompletedProcess[str]:
    env = dict(os.environ)
    env.update({"NO_COLOR": "1", "TERM": "dumb", "HOME": str(tmp_path)})
    return subprocess.run(  # nosec B603 -- fixed argv, this interpreter, no shell
        [sys.executable, "-c", _ENTRY_POINT_SCRIPT, target, reason, *argv],
        capture_output=True,
        text=True,
        env=env,
        cwd=tmp_path,
        timeout=120,
        check=False,
    )


def test_run_process_exit_status_is_75(tmp_path: Path) -> None:
    proc = _entry_point(
        tmp_path,
        "agyloop.cli.commands.run.run_from_plan_file",
        WIND_DOWN_REASON,
        "run",
        str(_plan(tmp_path)),
        "--cwd",
        str(tmp_path),
    )

    assert proc.returncode == EXIT_WIND_DOWN, proc.stderr
    assert f"Wound down: {WIND_DOWN_REASON}" in proc.stderr
    assert "Run failed" not in proc.stderr


def test_resume_process_exit_status_is_75(tmp_path: Path) -> None:
    proc = _entry_point(
        tmp_path,
        "agyloop.cli.commands.resume.resume_explicit",
        WIND_DOWN_REASON,
        "resume",
        "--conversation",
        "c123",
        "--cwd",
        str(tmp_path),
    )

    assert proc.returncode == EXIT_WIND_DOWN, proc.stderr
    assert f"Wound down: {WIND_DOWN_REASON}" in proc.stderr


def test_a_plain_failure_still_exits_1_as_a_process(tmp_path: Path) -> None:
    proc = _entry_point(
        tmp_path,
        "agyloop.cli.commands.run.run_from_plan_file",
        "budget blown",
        "run",
        str(_plan(tmp_path)),
        "--cwd",
        str(tmp_path),
    )

    assert proc.returncode == 1, proc.stderr
    assert "Run failed: budget blown" in proc.stderr


# -- the runner's own wind-down result, end to end -------------------------------------


async def test_the_runners_wind_down_result_maps_to_75() -> None:
    """The reason the runner writes is the reason the CLI recognises.

    Driven through the real runner with the policy on, so a change to how
    `_finish_wound_down` phrases its reason fails here rather than in production.
    """
    runner, *_ = make_runner(
        turns=[ScriptedTurn(signals=available_signals(), verdict=CONTINUE_VERDICT)],
        probes=[available_signals()],
        # One turn of headroom against a reserve of two: the first completed
        # turn is already inside the reserve.
        budget=Budget(max_turns=2, max_dollars=10.0),
    )
    runner._wind_down_policy = WindDownPolicy(enabled=True)

    result = await runner.run(initial_prompt="start", continue_prompt="keep going")

    assert RunOutcomeReporter().exit_code_for(result) == EXIT_WIND_DOWN
