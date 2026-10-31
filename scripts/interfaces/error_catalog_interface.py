# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract `scripts/error_catalog.py` implements. Interfaces declare; they never consume."""

from __future__ import annotations

from typing import Protocol

from vibey.cli.interfaces.error_catalog_interface import ErrorCatalogInterface


class ErrorPageInterface(Protocol):
    """Writes the error catalog into a document's GENERATED block."""

    def block(self, catalog: ErrorCatalogInterface) -> str:
        """The text between the markers: one table row per coded error."""
        ...

    def apply(self, document: str, catalog: ErrorCatalogInterface) -> str:
        """`document` with its GENERATED block replaced by the regenerated text."""
        ...

    def drift(self, document: str, catalog: ErrorCatalogInterface) -> bool:
        """True when regeneration would change the block, or the markers are missing."""
        ...
