# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""LedgerBudgetSource: cycle spend summed from TURN_COMPLETED cost_usd
(what engines actually write -- the greeter4 live run proved BUDGET_SPENT
events carry no dollars in production) plus explicit BUDGET_SPENT."""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.interfaces import LedgerBudgetSourceInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase

NOW = datetime(2026, 8, 19, tzinfo=UTC)


def _event(cycle: int, kind: EventKind, payload: dict[str, object]) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=cycle,
        phase=Phase.BUILD,
        seq=1,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload=payload,
        digest=digest_event(payload),
    )


class _Reader:
    def __init__(self, events) -> None:  # type: ignore[no-untyped-def]
        self._events = events

    async def all_for_project(self, project_id: UUID):  # type: ignore[no-untyped-def]
        return tuple(self._events)


async def test_sums_only_this_cycles_budget_events_and_tolerates_junk() -> None:
    events = [
        _event(1, EventKind.BUDGET_SPENT, {"dollars": 0.25, "turns": 3}),
        _event(1, EventKind.BUDGET_SPENT, {"dollars": 1.75, "turns": 2}),
        # Other cycles, other kinds, and corrupt payloads never count.
        _event(2, EventKind.BUDGET_SPENT, {"dollars": 99.0, "turns": 99}),
        _event(2, EventKind.TURN_COMPLETED, {"cost_usd": 99.0}),
        _event(1, EventKind.FINDING_RAISED, {"cost_usd": 50.0}),
        _event(1, EventKind.BUDGET_SPENT, {"dollars": "bad", "turns": "bad"}),
    ]
    source = LedgerBudgetSource(_Reader(events), max_dollars=10.0, max_turns=100)

    budget = await source.current(uuid4(), 1)

    assert budget.dollars_spent == 2.0
    assert budget.turns_spent == 5
    assert budget.max_dollars == 10.0
    assert budget.max_turns == 100
    assert budget.any_exhausted is False


async def test_turn_completed_events_carry_the_real_spend() -> None:
    # Production shape: engines write cost on TURN_COMPLETED, while the
    # translated BUDGET_SPENT capacity chatter has no dollars at all.
    events = [
        _event(1, EventKind.TURN_COMPLETED, {"verdict": "Done", "cost_usd": 1.5}),
        _event(1, EventKind.TURN_COMPLETED, {"verdict": "Done", "cost_usd": 2.25}),
        # A turn whose engine reports no cost (agyloop) still counts as a turn.
        _event(1, EventKind.TURN_COMPLETED, {"verdict": "Done"}),
        # A corrupt cost never counts as dollars, but the turn still does.
        _event(1, EventKind.TURN_COMPLETED, {"cost_usd": "bad"}),
        _event(1, EventKind.BUDGET_SPENT, {"source": "utilization", "headroom": None}),
    ]
    source = LedgerBudgetSource(_Reader(events), max_dollars=3.0, max_turns=100)

    budget = await source.current(uuid4(), 1)

    assert budget.dollars_spent == 3.75
    assert budget.turns_spent == 4
    assert budget.any_exhausted is True


async def test_uncapped_source_never_reports_exhaustion() -> None:
    events = [_event(1, EventKind.BUDGET_SPENT, {"dollars": 1000.0, "turns": 9999})]
    source = LedgerBudgetSource(_Reader(events))

    budget = await source.current(uuid4(), 1)

    assert budget.any_exhausted is False
    assert budget.max_dollars is None and budget.max_turns is None


# ── caps_from_config: the one parser the brake and `vibey cost` share (#210) ──


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        # Both keys, as `vibey new --max-cycle-dollars/--max-cycle-turns` writes them.
        ({"max_cycle_dollars": 12.5, "max_cycle_turns": 40}, (12.5, 40)),
        # Neither key: uncapped, never a made-up default.
        ({}, (None, None)),
        # An integer dollar cap (the operator's spec can carry one) is a float cap.
        ({"max_cycle_dollars": 25}, (25.0, None)),
        ({"max_cycle_turns": 7}, (None, 7)),
        # isinstance(True, int) holds, so without the bool guard `true` was a
        # one-turn cap and a one-dollar cap.
        ({"max_cycle_dollars": True, "max_cycle_turns": True}, (None, None)),
        ({"max_cycle_dollars": False, "max_cycle_turns": False}, (None, None)),
        # Not numbers, or a fractional turn count: no cap rather than a guess.
        ({"max_cycle_dollars": "10", "max_cycle_turns": 2.5}, (None, None)),
        # The legacy `budget` table that `vibey cost` used to print from is
        # enforced by nothing, so it is not a cap.
        (
            {"budget": {"max_dollars_per_cycle": 40.0, "max_dollars_total": 250.0}},
            (None, None),
        ),
    ],
    ids=[
        "both",
        "neither",
        "int-dollars",
        "turns-only",
        "bool-true-rejected",
        "bool-false-rejected",
        "non-numeric-rejected",
        "legacy-budget-key-ignored",
    ],
)
def test_caps_from_config(
    config: dict[str, object], expected: tuple[float | None, int | None]
) -> None:
    caps = LedgerBudgetSource.caps_from_config(config)

    assert caps == expected
    max_dollars, _ = caps
    assert max_dollars is None or type(max_dollars) is float


def test_ledger_budget_source_satisfies_its_declared_interface() -> None:
    assert isinstance(LedgerBudgetSource(_Reader([])), LedgerBudgetSourceInterface)
