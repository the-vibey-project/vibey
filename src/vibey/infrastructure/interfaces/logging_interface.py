# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for binding a delivery's correlation id into the log context.

An interface module imports the standard library and other interfaces, and
nothing else from its own tree (ADR-0016) -- hence the domain interface below
rather than the concrete ``CorrelationId``.
"""

from contextlib import AbstractContextManager
from typing import Protocol, runtime_checkable

from vibey.domain.interfaces.correlation_interface import CorrelationIdInterface


@runtime_checkable
class CorrelationLogContextInterface(Protocol):
    """Puts the delivery's correlation id on every log line in its scope."""

    @property
    def field(self) -> str:
        """The key the id is rendered under."""
        ...

    def bind(self, correlation_id: CorrelationIdInterface) -> None:
        """Bind the id for this context, until ``clear`` or process exit."""
        ...

    def clear(self) -> None:
        """Unbind the id. Safe when nothing is bound."""
        ...

    def bound(self, correlation_id: CorrelationIdInterface) -> AbstractContextManager[str]:
        """Bind for a ``with`` block, restoring the prior binding on exit."""
        ...
