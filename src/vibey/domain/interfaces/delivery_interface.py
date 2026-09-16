# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for one delivery's correlation id and how it is derived."""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class DeliveryIdInterface(Protocol):
    """An identifier that stays the same for one delivery, end to end."""

    @property
    def value(self) -> UUID:
        """The id itself."""
        ...


@runtime_checkable
class DeliveryCorrelationInterface(Protocol):
    """Derives delivery ids. Deterministic: same project, same id, always."""

    @property
    def namespace(self) -> UUID:
        """The namespace every id from this deriver is folded into."""
        ...

    def for_project(self, project_id: UUID) -> DeliveryIdInterface:
        """The delivery id for the project. Never keyed on the cycle."""
        ...
