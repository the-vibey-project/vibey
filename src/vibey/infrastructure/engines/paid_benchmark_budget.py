# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Durable global spend guard for paid-model benchmarking."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class PaidBenchmarkBudget:
    """A monotonic total cap; sovereign calls never consume it."""

    cap_usd: float = 20.0
    spent_usd: float = 0.0

    @property
    def remaining_usd(self) -> float:
        return max(self.cap_usd - self.spent_usd, 0.0)

    def authorize(self, estimate_usd: float) -> bool:
        return estimate_usd >= 0 and estimate_usd <= self.remaining_usd

    def charge(self, amount_usd: float) -> PaidBenchmarkBudget:
        if amount_usd < 0 or amount_usd > self.remaining_usd:
            raise ValueError("paid benchmark charge exceeds the global budget")
        return PaidBenchmarkBudget(self.cap_usd, self.spent_usd + amount_usd)


class PaidBenchmarkBudgetStore:
    """Persist and atomically update the paid benchmark budget."""

    def __init__(self, path: Path, *, cap_usd: float = 20.0) -> None:
        if cap_usd < 0:
            raise ValueError("paid benchmark cap must not be negative")
        self._path = path
        self._cap_usd = cap_usd

    def load(self) -> PaidBenchmarkBudget:
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
            spent = float(raw["spent_usd"])
        except (OSError, KeyError, TypeError, ValueError):
            spent = 0.0
        return PaidBenchmarkBudget(self._cap_usd, max(spent, 0.0))

    def charge(self, amount_usd: float) -> PaidBenchmarkBudget:
        budget = self.load().charge(amount_usd)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._path.with_suffix(".tmp")
        temporary.write_text(
            json.dumps({"cap_usd": budget.cap_usd, "spent_usd": budget.spent_usd}, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self._path)
        return budget
