# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind `vibey abandon`.

Mirrors `vibey/cli/abandon.py` (ADR-0016). Interfaces declare; they never consume. The
types the seams are declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from uuid import UUID

    from vibey.application.dto import AbandonmentReport


@runtime_checkable
class AbandonPresenterInterface(Protocol):
    """Renders what an abandonment did, or would do: for a person first, a program
    second."""

    def report(self, report: AbandonmentReport, *, dry_run: bool) -> list[str]:
        """The move, who made it and why, and every job cancelled and gate withdrawn --
        or, for a project already abandoned, that nothing changed."""
        ...

    def document(self, report: AbandonmentReport, *, dry_run: bool) -> dict[str, object]:
        """The JSON object: `project_id`, `name`, `from`, `to`, `cycle`, `dry_run`,
        `already_abandoned`, `written`, `reason`, `by`, `account`, `cancelled_jobs` and
        `withdrawn_gates` -- a fixed contract."""
        ...

    def report_json(self, report: AbandonmentReport, *, dry_run: bool) -> str: ...


@runtime_checkable
class AbandonCommandInterface(Protocol):
    """Runs `vibey abandon` through the one abandonment service."""

    async def run(
        self,
        project_id: UUID,
        *,
        reason: str,
        by: str | None,
        as_json: bool,
        dry_run: bool,
    ) -> None:
        """Exits 2, changing nothing, for a reason or label that cannot be recorded; 1
        for an unknown project; 3 for a project that cannot be abandoned."""
        ...
