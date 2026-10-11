# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam behind `--auto-accept-design`: `application/design_auto_accept.py` (ADR-0016).

Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import DesignAutoAcceptReport, ProjectRecord
from vibey.domain.phase import VisualDecision


@runtime_checkable
class DesignAcceptorInterface(Protocol):
    """What accepts a finished DESIGN spec: `DesignAcceptanceService`."""

    async def accept(
        self,
        project_id: UUID,
        *,
        visual_choice: VisualDecision = VisualDecision.DECLINED,
        accepted_by: str | None = None,
    ) -> ProjectRecord:
        """Accept the project's spec; `accepted_by` is written on the ledger event."""
        ...


@runtime_checkable
class DesignAutoAcceptInterface(Protocol):
    """Accepts one project's finished DESIGN spec for an operator who said to."""

    async def run(self, project_id: UUID | None = None) -> DesignAutoAcceptReport:
        """One sweep: accept when DESIGN has settled, say what it is waiting for if not."""
        ...
