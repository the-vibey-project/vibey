# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam behind gate timeouts: `application/gate_timeouts.py` (ADR-0016).

Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import GateTimeoutReport


@runtime_checkable
class GateTimeoutSweepInterface(Protocol):
    """Resolves waiting gates to their default where each project declared that kind may."""

    async def run(self, project_id: UUID | None = None) -> GateTimeoutReport:
        """One sweep over one project's open gates, or every project's."""
        ...

    async def run_if_due(self, project_id: UUID | None) -> GateTimeoutReport | None:
        """A sweep at most once per interval per scope and process; None when not due."""
        ...
