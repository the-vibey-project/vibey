# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract behind `vibey doctor`'s host-health section.

Mirrors `vibey/domain/host_health.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.domain.host_health import HostHealthSummary


@runtime_checkable
class HostHealthReportInterface(Protocol):
    """Reads the weekly host-health record and says what `vibey doctor` prints. Pure."""

    def newest(self, text: str) -> HostHealthSummary | None:
        """The newest well-formed record in the JSON-lines `text`, or None when there is none."""
        ...

    def doctor_lines(
        self,
        summary: HostHealthSummary | None,
        *,
        source: str,
        now: datetime,
        max_age_days: int,
        required: bool,
    ) -> tuple[list[str], bool]:
        """The lines, and False only when `required` and the record is missing or stale."""
        ...
