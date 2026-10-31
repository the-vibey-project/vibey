# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for naming local model families and saying what a model can be tried for.

The domain types the seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.model_families import ModelFamily


@runtime_checkable
class ModelFamiliesInterface(Protocol):
    def all(self) -> tuple[ModelFamily, ...]:
        """Every family, in the order they are shown."""
        ...

    def family_of(self, tag: str) -> ModelFamily | None:
        """The family an Ollama tag belongs to, or None."""
        ...

    def resolve(self, name: str) -> str:
        """A family key becomes its suggested tag; anything else is returned as given."""
        ...

    def jobs(self, capabilities: frozenset[str]) -> tuple[str, ...]:
        """What a model reporting these Ollama capabilities can be tried for."""
        ...
