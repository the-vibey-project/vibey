# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for judging and ordering a BUILD decomposition as a whole."""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable


@runtime_checkable
class PlannedItemInterface(Protocol):
    """What the planner reads of a work item: who it is, what it satisfies,
    and what it waits for."""

    @property
    def item_id(self) -> str: ...

    @property
    def acceptance_ids(self) -> tuple[str, ...]: ...

    @property
    def depends_on(self) -> tuple[str, ...]: ...


@runtime_checkable
class DecompositionPlannerInterface(Protocol):
    """Judges a decomposition whole, then orders it -- never one item at a time,
    because a plan read item by item is only found wrong after part of it has
    been acted on."""

    def violations(
        self,
        items: Sequence[PlannedItemInterface],
        *,
        criteria_ids: Sequence[str],
        walking_skeleton_item_id: str,
    ) -> tuple[str, ...]:
        """Every rule the plan breaks, each named; empty means it can enter BUILD."""
        ...

    def in_dependency_order[ItemT: PlannedItemInterface](
        self, items: Sequence[ItemT]
    ) -> tuple[ItemT, ...]:
        """The same items, every dependency before its dependents, otherwise in
        the order given. Defined only for a plan `violations` accepts."""
        ...
