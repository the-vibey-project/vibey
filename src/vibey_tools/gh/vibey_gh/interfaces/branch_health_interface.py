# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for announcing a red permanent branch (vibey ADR-0016)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class BranchHealthVerdict:
    """What one completed CI run says about its branch, and what was done about it.

    `state` is `red`, `green`, `unknown` or `ignored`. Unknown is its own answer, never
    folded into green: a cancelled or half-reported run proves nothing either way, and
    closing the alert on it would announce a recovery nobody observed.
    """

    state: str
    reason: str
    issue: int | None = None


@runtime_checkable
class BranchHealthInterface(Protocol):
    """Reads one completed CI run on a permanent branch and keeps its alert current."""

    def judge(
        self, jobs: Sequence[Mapping[str, Any]], watched: Sequence[str], run_conclusion: str
    ) -> tuple[str, tuple[str, ...]]:
        """(`red`, `green` or `unknown`; the watched jobs that failed), from the run's jobs."""
        ...

    def report(self, run_id: int) -> BranchHealthVerdict:
        """Judge the run and open, update or close the branch's one tracking issue."""
        ...
