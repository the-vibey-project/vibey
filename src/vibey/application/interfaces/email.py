# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Email port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class EmailPort(Protocol):
    """Common protocol for sovereign and paid email relays."""

    async def send_email(self, to_addr: str, subject: str, body: str) -> None:
        """Send a transactional email message."""
        ...
