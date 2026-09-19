# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for decoding a model's decomposition into work items.

Mirrors `vibey/infrastructure/engines/design_json.py` (ADR-0016). Interfaces declare;
they never consume.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from vibey.domain.plan import WorkItem
from vibey.domain.spec import DesignSpec


@runtime_checkable
class WorkPlanDecoderInterface(Protocol):
    def items(self, raw_items: object) -> tuple[WorkItem, ...]:
        """Every item decoded, or ValueError; an empty or non-list input is refused."""
        ...

    def item(self, entry: object) -> WorkItem: ...

    def slug(self, raw: object) -> str:
        """A model-minted id projected onto the worktree id shape, or ValueError."""
        ...

    def spec_json(self, spec: DesignSpec) -> dict[str, object]: ...

    def require_unique(self, items: Sequence[WorkItem]) -> None: ...

    def require_valid(
        self, items: Sequence[WorkItem], criteria_ids: Sequence[str], *, strict: bool = False
    ) -> None:
        """ValueError naming every violation; a plan passes whole or not at all."""
        ...

    def violations(
        self, items: Sequence[WorkItem], criteria_ids: Sequence[str], *, strict: bool = False
    ) -> tuple[str, ...]: ...
