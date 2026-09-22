# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Forward Email adapter implementing the Email port (ADR-0042).

Self-hosted Forward Email (or any SMTP relay) over stdlib smtplib.
"""

from __future__ import annotations

import asyncio
import smtplib
from email.message import EmailMessage

from vibey.application.interfaces.email import EmailPort


class ForwardEmailAdapter(EmailPort):
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
    ) -> None:
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_email = from_email or username or "vibey@localhost"

    async def send_email(self, to_addr: str, subject: str, body: str) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._from_email
        message["To"] = to_addr
        message.set_content(body)
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        # Port 465 is implicit TLS: opening plain SMTP there fails the
        # handshake (or greets in plaintext). STARTTLS is only for submission
        # ports such as 587.
        if self._smtp_port == 465:
            with smtplib.SMTP_SSL(self._smtp_host, self._smtp_port) as server:
                if self._password:
                    server.login(self._username or "", self._password)
                server.send_message(message)
            return
        with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
            server.ehlo()
            if self._password:
                server.starttls()
                server.ehlo()
                server.login(self._username or "", self._password)
            server.send_message(message)
