# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for binding a delivery's correlation id into the log context.

An interface module imports the standard library and other interfaces, and
nothing else from its own tree (ADR-0016) -- hence the domain interface below
rather than the concrete ``DeliveryId``.
"""

from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from vibey.domain.interfaces.delivery_interface import DeliveryIdInterface


@runtime_checkable
class DeliveryLogContextInterface(Protocol):
    """Puts the delivery id on every log line emitted inside its scope."""

    @property
    def field(self) -> str:
        """The key the id is rendered under."""
        ...

    def bind(self, delivery_id: DeliveryIdInterface) -> None:
        """Bind the id for this context, until ``clear`` or process exit."""
        ...

    def clear(self) -> None:
        """Unbind the id. Safe when nothing is bound."""
        ...

    def bound(self, delivery_id: DeliveryIdInterface) -> AbstractContextManager[str]:
        """Bind for the duration of a ``with`` block, yielding the bound value."""
        ...
