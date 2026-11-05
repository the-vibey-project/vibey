# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for naming the sovereign model and resolving which build an operator asked for.

The domain types the seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.sovereign_model import SovereignModel


@runtime_checkable
class SovereignModelsInterface(Protocol):
    def all(self) -> tuple[SovereignModel, ...]:
        """Every build, default first."""
        ...

    def default(self) -> SovereignModel:
        """The build the local loop runs when nothing says otherwise."""
        ...

    def by_key(self, key: str) -> SovereignModel | None:
        """The build a variant key (``heretic``, ``stock``) names, or None."""
        ...

    def variant_of(self, tag: str) -> SovereignModel | None:
        """The build an Ollama tag names exactly, or None."""
        ...

    def same_family(self, tag: str) -> bool:
        """Whether a tag shares the sovereign architecture, so measured fits carry over."""
        ...

    def resolve(self, name: str) -> str:
        """A variant key becomes its tag; any other name is returned as given."""
        ...

    def from_environment(self, environ: Mapping[str, str], *, explicit: str | None = None) -> str:
        """The tag the local loop runs, by the documented precedence."""
        ...
