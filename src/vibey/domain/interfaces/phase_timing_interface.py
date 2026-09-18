# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for the phase-timing projection: how long each phase visit
took and what it spent, measured from the ledger rather than estimated.

These seams name the ledger's own vocabulary (``LedgerEvent``, ``Phase``) and
nothing that consumes them, the same way ``application/interfaces/ledger.py``
names ``LedgerEvent``. The value objects are declared here as read-only
Protocols so a consumer -- the forecast slice of issue #88 -- can depend on
the shape without depending on ``domain/phase_timing.py``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.domain.phase import Phase

if TYPE_CHECKING:
    from vibey.domain.ledger import LedgerEvent


@runtime_checkable
class PhaseSpendInterface(Protocol):
    """What a span of the ledger spent, by the budget brake's own rule."""

    @property
    def dollars(self) -> float:
        """``TurnCompleted.cost_usd`` plus ``BudgetSpent.dollars``."""
        ...

    @property
    def turn_completed_events(self) -> int:
        """How many ``TurnCompleted`` events landed here. NOT a turn count:
        see ``PhaseTimelineInterface.turn_caveat``."""
        ...

    @property
    def budget_turns(self) -> int:
        """The ``turns`` explicitly reported on ``BudgetSpent`` events."""
        ...

    def plus(self, other: PhaseSpendInterface) -> PhaseSpendInterface:
        """The sum of two spends. Never mutates either operand."""
        ...


@runtime_checkable
class LedgerSpendRuleInterface(Protocol):
    """Which ledger events are spend, and how much each one spent."""

    def spend_of(self, event: LedgerEvent) -> PhaseSpendInterface | None:
        """What one event spent, or None if it is not a spend event at all."""
        ...


@runtime_checkable
class PhaseVisitInterface(Protocol):
    """One stay in one phase: from the transition that entered it to the
    transition that left it, both located by ``seq``."""

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> Phase: ...

    @property
    def entered_seq(self) -> int: ...

    @property
    def entered_at(self) -> datetime:
        """``produced_at`` of the event that opened the visit, as recorded."""
        ...

    @property
    def entry_observed(self) -> bool:
        """False when no ``PhaseTransitioned`` opened this visit -- the range
        began inside it -- so its duration is only a lower bound."""
        ...

    @property
    def left_seq(self) -> int | None: ...

    @property
    def left_at(self) -> datetime | None:
        """``produced_at`` of the transition that left, as recorded. None while open."""
        ...

    @property
    def duration(self) -> timedelta | None:
        """``left_at - entered_at``, floored at zero. None while open."""
        ...

    @property
    def clock_skewed(self) -> bool:
        """True when the recorded ``left_at`` is earlier than ``entered_at``
        although ``seq`` says the leaving came after; ``duration`` is then
        zero, not the negative difference."""
        ...

    @property
    def measured(self) -> bool:
        """Closed, entered by an observed transition, and not clock-skewed:
        the only visits whose duration an estimator may take at face value."""
        ...

    @property
    def spend(self) -> PhaseSpendInterface: ...


@runtime_checkable
class PhaseTotalInterface(Protocol):
    """Every visit to one ``(cycle, phase)``, rolled up. A phase can be
    visited more than once in a cycle (a deploy-review routing back to
    DESIGN, a DEPLOY_EXECUTE retry), so this is a sum, not one visit."""

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> Phase: ...

    @property
    def visits(self) -> int: ...

    @property
    def duration(self) -> timedelta | None:
        """The summed visit durations. None while any of the visits is open."""
        ...

    @property
    def measured(self) -> bool:
        """True only when every visit rolled up here is ``measured``."""
        ...

    @property
    def spend(self) -> PhaseSpendInterface: ...


@runtime_checkable
class UnattributedSpendInterface(Protocol):
    """Spend whose ``(cycle, phase)`` no visit had opened by its ``seq``.
    Reported rather than dropped, so every dollar is accounted for."""

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> Phase: ...

    @property
    def spend(self) -> PhaseSpendInterface: ...


@runtime_checkable
class PhaseTimelineInterface(Protocol):
    """The projection's result for one project."""

    @property
    def visits(self) -> tuple[PhaseVisitInterface, ...]:
        """Every visit, in ``seq`` order."""
        ...

    @property
    def totals(self) -> tuple[PhaseTotalInterface, ...]:
        """One row per ``(cycle, phase)``, in order of first entry."""
        ...

    @property
    def unattributed(self) -> tuple[UnattributedSpendInterface, ...]: ...

    @property
    def turn_caveat(self) -> str:
        """Why ``turn_completed_events`` must not be read as a turn count."""
        ...


@runtime_checkable
class PhaseTimingProjectionInterface(Protocol):
    """Derives the phase timeline from one project's ledger events. Pure:
    no clock is read, so an open visit stays open rather than being timed
    against "now" -- a caller that wants elapsed time supplies its own now."""

    def project(self, events: Sequence[LedgerEvent]) -> PhaseTimelineInterface:
        """The timeline, with ``seq`` -- never ``produced_at`` -- as the order."""
        ...
