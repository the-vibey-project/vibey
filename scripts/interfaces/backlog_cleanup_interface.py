# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts `scripts/backlog_cleanup.py` implements. Interfaces declare; they never consume.

A *probe* answers one check against the checkout or the forge. The *cleanup* surveys
every open issue against the declared expectations and applies only what changed.
"""

from typing import Any, Protocol


class ProbeInterface(Protocol):
    """One check: does the evidence for an expectation hold right now?"""

    def name(self) -> str:
        """The probe's stable name, as written in the expectations file."""
        ...

    def holds(self, context: dict[str, Any]) -> bool:
        """True when the evidence holds. Never raises: failure is False."""
        ...


class BacklogCleanupInterface(Protocol):
    """The hourly backlog loop: survey the open issues, apply only changes."""

    def survey(self) -> list[dict[str, Any]]:
        """One verdict row per open issue: number, verdict, evidence, missing, next."""
        ...

    def apply(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        """Post marker-guarded comments and close resolved issues. Capped and paced."""
        ...

    def coverage_gaps(self, rows: list[dict[str, Any]]) -> list[int]:
        """Open issues with no expectations entry and no cleanup marker: triage debt."""
        ...
