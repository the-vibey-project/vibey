# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/host_health.py` (ADR-0016). Interfaces declare; they never consume."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from pathlib import Path


class HostHealthDoctorInterface(Protocol):
    """`vibey doctor`'s host-health section (scripts/host_health.py)."""

    def record_path(self) -> tuple[Path | None, str]:
        """The record to read, and where that choice came from."""
        ...

    def doctor_lines(self) -> tuple[list[str], bool]: ...
