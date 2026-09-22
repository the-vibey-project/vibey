# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The service-bus port seam (ADR-0042)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class BusPort(Protocol):
    """Common protocol for FOSS queue backends with dead-letter queues.

    Sovereign default: RabbitMQ. Queues are durable; a rejected or expired
    message lands on `<queue>.dlq`, which is what makes the system
    event-driven without losing poison messages.
    """

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        """Declare a durable queue (and its DLQ wiring); declaring twice is not an error."""
        ...

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        """Publish one JSON payload to a queue (declares it first when missing)."""
        ...

    async def consume(self, queue: str) -> dict[str, object] | None:
        """Take one message off a queue, or None when it is empty."""
        ...
