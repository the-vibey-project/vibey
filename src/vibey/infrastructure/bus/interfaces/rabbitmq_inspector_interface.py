# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The RabbitMQ inspector seam.

Mirrors `vibey/infrastructure/bus/rabbitmq_inspector.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from typing import Protocol, runtime_checkable

from vibey.application.interfaces.queue_reap import BusInspectorPort


@runtime_checkable
class RabbitMqBusInspectorInterface(BusInspectorPort, Protocol):
    """The management API's view of one vhost, for the queue reaper."""
