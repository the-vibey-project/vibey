# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/model_quality_study.py` implements. Interfaces declare; they never consume.

A *task loader* reads a task directory. A *workspace* builds the fresh git repository one trial
runs in. A *runner* drives the real `qwenloop` once and reports what it did. A *scorer* judges
the result with checks the model never saw. A *model preparer* screens a model and builds its
derived tag. A *ledger* appends one digest-chained line per trial. A *summarizer* turns the
ledger into solve rates with Wilson intervals.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class ClockInterface(Protocol):
    def now(self) -> str:
        """An ISO-8601 UTC timestamp, to the second, ending in `Z`."""
        ...


class CommandRunnerInterface(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        cwd: str | None = None,
        timeout: float,
        env: Mapping[str, str] | None = None,
    ) -> Any:
        """A result carrying `returncode` (124 is a timeout, 127 a missing tool), `stdout`, `stderr`."""
        ...


class TaskLoaderInterface(Protocol):
    def load_all(self, root: Path) -> tuple[Any, ...]:
        """Every task under `root`, sorted by id; a malformed task raises `ValueError`."""
        ...

    def split(self, tasks: Sequence[Any], *, screening: int, seed: int) -> tuple[Any, Any]:
        """(screening, confirmation), chosen by a seeded shuffle, balanced across tiers."""
        ...


class WorkspaceInterface(Protocol):
    def create(self, task: Any, parent: Path) -> Path:
        """A fresh git repository holding the task's seed and plan, never its hidden tests."""
        ...


class TrialRunnerInterface(Protocol):
    def run(self, *, workspace: Path, tag: str, plan: str) -> Mapping[str, Any]:
        """Drive `qwenloop run` once; return exit status, seconds and the event tallies."""
        ...


class TrialScorerInterface(Protocol):
    def score(self, task: Any, workspace: Path) -> Mapping[str, Any]:
        """Copy the hidden tests in, run every declared check, and classify the outcome."""
        ...


class ModelPreparerInterface(Protocol):
    def screen(self, entry: Mapping[str, Any]) -> Mapping[str, Any]:
        """Tool-calling, licence and fit verdicts for one candidate, with the reason for each."""
        ...

    def derive(self, entry: Mapping[str, Any], num_ctx: int) -> str:
        """Build (or reuse) the `num_ctx` derived Ollama tag and return its name."""
        ...


class StudyLedgerInterface(Protocol):
    def append(self, payload: Mapping[str, Any]) -> Mapping[str, Any]:
        """Append one trial; the chain is verified first."""
        ...

    def read(self) -> tuple[Mapping[str, Any], ...]:
        """Every recorded trial, oldest first; a broken chain raises."""
        ...


class StudySummarizerInterface(Protocol):
    def summarize(self, trials: Sequence[Mapping[str, Any]], z: float) -> Mapping[str, Any]:
        """Per-model and per-tier solve rates with Wilson intervals and the ranking."""
        ...

    def decide(
        self, summary: Mapping[str, Any], models: Sequence[Mapping[str, Any]]
    ) -> Mapping[str, Any]:
        """The decision rule of the preregistration, applied; says why, never just who."""
        ...
