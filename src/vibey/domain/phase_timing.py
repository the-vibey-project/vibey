# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Phase timing: the measured history any honest estimator needs (issue #88).

Issue #88 asks for time-and-cost-to-launch predictions "derived from the
conductor's own historical phase timings, not vibes". This is the first half
of that: a pure projection that reads one project's ledger and reports, for
every stay in every phase, when it was entered, when it was left, how long it
took, and what it spent. It predicts nothing. A later ``vibey forecast`` slice
consumes it.

**Boundaries.** A visit is opened by a ``PhaseTransitioned`` event and closed
by the next one. ``infrastructure/db/project_repository.py`` writes exactly one
per settled move, filed under the phase and cycle the project moved INTO, so
the event's own ``phase``/``cycle`` name the visit it opens. If the range does
not begin with a transition, the first event opens a visit in its own
``(cycle, phase)`` whose entry was never observed; its duration is a lower
bound and it is never ``measured``. A visit into DONE or ABANDONED stays open
unless the ledger records a move out of it, which is what those phases mean.

**Order is ``seq``, never ``produced_at``.** ``seq`` is assigned by the
database and totally orders a project's events; ``produced_at`` is supplied by
whoever wrote the event (migration 0009), and ``PhaseTransitioned`` in
particular carries database time while other kinds carry a handler's Clock
(see ``PhaseTransitionedDraftBuilder``). The two need not agree. So the
boundaries and their order come from ``seq`` alone, and ``produced_at`` is used
only to measure the distance between two boundaries ``seq`` has already fixed.

**When the clocks disagree with ``seq``** -- a transition whose recorded
``produced_at`` is earlier than the one before it -- the visit between them
reports a ``duration`` of zero and ``clock_skewed=True``, and its raw
``entered_at``/``left_at`` are kept exactly as recorded. Zero rather than the
negative difference, because ``seq`` proves the visit ended after it began and
a negative length is not a length. Zero rather than None, because the visit
did happen and still owns its spend, and a None would read as "still open".
The flag is what keeps the zero honest: a skewed visit is never ``measured``,
so an estimator that takes only measured visits never trains on a clamped
number. The cost is that the next visit, whose entry is that same early
timestamp, reads longer than it was -- the skew moves time between neighbours
rather than destroying it, so the durations of a closed run still telescope to
at least its wall-clock span.

**Spend** is attributed by the event's own ``(cycle, phase)`` tag to the most
recent visit with that tag opened at or before the event's ``seq`` -- not by
position -- so a turn a BUILD job reports after the project has already moved
to REVIEW is still BUILD's money. Spend whose tag names no visit opened by then
lands in ``unattributed`` instead of being dropped, so the visits plus the
unattributed rows always account for every dollar the ledger holds.

The rule for what counts as spend is ``application/budget_source.py``'s
``LedgerBudgetSource`` -- the budget brake -- reproduced event for event as
``LedgerSpendRule``: ``TurnCompleted`` contributes its numeric ``cost_usd``,
``BudgetSpent`` its numeric ``dollars`` and integer ``turns``, anything
non-numeric contributes zero. Reproduced, not imported, because that rule is
inlined in an ``application/`` method and ``domain/`` may not import upward:
the capability gap is that the family had no domain-level spend rule, and
``LedgerSpendRule`` is that rule added where both layers can reach it. The
other half -- ``LedgerBudgetSource`` calling it instead of keeping its own
copy -- is deliberately not done here, to keep this change inside ``domain/``;
it is the unification left open, and the issue #209 lane, which reworks the
cost path, is the natural place for it. Until then
``tests/domain/test_phase_timing.py`` pins the two to the same totals per
cycle, so they cannot drift apart silently.

**Turns are not counted, because the ledger cannot count them.** Engine
translation (``infrastructure/engines/loop_events.py``) maps more than one
engine event to ``TurnCompleted``, so the number of ``TurnCompleted`` events is
an engine-dependent multiple of the number of turns. It is reported under the
name of what it is -- ``turn_completed_events`` -- with ``turn_caveat`` beside
it, and never as ``turns``.
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Final

from vibey.domain.interfaces.phase_timing_interface import (
    LedgerSpendRuleInterface,
    PhaseSpendInterface,
    PhaseTimingProjectionInterface,
)
from vibey.domain.ledger import EventKind, LedgerEvent
from vibey.domain.phase import StoredPhase

TURN_EVENT_CAVEAT: Final = (
    "turn_completed_events counts TurnCompleted ledger events, not turns. "
    "Engine translation (infrastructure/engines/loop_events.py) maps both "
    "chatter.assistant and turn.completed to TurnCompleted for claudeloop and "
    "agyloop, codexloop's turn.failed as well as turn.completed, and every "
    "qwenloop text_delta, so the count overstates real turns by an "
    "engine-dependent factor. Do not present it, or a rate derived from it, "
    "as a number of turns."
)
"""The default ``turn_caveat``. A constructor argument rather than a fixed
string, so the text can follow the translation table when that is fixed
without anyone editing this module (ADR-0018)."""

_NO_DURATION: Final = timedelta(0)


@dataclass(frozen=True, slots=True)
class PhaseSpend:
    """What a span of the ledger spent. See ``PhaseSpendInterface``."""

    dollars: float = 0.0
    turn_completed_events: int = 0
    budget_turns: int = 0

    def plus(self, other: PhaseSpendInterface) -> "PhaseSpend":
        """The sum of two spends. Never mutates either operand."""
        return PhaseSpend(
            dollars=self.dollars + other.dollars,
            turn_completed_events=self.turn_completed_events + other.turn_completed_events,
            budget_turns=self.budget_turns + other.budget_turns,
        )


NO_SPEND: Final = PhaseSpend()
"""The additive identity, and the spend of a visit nothing was charged to."""


class LedgerSpendRule:
    """Which ledger events are spend, and how much. See the module docstring:
    this is ``LedgerBudgetSource``'s rule, and it is public so that class can
    adopt it instead of keeping its own copy."""

    def spend_of(self, event: LedgerEvent) -> PhaseSpend | None:
        """What one event spent, or None if it is not a spend event at all."""
        if event.kind is EventKind.TURN_COMPLETED:
            raw_cost = event.payload.get("cost_usd", 0.0)
            dollars = float(raw_cost) if isinstance(raw_cost, int | float) else 0.0
            return PhaseSpend(dollars=dollars, turn_completed_events=1)
        if event.kind is EventKind.BUDGET_SPENT:
            raw_dollars = event.payload.get("dollars", 0.0)
            raw_turns = event.payload.get("turns", 0)
            return PhaseSpend(
                dollars=float(raw_dollars) if isinstance(raw_dollars, int | float) else 0.0,
                budget_turns=raw_turns if isinstance(raw_turns, int) else 0,
            )
        return None


LEDGER_SPEND_RULE: Final[LedgerSpendRuleInterface] = LedgerSpendRule()
"""The published default rule; annotated so ``mypy --strict`` checks it
against its seam, for the reason ``PHASE_TIMING`` below gives."""


@dataclass(frozen=True, slots=True)
class PhaseVisit:
    """One stay in one phase. See ``PhaseVisitInterface``."""

    cycle: int
    phase: StoredPhase
    entered_seq: int
    entered_at: datetime
    entry_observed: bool
    left_seq: int | None
    left_at: datetime | None
    spend: PhaseSpend

    def __post_init__(self) -> None:
        if (self.left_seq is None) != (self.left_at is None):
            raise ValueError("a visit is left at a seq and a time together, or not at all")

    @property
    def duration(self) -> timedelta | None:
        """``left_at - entered_at``, floored at zero. None while open."""
        if self.left_at is None:
            return None
        return max(self.left_at - self.entered_at, _NO_DURATION)

    @property
    def clock_skewed(self) -> bool:
        """The recorded clocks put the leaving before the entering."""
        return self.left_at is not None and self.left_at < self.entered_at

    @property
    def measured(self) -> bool:
        """Closed, observably entered, and not clock-skewed."""
        return self.left_at is not None and self.entry_observed and not self.clock_skewed


@dataclass(frozen=True, slots=True)
class PhaseTotal:
    """Every visit to one ``(cycle, phase)``. See ``PhaseTotalInterface``."""

    cycle: int
    phase: StoredPhase
    visits: int
    duration: timedelta | None
    measured: bool
    spend: PhaseSpend


@dataclass(frozen=True, slots=True)
class UnattributedSpend:
    """Spend no visit could own. See ``UnattributedSpendInterface``."""

    cycle: int
    phase: StoredPhase
    spend: PhaseSpend


@dataclass(frozen=True, slots=True)
class PhaseTimeline:
    """The projection's result. See ``PhaseTimelineInterface``."""

    visits: tuple[PhaseVisit, ...]
    totals: tuple[PhaseTotal, ...]
    unattributed: tuple[UnattributedSpend, ...]
    turn_caveat: str


class PhaseTimingProjection:
    """Derives a project's phase timeline from its ledger events."""

    def __init__(
        self,
        *,
        spend_rule: LedgerSpendRuleInterface = LEDGER_SPEND_RULE,
        turn_caveat: str = TURN_EVENT_CAVEAT,
    ) -> None:
        self._spend_rule = spend_rule
        self._turn_caveat = turn_caveat

    def project(self, events: Sequence[LedgerEvent]) -> PhaseTimeline:
        """The timeline, with ``seq`` -- never ``produced_at`` -- as the order.

        Raises ``ValueError`` if the events belong to more than one project:
        interleaving two projects' transitions would invent visits neither had.
        """
        ordered = sorted(events, key=lambda event: event.seq)
        self._require_one_project(ordered)

        visits: list[PhaseVisit] = []
        latest: dict[tuple[int, StoredPhase], int] = {}
        unattributed: dict[tuple[int, StoredPhase], PhaseSpend] = {}

        if ordered and ordered[0].kind is not EventKind.PHASE_TRANSITIONED:
            self._open(visits, latest, ordered[0], entry_observed=False)

        for event in ordered:
            if event.kind is EventKind.PHASE_TRANSITIONED:
                if visits:
                    visits[-1] = replace(visits[-1], left_seq=event.seq, left_at=event.produced_at)
                self._open(visits, latest, event, entry_observed=True)
                continue
            spend = self._spend_rule.spend_of(event)
            if spend is None:
                continue
            tag = (event.cycle, event.phase)
            index = latest.get(tag)
            if index is None:
                unattributed[tag] = unattributed.get(tag, NO_SPEND).plus(spend)
            else:
                visits[index] = replace(visits[index], spend=visits[index].spend.plus(spend))

        return PhaseTimeline(
            visits=tuple(visits),
            totals=self._totals(visits),
            unattributed=tuple(
                UnattributedSpend(cycle=cycle, phase=phase, spend=spend)
                for (cycle, phase), spend in unattributed.items()
            ),
            turn_caveat=self._turn_caveat,
        )

    @staticmethod
    def _require_one_project(ordered: Sequence[LedgerEvent]) -> None:
        projects = {event.project_id for event in ordered}
        if len(projects) > 1:
            raise ValueError(
                f"phase timing is per project; the events span {len(projects)} projects"
            )

    @staticmethod
    def _open(
        visits: list[PhaseVisit],
        latest: dict[tuple[int, StoredPhase], int],
        event: LedgerEvent,
        *,
        entry_observed: bool,
    ) -> None:
        latest[(event.cycle, event.phase)] = len(visits)
        visits.append(
            PhaseVisit(
                cycle=event.cycle,
                phase=event.phase,
                entered_seq=event.seq,
                entered_at=event.produced_at,
                entry_observed=entry_observed,
                left_seq=None,
                left_at=None,
                spend=NO_SPEND,
            )
        )

    @staticmethod
    def _totals(visits: Sequence[PhaseVisit]) -> tuple[PhaseTotal, ...]:
        grouped: dict[tuple[int, StoredPhase], list[PhaseVisit]] = {}
        for visit in visits:
            grouped.setdefault((visit.cycle, visit.phase), []).append(visit)
        totals: list[PhaseTotal] = []
        for (cycle, phase), group in grouped.items():
            durations = [visit.duration for visit in group]
            closed = [duration for duration in durations if duration is not None]
            spend = NO_SPEND
            for visit in group:
                spend = spend.plus(visit.spend)
            totals.append(
                PhaseTotal(
                    cycle=cycle,
                    phase=phase,
                    visits=len(group),
                    duration=sum(closed, _NO_DURATION) if len(closed) == len(group) else None,
                    measured=all(visit.measured for visit in group),
                    spend=spend,
                )
            )
        return tuple(totals)


PHASE_TIMING: Final[PhaseTimingProjectionInterface] = PhaseTimingProjection()
"""The published default projection. The annotation is load-bearing: a
``runtime_checkable`` Protocol only checks member names at runtime, so this
assignment is what makes ``mypy --strict`` verify that the projection -- and,
through its return types, every value object above -- satisfies the declared
seam."""
