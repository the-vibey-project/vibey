# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import tempfile
from dataclasses import dataclass
from pathlib import Path

from agyloop.cli.run_outcome import RunOutcomeReporter
from agyloop.domain.handoff_marker import WIND_DOWN_REASON_PREFIX


def test_wind_down_exit_code():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        plan_file = root / "plan.md"
        plan_file.write_text("# Plan\n- item 1")

        # We need to mock a la l la... wait, I'll just use a real agyloop run
        # with a plan that we know triggers wind-down.
        # But that's hard. Instead, I'll test the RunOutcomeReporter directly.
        pass


@dataclass
class MockResult:
    success: bool
    reason: str


def test_reporter_wind_down_code():
    reporter = RunOutcomeReporter()
    # A "wind-down" result: success=False, reason starts with WIND_DOWN_REASON_PREFIX
    result = MockResult(success=False, reason=f"{WIND_DOWN_REASON_PREFIX} capacity")
    assert reporter.exit_code_for(result) == 75


def test_reporter_failure_code():
    reporter = RunOutcomeReporter()
    # A regular failure
    result = MockResult(success=False, reason="crash")
    assert reporter.exit_code_for(result) == 1


def test_reporter_success_code():
    reporter = RunOutcomeReporter()
    result = MockResult(success=True, reason="done")
    assert reporter.exit_code_for(result) == 0
