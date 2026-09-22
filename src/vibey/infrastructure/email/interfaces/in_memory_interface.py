# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory email seam.

Mirrors `vibey/infrastructure/email/in_memory.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.email import EmailPort


@runtime_checkable
class InMemoryEmailInterface(EmailPort, Protocol):
    """The in-memory implementation of the Email port."""
