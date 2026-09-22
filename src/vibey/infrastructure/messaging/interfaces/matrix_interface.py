# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The Matrix messaging seam.

Mirrors `vibey/infrastructure/messaging/matrix.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.messaging import MessagingPort


@runtime_checkable
class MatrixMessagingAdapterInterface(MessagingPort, Protocol):
    """The self-hosted Matrix implementation of the Messaging port."""
