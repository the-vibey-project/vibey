# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Issue Tracker port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class IssueTrackerPort(Protocol):
    """Common protocol for sovereign and paid ticket managers."""

    async def create_ticket(self, title: str, description: str) -> str:
        """Create a new issue/ticket and return its identifier."""
        ...

    async def get_ticket_status(self, ticket_id: str) -> str:
        """Query the current state/status of a ticket."""
        ...
