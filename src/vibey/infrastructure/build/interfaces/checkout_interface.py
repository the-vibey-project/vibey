# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts of the checkout adapters DECOMPOSE consults.

Mirrors `vibey/infrastructure/build/checkout.py` (ADR-0016). The runtime seams
`BuildDecomposeHandler` consumes are `CheckoutView` and `CheckoutLocator` in
`application/interfaces/build.py`; they are restated here beside the classes, with
what the filesystem view adds. Interfaces declare; they never consume.
"""

from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.interfaces import CheckoutView


@runtime_checkable
class FilesystemCheckoutInterface(Protocol):
    @property
    def root(self) -> Path:
        """The checkout's resolved root."""
        ...

    def exists(self, path: str) -> bool:
        """Whether the checkout-relative path exists inside the root; False when it
        escapes it."""
        ...


@runtime_checkable
class ProjectCheckoutLocatorInterface(Protocol):
    async def checkout(self, project_id: UUID) -> CheckoutView | None:
        """The project's working tree, or None when the project or its tree is gone."""
        ...
