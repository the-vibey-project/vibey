# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/web_search_doctor.py` (ADR-0016). Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class WebSearchDoctorInterface(Protocol):
    """`vibey doctor`'s web-search section: the local SearXNG and the Brave backup."""

    def doctor_lines(self) -> tuple[list[str], bool]:
        """The section's lines, and whether it passed (False only for a setting the worker
        would refuse to start with)."""
        ...
