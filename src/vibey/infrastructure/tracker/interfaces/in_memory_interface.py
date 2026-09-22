# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory tracker seam.

Mirrors `vibey/infrastructure/tracker/in_memory.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.tracker import IssueTrackerPort


@runtime_checkable
class InMemoryTrackerInterface(IssueTrackerPort, Protocol):
    """The in-memory implementation of the Tracker port."""
