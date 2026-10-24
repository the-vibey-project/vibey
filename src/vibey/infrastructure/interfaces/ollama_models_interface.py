# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for asking an Ollama which models it has and what they can do."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.ollama_models import InstalledModel


@runtime_checkable
class OllamaModelsInterface(Protocol):
    def installed(self) -> tuple[InstalledModel, ...]:
        """Every model the Ollama has. Raises `OllamaUnavailable` when none answers."""
        ...

    def capabilities(self, tag: str) -> frozenset[str] | None:
        """What Ollama reports for a model, or None when it does not say."""
        ...
