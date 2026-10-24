# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for slicing a BUILD decomposition into the CDD layers (ADR-0092).

The domain types the seam is declared over are imported under TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from vibey.domain.plan import WorkItem
    from vibey.domain.slicing import SlicePlan


@runtime_checkable
class AutoSlicerInterface(Protocol):
    """Lays the project, phase, epic and story layers over a decomposition and orders the
    groups -- the whole plan at once, never one item at a time."""

    @property
    def max_children(self) -> int:
        """The most children one group holds before the plan gains the next layer out."""
        ...

    def slice(self, items: Sequence[WorkItem]) -> SlicePlan:
        """The slices of `items`, which must already be in dependency order."""
        ...

    def sequence(self, items: Sequence[WorkItem], plan: SlicePlan) -> tuple[WorkItem, ...]:
        """`items` with the ordering the slices prescribe added to their dependencies."""
        ...
