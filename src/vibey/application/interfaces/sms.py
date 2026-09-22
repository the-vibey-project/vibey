# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SMS port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SmsPort(Protocol):
    """Common protocol for transactional SMS delivery."""

    async def send_sms(self, phone_number: str, message: str) -> None:
        """Send a transactional SMS notification."""
        ...
