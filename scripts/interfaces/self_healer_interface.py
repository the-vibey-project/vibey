# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/self_healer.py` implements. Interfaces declare; they never consume.

The *forge* lists the integration branch's workflow runs and re-runs one. The *runner* runs a
declared command. The *healer* finds what is red, re-runs the flakes it may, applies the
scripted repairs, and guards what those repairs may change.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Protocol


class RunForgeInterface(Protocol):
    """The forge's Actions API."""

    def runs(self, branch: str, since: datetime) -> list[dict[str, Any]]:
        """Every workflow run on `branch` created at or after `since`."""
        ...

    def rerun_failed(self, run_id: int) -> bool:
        """Re-run the run's failed jobs. False when the forge refused."""
        ...


class ArgvRunnerInterface(Protocol):
    """Runs one argv list, never through a shell."""

    def run(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        """The exit code and the combined output."""
        ...


class SelfHealerInterface(Protocol):
    """The daily self-healer's deterministic half."""

    def failing(self, now: datetime) -> list[dict[str, Any]]:
        """The newest run of each workflow on the branch in the window, where it failed."""
        ...

    def rerun(self, failing: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Re-run the allowlisted first attempts, capped; returns those re-run."""
        ...

    def repair(self) -> list[dict[str, Any]]:
        """Run every declared repair in order; returns each one's name and exit code."""
        ...

    def refused(self, touched: list[tuple[str, str]] | None) -> list[str]:
        """The paths a repair patch changes outside the declared allowed paths, given what it
        changes as (status, path); None (unreadable) and nothing are refused outright."""
        ...


class AdvisoryLockInterface(Protocol):
    """Takes the fixed release of each Python dependency a pip-audit report names."""

    def fixable(self, report: str) -> list[str]:
        """The names in a pip-audit JSON report that have at least one fixed version."""
        ...

    def run(self) -> int:
        """Audit, then re-lock those names; the exit code of the re-lock (0 when none)."""
        ...
