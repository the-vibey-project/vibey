# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam behind `--auto-answer`: `application/gate_auto_answers.py` (ADR-0016).

Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import GateAutoAnswerReport


@runtime_checkable
class GateAutoAnswerSweepInterface(Protocol):
    """Answers the waiting gates a worker was told it may answer, up to its limit."""

    async def run(self, project_id: UUID | None = None) -> GateAutoAnswerReport:
        """One sweep over one project's open gates, or every project's."""
        ...
