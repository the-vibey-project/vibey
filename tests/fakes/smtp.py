# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An SMTP relay that lives in memory, for the adapter's `connector` seam (ADR-0047 lane S05).

It stands in for `STDLIB_SMTP` with no mock and no patching: every open is recorded with the
timeout it was given, every call on the session is recorded in order, and every message sent is
kept. Nothing leaves the process.
"""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any


class InMemorySmtpSession:
    def __init__(self, commands: list[str], messages: list[EmailMessage]) -> None:
        self._commands = commands
        self._messages = messages

    def __enter__(self) -> InMemorySmtpSession:
        return self

    def __exit__(self, *exc: Any) -> None:
        return None

    def ehlo(self) -> None:
        self._commands.append("ehlo")

    def starttls(self) -> None:
        self._commands.append("starttls")

    def login(self, user: str, password: str) -> None:
        self._commands.append(f"login:{user}")

    def send_message(self, message: EmailMessage) -> None:
        self._commands.append("send")
        self._messages.append(message)


class InMemorySmtpServer:
    """Satisfies `SmtpConnectorInterface`."""

    def __init__(self) -> None:
        self.connections: list[tuple[str, str, int]] = []
        """One `(kind, host, port)` per open; kind is `plain` or `implicit_tls`."""
        self.timeouts: list[float] = []
        """The timeout each open was given, at the same index as `connections`."""
        self.commands: list[str] = []
        """Every call made on a session, in order."""
        self.messages: list[EmailMessage] = []

    def plain(self, host: str, port: int, *, timeout: float) -> InMemorySmtpSession:
        return self._open("plain", host, port, timeout)

    def implicit_tls(self, host: str, port: int, *, timeout: float) -> InMemorySmtpSession:
        return self._open("implicit_tls", host, port, timeout)

    def _open(self, kind: str, host: str, port: int, timeout: float) -> InMemorySmtpSession:
        self.connections.append((kind, host, port))
        self.timeouts.append(timeout)
        return InMemorySmtpSession(self.commands, self.messages)
