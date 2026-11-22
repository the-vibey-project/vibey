# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `cli/web_tools_doctor.py` (ADR-0016). Interfaces declare; they never consume."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class WebToolsDoctorInterface(Protocol):
    """`vibey doctor`'s `web-tools` line: the hub's search and fetch, for the agent."""

    def line(self) -> str:
        """One `MARK web-tools detail` line; never raises."""
        ...
