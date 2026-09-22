# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Issue Tracker implementation of the Tracker port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.tracker import IssueTrackerPort


class InMemoryTracker(IssueTrackerPort):
    """Faked ticket store for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.tickets: dict[str, dict[str, str]] = {}

    async def create_ticket(self, title: str, description: str) -> str:
        ticket_id = f"TICKET-{len(self.tickets) + 1}"
        self.tickets[ticket_id] = {
            "title": title,
            "description": description,
            "status": "open",
        }
        return ticket_id

    async def get_ticket_status(self, ticket_id: str) -> str:
        if ticket_id not in self.tickets:
            raise KeyError(f"ticket {ticket_id!r} not found")
        return self.tickets[ticket_id]["status"]
