# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Messaging implementation of the Instant Messenger port (ADR-0042)."""

from __future__ import annotations

from vibey.application.interfaces.messaging import MessagingPort


class InMemoryMessaging(MessagingPort):
    """Faked outbox for testing and unconfigured local runs."""

    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []

    async def send_message(self, channel_id: str, message: str) -> None:
        self.sent.append({"channel_id": channel_id, "message": message})
