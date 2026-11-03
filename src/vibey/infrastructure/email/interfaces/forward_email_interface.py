# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Forward Email seam.

Mirrors `vibey/infrastructure/email/forward_email.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from __future__ import annotations

from email.message import EmailMessage
from typing import Any, Protocol, runtime_checkable

from vibey.application.interfaces.email import EmailPort


@runtime_checkable
class ForwardEmailAdapterInterface(EmailPort, Protocol):
    """The SMTP implementation of the Email port."""


class SmtpSessionInterface(Protocol):
    """One open SMTP connection: the calls the adapter makes on it, in the order it makes them."""

    def __enter__(self) -> SmtpSessionInterface: ...

    def __exit__(self, *exc: Any) -> Any: ...

    def ehlo(self) -> Any: ...

    def starttls(self) -> Any: ...

    def login(self, user: str, password: str) -> Any: ...

    def send_message(self, message: EmailMessage) -> Any: ...


@runtime_checkable
class SmtpConnectorInterface(Protocol):
    """Opens SMTP connections. The declared seam a test substitutes for the network.

    Every open is bounded by `timeout` seconds, which is required, so no connection can be made
    without a bound (gap K3).
    """

    def plain(self, host: str, port: int, *, timeout: float) -> SmtpSessionInterface:
        """A plain SMTP connection, upgraded with STARTTLS by the caller on submission ports."""
        ...

    def implicit_tls(self, host: str, port: int, *, timeout: float) -> SmtpSessionInterface:
        """A connection that is TLS from the first byte (port 465)."""
        ...
