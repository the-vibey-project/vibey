# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/autonomy_scorecard.py` implements. Interfaces declare; they never consume.

A *source* observes figures from one place (the forge, the review canary, the repository,
the local queue) and returns them, measured, declared or unknown with the reason. A
*staleness policy* carries a figure a run could not re-read forward from the last record,
marked stale, until it is too old to stand. An *evaluator* judges each declared stage from
its figures. A *ledger* appends one digest-chained line per measurement. A *renderer* writes
the latest measurement into a document's GENERATED blocks.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class CommandRunnerInterface(Protocol):
    """Runs one command and reports what it did; a missing tool is a result, not a crash."""

    def run(
        self, argv: Sequence[str], *, timeout: float, env: Mapping[str, str] | None = None
    ) -> Any:
        """A result carrying `returncode`, `stdout` and `stderr`."""
        ...


class ClockInterface(Protocol):
    """The time, in UTC, for the one place a measurement is stamped."""

    def now(self) -> str:
        """An ISO-8601 UTC timestamp, to the second, ending in `Z`."""
        ...


class ForgeClientInterface(Protocol):
    """Reads the forge. Every method raises `SourceUnavailable` when the forge cannot answer."""

    def merged_pulls(self, base: str, since: str) -> list[dict[str, Any]]:
        """Pull requests merged into `base` on or after the day `since` names."""
        ...

    def check_runs(self, sha: str, name: str) -> list[dict[str, Any]]:
        """The check runs called `name` on commit `sha`."""
        ...

    def rulesets(self) -> list[dict[str, Any]]:
        """Every ruleset of the repository, each with its conditions and rules."""
        ...

    def workflow_runs(
        self, workflow: str, *, branch: str | None, event: str | None, since: str
    ) -> list[dict[str, Any]]:
        """Runs of `workflow` created on or after the day `since` names."""
        ...


class QueueReaderInterface(Protocol):
    """Reads the local queue, read-only. Raises `SourceUnavailable` when it cannot."""

    def gates(self, start: str, end: str) -> list[dict[str, Any]]:
        """Gates raised in [start, end): kind, phase, answered_by, answered_at."""
        ...

    def jobs_succeeded(self, phase: str, start: str, end: str) -> int:
        """Jobs of `phase` that reached `succeeded` in [start, end)."""
        ...

    def transitions(self, to: str, start: str, end: str) -> int:
        """Phase transitions into `to` recorded in [start, end)."""
        ...

    def last_event_at(self, end: str) -> str | None:
        """The latest event recorded before `end`, or None when there is none."""
        ...

    def engine_auth(self) -> dict[str, str | None]:
        """Each engine's latest successful login check, across every project."""
        ...


class SourceInterface(Protocol):
    """Observes the figures one place can give."""

    name: str

    def observe(self, cutoff: str) -> list[Any]:
        """Every figure this source declares: measured, declared, or unknown with the reason."""
        ...


class StalenessPolicyInterface(Protocol):
    """Merges a run's figures with the previous record's."""

    def merge(
        self, previous: Sequence[Mapping[str, Any]], fresh: Sequence[Any], cutoff: str
    ) -> list[Any]:
        """Fresh figures, and previous ones carried forward as stale where a run missed them."""
        ...


class StageEvaluatorInterface(Protocol):
    """Judges each declared stage from the figures."""

    def evaluate(self, stages: Sequence[Mapping[str, Any]], figures: Sequence[Any]) -> list[Any]:
        """One verdict per stage: autonomous, partial, manual or unknown, with each criterion's."""
        ...


class ScorecardLedgerInterface(Protocol):
    """The append-only, digest-chained record."""

    def read(self, path: Path) -> tuple[Mapping[str, Any], ...]:
        """Every measurement, oldest first; `ValueError` for a broken chain."""
        ...

    def append(self, path: Path, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Append one measurement after the last, chained to it."""
        ...


class ScorecardRendererInterface(Protocol):
    """Writes the latest measurement into a document's GENERATED blocks."""

    def blocks(self, entry: Mapping[str, Any]) -> dict[str, str]:
        """Each block's body, by name."""
        ...
