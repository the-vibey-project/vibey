# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for checking that a plan's verification commands name real files.

Mirrors `vibey/domain/plan_references.py` (ADR-0016). Interfaces declare; they never
consume. The domain types the seam is declared over are imported under TYPE_CHECKING
only.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from vibey.domain.plan_references import FileReference, UnresolvedReference


@runtime_checkable
class VerificationCommandsInterface(Protocol):
    """What the checker reads of an item's verification: the commands, in order."""

    @property
    def commands(self) -> tuple[str, ...]: ...


@runtime_checkable
class ReferencingItemInterface(Protocol):
    """What the checker reads of a work item: who it is, what it waits for, what it
    says it will create, and the commands that verify it."""

    @property
    def item_id(self) -> str: ...

    @property
    def depends_on(self) -> tuple[str, ...]: ...

    @property
    def files_touched_hint(self) -> tuple[str, ...]: ...

    @property
    def verification(self) -> VerificationCommandsInterface: ...


@runtime_checkable
class PlanReferenceCheckerInterface(Protocol):
    """Finds the files a plan's verification runs or reads that nothing provides."""

    def references(self, command: str) -> tuple[FileReference, ...]:
        """The checkout files one command executes or reads, in order, and the ones it
        creates -- each classified; an unparseable command names none."""
        ...

    def unresolved(
        self,
        items: Sequence[ReferencingItemInterface],
        *,
        exists: Callable[[str], bool],
    ) -> tuple[UnresolvedReference, ...]:
        """Every executed or read file that is neither in the checkout (`exists`) nor
        created by the item itself, an item it depends on, or an earlier command."""
        ...

    def violations(
        self,
        items: Sequence[ReferencingItemInterface],
        *,
        exists: Callable[[str], bool],
    ) -> tuple[str, ...]:
        """`unresolved`, one sentence per item naming every missing path; empty is sound."""
        ...
