# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Forward Email seam.

Mirrors `vibey/infrastructure/email/forward_email.py` (ADR-0016). Interfaces
declare; they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.email import EmailPort


@runtime_checkable
class ForwardEmailAdapterInterface(EmailPort, Protocol):
    """The SMTP implementation of the Email port."""
