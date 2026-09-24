# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind changing a project's cycle caps (`vibey budget`).

Mirrors `vibey/domain/budget_caps.py` (ADR-0016). Interfaces declare; they never
consume. The domain types the seams are declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime

    from vibey.domain.budget_caps import CapField
    from vibey.domain.ledger import LedgerEvent


@runtime_checkable
class CycleCapsInterface(Protocol):
    """The caps in force for each of a project's cycles. `None` is uncapped."""

    @property
    def max_dollars(self) -> float | None: ...

    @property
    def max_turns(self) -> int | None: ...

    def value_of(self, cap: CapField) -> float | int | None: ...


@runtime_checkable
class CapChangeInterface(Protocol):
    """One cap, from the value it had to the value it has now."""

    @property
    def field(self) -> CapField: ...

    @property
    def old(self) -> float | int | None: ...

    @property
    def new(self) -> float | int | None: ...

    def payload(self, *, by: str, account: str) -> dict[str, object]:
        """The `BudgetCapChanged` event's payload: `field`, `old`, `new`, `by`, `account`."""
        ...


@runtime_checkable
class CapRequestInterface(Protocol):
    """Caps to set to a value, and caps to clear. The two never overlap."""

    @property
    def set_to(self) -> Mapping[CapField, float | int]: ...

    @property
    def clear(self) -> frozenset[CapField]: ...


@runtime_checkable
class CapChangePlannerInterface(Protocol):
    """Refuses what is not a cap, and says what a request changes."""

    def setting(
        self, *, max_dollars: object = None, max_turns: object = None
    ) -> CapRequestInterface:
        """Raises `InvalidBudgetChange` for a value that is not a cap, or for neither."""
        ...

    def clearing(self, caps: Iterable[CapField]) -> CapRequestInterface:
        """Raises `InvalidBudgetChange` when no cap is named."""
        ...

    def plan(
        self, current: CycleCapsInterface, request: CapRequestInterface
    ) -> tuple[CapChangeInterface, ...]:
        """Dollars first; a cap the request would leave as it is is not a change."""
        ...

    def actor(self, label: str | None, *, account: str) -> str:
        """The label a caller named itself by, checked, or else the account."""
        ...


@runtime_checkable
class CapHistoryEntryInterface(Protocol):
    """One recorded change to a cap, as the ledger holds it."""

    @property
    def at(self) -> datetime: ...

    @property
    def by(self) -> str | None: ...

    @property
    def field(self) -> str: ...

    @property
    def old(self) -> object: ...

    @property
    def new(self) -> object: ...


@runtime_checkable
class BudgetCapHistoryInterface(Protocol):
    """Every change to a project's caps, oldest first, from `trusted` ledger events."""

    def entries(self, events: Iterable[LedgerEvent]) -> tuple[CapHistoryEntryInterface, ...]: ...
