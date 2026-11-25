# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for pulling a model into Ollama (`vibey install --model`).

Mirrors `vibey/infrastructure/ollama_pull.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.infrastructure.ollama_pull import ModelInstallResult


@runtime_checkable
class OllamaModelPullerInterface(Protocol):
    def install(self, tag: str, say: Callable[[str], None], size: str | None) -> ModelInstallResult:
        """Pull `tag` unless it is there, saying its size (when known) and its progress."""
        ...
