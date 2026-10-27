# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for taking a fresh clone to a working contributor environment (ADR-0016)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class SetupStep:
    """One step's observed result.

    `status` is `done`, `unchanged`, `skipped`, `failed`, `unknown` (could not be observed) or
    `advisory` (shown, never failing setup).
    """

    name: str
    status: str
    detail: str = ""


@dataclass(frozen=True, slots=True)
class SetupReport:
    steps: tuple[SetupStep, ...]

    @property
    def ok(self) -> bool:
        return not any(step.status == "failed" for step in self.steps)


@runtime_checkable
class ContributorSetupInterface(Protocol):
    """One idempotent entry point from `git clone` to hooks installed and a database to test on."""

    def run(self, *, postgres: bool = False, doctor: bool = True) -> SetupReport:
        """Do each step, and report only what was observed afterwards."""
        ...

    def check(self) -> SetupReport:
        """Report the same state without changing or running anything."""
        ...

    def render(self, report: SetupReport) -> list[str]:
        """The report as lines for a terminal."""
        ...
