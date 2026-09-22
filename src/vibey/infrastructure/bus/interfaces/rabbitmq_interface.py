# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The RabbitMQ bus seam.

Mirrors `vibey/infrastructure/bus/rabbitmq.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.bus import BusPort


@runtime_checkable
class RabbitMqBusAdapterInterface(BusPort, Protocol):
    """The self-hosted RabbitMQ implementation of the Bus port."""
