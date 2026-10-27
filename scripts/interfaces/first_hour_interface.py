# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/first_hour.py` implements. Interfaces declare; they never consume.

A *ledger* is a JSON-lines record that is read whole and appended to, never rewritten. A
*measurer* performs the documented first hour and times every step. A *renderer* writes the
latest complete measurement into the first-hour guide. A *collector* folds survey answers
into the survey ledger, consuming every answer it has not yet recorded.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Protocol


class FirstHourLedgerInterface(Protocol):
    """An append-only JSON-lines record keyed by an identity, never by a timestamp."""

    def read(self) -> list[dict[str, Any]]:
        """Every record in file order; a malformed or repeated line is an error naming it."""
        ...

    def append(self, record: Mapping[str, Any]) -> bool:
        """Add the record, unless its identity is already here. True when it was added."""
        ...


class FirstHourMeasurerInterface(Protocol):
    """Performs the documented first hour in a clean directory and times each step."""

    def measure(self, workdir: Path, run_id: str, environ: Mapping[str, str]) -> dict[str, Any]:
        """One record: each step's seconds and outcome, the commit, and whether it completed."""
        ...


class GuideRendererInterface(Protocol):
    """Writes the latest complete measurement into the guide's GENERATED block."""

    def render(self, text: str, records: Sequence[Mapping[str, Any]]) -> str:
        """The guide text with its block regenerated from the record."""
        ...

    def problems(self, text: str, records: Sequence[Mapping[str, Any]]) -> list[str]:
        """What is out of step between the guide and the record; empty when none is."""
        ...


class SurveyCollectorInterface(Protocol):
    """Folds survey answers into the survey ledger."""

    def body(self, quarter: str) -> str:
        """The text of the quarter's survey issue."""
        ...

    def collect(self, comments: Sequence[Mapping[str, Any]], quarter: str) -> int:
        """Record every comment whose id the ledger lacks. Returns how many were new."""
        ...
