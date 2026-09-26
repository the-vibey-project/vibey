# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""ULTRA: effort without a ceiling (ADR-0063), the pure half.

- **Chosen, never climbed into.** A project runs ULTRA when the latest trusted of its
  `UltraStarted` / `UltraStopped` events is a start. No ladder reaches ULTRA, and an
  ULTRA pass never parks for running long: the attempt ladder is not consulted.
- **"Done" is a checkpoint.** A pass that ends with a done verdict is followed by the
  next pass, numbered one higher, under its own job key, so a replayed pass is answered
  by that key and never runs twice.
- **What stops it.** The operator's Stop (the latest control is `UltraStopped`), and the
  budget brake at a declared cap. Nothing else. A run with no dollar cap needs the
  no-cap declaration (sub-doctrine 8.b as amended): without it the pass waits for a cap.
  `CreditsExhausted` stays a handoff; it is not decided here.
- **The no-cap path's facts.** The phrase a person types, and the measured cost per hour
  of an engine from its recorded spend -- `None`, shown as "unknown", when nothing has
  been measured (8.g).

Only `trusted` events count: an engine's output is mapped onto no ULTRA kind, but a kind
is a string, and a control nobody on the host gave is not a control.
"""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final
from uuid import UUID

from vibey.domain.budget import BudgetLedger
from vibey.domain.effort import Effort
from vibey.domain.job import idempotency_key
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase_timing import LEDGER_SPEND_RULE

NO_CAP_PHRASE: Final = "I accept unlimited spending"
"""What a person types to declare no cap (8.b, ADR-0063 step 2). Matched exactly."""

ULTRA_PAYLOAD_KEY: Final = "ultra_pass"
"""The BUILD job payload key that carries an ULTRA pass's number."""


class UltraVerdict(StrEnum):
    """What the next ULTRA pass does."""

    CONTINUE = "continue"
    OPERATOR_STOP = "operator_stop"
    BUDGET_BRAKE = "budget_brake"
    NEEDS_CAP = "needs_cap"


@dataclass(frozen=True, slots=True)
class UltraPass:
    """One improvement pass of one work item. Passes are numbered from 1."""

    work_item_id: str
    number: int = 1

    def __post_init__(self) -> None:
        if self.number < 1:
            raise ValueError("an ULTRA pass is numbered from 1")

    def next(self) -> "UltraPass":
        return UltraPass(self.work_item_id, self.number + 1)

    def job_key(self, project_id: UUID, cycle: int) -> str:
        """The pass's idempotency key: one job per (project, cycle, item, pass)."""
        return idempotency_key(
            project_id, cycle, "build.implement", f"ultra:{self.work_item_id}:{self.number}"
        )


@dataclass(frozen=True, slots=True)
class UltraState:
    """What the ledger says about a project's ULTRA run."""

    active: bool = False
    no_cap_declared: bool = False


class UltraPolicy:
    """Reads ULTRA's state from a ledger and decides each pass. Pure."""

    def state(self, events: Iterable[LedgerEvent]) -> UltraState:
        active = False
        no_cap = False
        for event in events:
            if event.provenance is not Provenance.TRUSTED:
                continue
            if event.kind is EventKind.ULTRA_STARTED:
                active = True
            elif event.kind is EventKind.ULTRA_STOPPED:
                active = False
            elif event.kind is EventKind.ULTRA_NO_CAP_CHANGED:
                no_cap = event.payload.get("enabled") is True
        return UltraState(active=active, no_cap_declared=no_cap)

    def decide(self, state: UltraState, budget: BudgetLedger) -> UltraVerdict:
        """Stop first, then the brake, then the cap the run needs; else continue."""
        if not state.active:
            return UltraVerdict.OPERATOR_STOP
        if budget.any_exhausted:
            return UltraVerdict.BUDGET_BRAKE
        if budget.max_dollars is None and not state.no_cap_declared:
            return UltraVerdict.NEEDS_CAP
        return UltraVerdict.CONTINUE

    def effort(self, state: UltraState, ladder_effort: Effort) -> Effort:
        """ULTRA while the run is active; otherwise whatever the ladder said."""
        return Effort.ULTRA if state.active else ladder_effort

    def pass_of(self, work_item_id: str, payload: Mapping[str, object]) -> UltraPass:
        raw = payload.get(ULTRA_PAYLOAD_KEY)
        number = raw if isinstance(raw, int) and not isinstance(raw, bool) and raw >= 1 else 1
        return UltraPass(work_item_id, number)

    @staticmethod
    def phrase_matches(typed: str) -> bool:
        return typed.strip() == NO_CAP_PHRASE

    @staticmethod
    def rate_per_hour(events: Iterable[LedgerEvent], engine_id: str | None = None) -> float | None:
        """Measured dollars per hour: recorded spend over the span it was recorded in,
        for one engine or all. `None` when nothing was measured or the span is empty."""
        dollars = 0.0
        first = last = None
        for event in events:
            if engine_id is not None and str(event.engine_id) != engine_id:
                continue
            spend = LEDGER_SPEND_RULE.spend_of(event)
            if spend is None or spend.dollars <= 0:
                continue
            dollars += spend.dollars
            first = event.produced_at if first is None else min(first, event.produced_at)
            last = event.produced_at if last is None else max(last, event.produced_at)
        if first is None or last is None or last <= first:
            return None
        return dollars / ((last - first).total_seconds() / 3600)


ULTRA_POLICY: Final = UltraPolicy()
