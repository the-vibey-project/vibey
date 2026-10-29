# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The SMS port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class SmsPort(Protocol):
    """Common protocol for transactional SMS delivery."""

    async def send_sms(
        self, phone_number: str, message: str, *, idempotency_key: str | None = None
    ) -> None:
        """Send a transactional SMS notification.

        The key names one logical message. The backend cannot deduplicate it; the surface
        lane guards it (ADR-0047 §8).
        """
        ...
