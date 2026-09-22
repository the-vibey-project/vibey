# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Instant Messenger port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class MessagingPort(Protocol):
    """Common protocol for matrix/element and instant messenger relays."""

    async def send_message(self, channel_id: str, message: str) -> None:
        """Send an instant message to a channel/room."""
        ...
