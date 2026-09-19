# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam for reading the model side of the fit (ADR-0016).

`MemorySamplerInterface` reads the machine; this reads the model the work wants on it,
from the runner that would serve it. A caller that must not proceed on an assumed model
(doctrine 10) takes this seam, so a test hands it an exact model -- or the absence of one
-- instead of patching a module function (sub-doctrine 9.b).

`Model` is imported for typing only: a frozen data record, the same standing `Machine`
has in the memory seam. Naming the shape a seam speaks in is declaring, not consuming.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey_gh.fit import Model


@runtime_checkable
class ModelSamplerInterface(Protocol):
    """Reads what a runner says about one model it may hold."""

    def sample(self, name: str) -> Model | None:
        """The model as the runner states it, or `None` when the runner does not hold it
        or could not be read -- never a model assumed into existence."""
        ...
