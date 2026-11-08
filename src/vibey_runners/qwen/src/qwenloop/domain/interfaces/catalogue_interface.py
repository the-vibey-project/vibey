# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Interface for the model catalogue."""

from typing import Protocol, runtime_checkable

from qwenloop.domain.catalogue import ModelEntry


@runtime_checkable
class ModelCatalogueInterface(Protocol):
    """Protocol declaring model catalogue lookup operations."""

    def entries(self) -> tuple[ModelEntry, ...]:
        """Every model entry in the catalogue, in declared order."""
        ...

    def get(self, name: str) -> ModelEntry:
        """Lookup an entry by name or raise KeyError listing known entries."""
        ...

    def by_ollama_tag(self, tag: str) -> ModelEntry | None:
        """Lookup an entry by its Ollama tag, or None if unknown."""
        ...
