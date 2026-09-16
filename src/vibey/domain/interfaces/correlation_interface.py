# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for one delivery's correlation id and how it is derived."""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class CorrelationIdInterface(Protocol):
    """An identifier that stays the same for one delivery, end to end."""

    @property
    def value(self) -> UUID:
        """The id itself, as written to ``event.correlation_id``."""
        ...


@runtime_checkable
class DeliveryCorrelationInterface(Protocol):
    """Derives delivery correlation ids. Deterministic: same project, same id."""

    @property
    def namespace(self) -> UUID:
        """The namespace every id from this deriver is folded into."""
        ...

    def for_project(self, project_id: UUID) -> CorrelationIdInterface:
        """The delivery's correlation id. Never keyed on the cycle."""
        ...
