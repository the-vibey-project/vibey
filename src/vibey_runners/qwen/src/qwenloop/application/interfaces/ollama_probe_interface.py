# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application port for asking whether a local Ollama is running (#388)."""

from typing import Protocol, runtime_checkable


@runtime_checkable
class OllamaProbeInterface(Protocol):
    def available(self) -> bool:
        """True when a local Ollama answers; any failure means it is not available."""
        ...


@runtime_checkable
class OllamaModelProbeInterface(Protocol):
    def capabilities(self, base_url: str, model: str) -> frozenset[str] | None:
        """What an Ollama at `base_url` reports `model` can do, or None when the endpoint is
        not an Ollama or does not say."""
        ...
