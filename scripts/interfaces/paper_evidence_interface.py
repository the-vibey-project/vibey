# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/paper_evidence.py` implements. Interfaces declare; they never consume.

`StressRung` is the one value shape the contracts exchange: a row of the stress record's
table, exactly as the record prints it.
"""

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class StressRung:
    """One rung of the stress record: offered concurrency and what came back."""

    concurrency: int
    attempted: int
    succeeded: int
    p50_seconds: float
    max_seconds: float
    throughput_per_minute: float


class StressRecordInterface(Protocol):
    """Reads the tracked stress record and summarises its rung table."""

    def rungs(self) -> tuple[StressRung, ...]:
        """Every row of the rung table, in the record's order."""
        ...

    def summary(self) -> dict[str, Any]:
        """The totals, the stable-region band, and the held-out band check."""
        ...


class GitHistoryInterface(Protocol):
    """Reads this checkout's git history and summarises its production record."""

    def summary(self) -> dict[str, Any]:
        """Commit, day, hour, pull-request and release-tag counts at HEAD."""
        ...


class PaperEvidenceInterface(Protocol):
    """Composes both sources into the report the paper's numbers are traced to."""

    def collect(self) -> dict[str, Any]:
        """Both summaries, keyed by source, plus the revision they were read at."""
        ...

    def render(self, evidence: dict[str, Any]) -> str:
        """A human-readable report of `collect()`'s result."""
        ...
