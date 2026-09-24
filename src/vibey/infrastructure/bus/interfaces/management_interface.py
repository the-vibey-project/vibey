# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The RabbitMQ management API seam.

Mirrors `vibey/infrastructure/bus/management.py` (ADR-0016). Interfaces declare; they
never consume.
"""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class RabbitMqApiErrorInterface(Protocol):
    """An HTTP error from the management API."""

    @property
    def status(self) -> int: ...


@runtime_checkable
class RabbitMqManagementApiInterface(Protocol):
    """Authenticated requests to one broker's management API, scoped to one vhost."""

    @property
    def vhost(self) -> str:
        """The vhost, percent-encoded for a path segment."""
        ...

    def name(self, value: str) -> str: ...

    def request(self, method: str, path: str, payload: dict[str, object] | None = None) -> Any:
        """The decoded JSON, or None for an empty body; an HTTP error raises."""
        ...
