# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory SMS implementation."""

from __future__ import annotations

from vibey.application.interfaces.sms import SmsPort


class InMemorySms(SmsPort):
    def __init__(self) -> None:
        self.sent_sms: list[dict[str, str]] = []
        self.sent_keys: list[str | None] = []
        """The idempotency key of each send, in order. Nothing deduplicates on it."""

    async def send_sms(
        self, phone_number: str, message: str, *, idempotency_key: str | None = None
    ) -> None:
        self.sent_keys.append(idempotency_key)
        self.sent_sms.append(
            {
                "phone_number": phone_number,
                "message": message,
            }
        )
