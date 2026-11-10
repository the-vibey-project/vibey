# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/ci_cost_baseline.py` implements. Interfaces declare; they never consume.

A *reader* asks the forge's Actions API for workflows, runs, jobs and timing (GET only, and
every method raises `ForgeUnavailable` when the forge cannot answer). *Statistics* computes the
percentiles. A *runner OS* classifier maps a job's runner labels to an operating system. The
*baseline* collects one record of what CI cost over a window, naming the window and the cutoff.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable


class ClockInterface(Protocol):
    """The time, in UTC, for the one place a measurement is stamped."""

    def now(self) -> str:
        """An ISO-8601 UTC timestamp to the second, ending in `Z`."""
        ...


class GhActionsReaderInterface(Protocol):
    """Reads the Actions API of one repository. Reads only; never a write."""

    def repository(self) -> Mapping[str, Any]:
        """The repository object (carries `private` and `visibility`)."""
        ...

    def workflows(self) -> list[dict[str, Any]]:
        """Every workflow: id, name, path and state."""
        ...

    def runs_page(
        self, workflow_id: int, *, page: int, per_page: int, since: str | None
    ) -> tuple[int, list[dict[str, Any]]]:
        """(total_count, one page of runs, newest first) created at or after `since` when given."""
        ...

    def jobs(self, run_id: int) -> list[dict[str, Any]]:
        """Every job of one run."""
        ...

    def timing(self, run_id: int) -> Mapping[str, Any]:
        """The run's timing object (billable milliseconds by runner OS)."""
        ...

    @property
    def calls(self) -> int:
        """How many API calls this reader has made."""
        ...


class StatisticsInterface(Protocol):
    """Percentiles over a list of numbers."""

    def percentile(self, values: Sequence[float], q: float) -> float | None:
        """The `q`-th percentile (0-100) by linear interpolation; None for no values."""
        ...


class RunnerOsInterface(Protocol):
    """Classifies a job's runner labels."""

    def of(self, labels: Sequence[str]) -> str:
        """One of `ubuntu`, `macos`, `windows` or `other`."""
        ...


@runtime_checkable
class CiCostBaselineInterface(Protocol):
    """Collects the CI cost record for a window."""

    def collect(self, since_days: int) -> dict[str, object]:
        """The record: window and cutoff, per-workflow figures, totals, cost basis, unknowns."""
        ...
