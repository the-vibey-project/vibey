# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Forward Email adapter implementing the Email port (ADR-0042).

Self-hosted Forward Email (or any SMTP relay) over stdlib smtplib.
"""

from __future__ import annotations

import asyncio
import hashlib
import smtplib
from email.message import EmailMessage

from vibey.application.interfaces.email import EmailPort
from vibey.domain.config import DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS
from vibey.infrastructure.email.interfaces.forward_email_interface import (
    SmtpConnectorInterface,
    SmtpSessionInterface,
)


class StdlibSmtpConnector:
    """Opens real connections with `smtplib`, each bounded by the timeout it is given."""

    def plain(self, host: str, port: int, *, timeout: float) -> SmtpSessionInterface:
        return smtplib.SMTP(host, port, timeout=timeout)

    def implicit_tls(self, host: str, port: int, *, timeout: float) -> SmtpSessionInterface:
        return smtplib.SMTP_SSL(host, port, timeout=timeout)


STDLIB_SMTP: SmtpConnectorInterface = StdlibSmtpConnector()


class ForwardEmailAdapter(EmailPort):
    def __init__(
        self,
        *,
        smtp_host: str,
        smtp_port: int,
        username: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
        timeout: float = DEFAULT_SURFACE_ADAPTER_TIMEOUT_SECONDS,
        connector: SmtpConnectorInterface = STDLIB_SMTP,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        self._connector = connector
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._username = username
        self._password = password
        self._from_email = from_email or username or "vibey@localhost"
        self._timeout = timeout

    async def send_email(
        self, to_addr: str, subject: str, body: str, *, idempotency_key: str | None = None
    ) -> None:
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = self._from_email
        message["To"] = to_addr
        if idempotency_key is not None:
            # A courtesy to receivers, not a guarantee: SMTP cannot deduplicate, the guard does.
            digest = hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:32]
            domain = self._from_email.rpartition("@")[2] if "@" in self._from_email else ""
            message["Message-ID"] = f"<vibey.{digest}@{domain or 'localhost'}>"
        message.set_content(body)
        await asyncio.to_thread(self._send_sync, message)

    def _send_sync(self, message: EmailMessage) -> None:
        # Port 465 is implicit TLS: opening plain SMTP there fails the
        # handshake (or greets in plaintext). STARTTLS is only for submission
        # ports such as 587.
        if self._smtp_port == 465:
            with self._connector.implicit_tls(
                self._smtp_host, self._smtp_port, timeout=self._timeout
            ) as server:
                if self._password:
                    server.login(self._username or "", self._password)
                server.send_message(message)
            return
        with self._connector.plain(
            self._smtp_host, self._smtp_port, timeout=self._timeout
        ) as server:
            server.ehlo()
            if self._password:
                server.starttls()
                server.ehlo()
                server.login(self._username or "", self._password)
            server.send_message(message)
