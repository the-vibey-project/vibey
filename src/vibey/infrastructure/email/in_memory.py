# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Email implementation of the Email port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.email import EmailPort


class InMemoryEmail(EmailPort):
    """Faked outbox for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send_email(self, to_addr: str, subject: str, body: str) -> None:
        self.sent.append({"to": to_addr, "subject": subject, "body": body})
