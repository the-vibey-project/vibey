# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""How `vibey budget` reads to a person, and the JSON it hands a program -- no database."""

import json
from datetime import UTC, datetime
from uuid import UUID

from vibey.application.dto import BudgetChange, ProjectBudget
from vibey.cli.budget import BudgetPresenter
from vibey.domain.budget import BudgetLedger
from vibey.domain.budget_caps import CapChange, CapField, CapHistoryEntry

PID = UUID("6f1c2a0e-0000-4000-8000-00000000b1d6")
AT = datetime(2026, 9, 24, 15, 2, tzinfo=UTC)
PRESENTER = BudgetPresenter()


def _budget(ledger: BudgetLedger, *history: CapHistoryEntry) -> ProjectBudget:
    return ProjectBudget(project_id=PID, name="greeter", cycle=2, budget=ledger, history=history)


def test_a_cap_set_finer_than_a_cent_is_shown_as_set() -> None:
    lines = PRESENTER.budget(_budget(BudgetLedger(0, 0.0, None, 0.005)))

    assert lines[1] == "  dollars: $0.00 spent this cycle; cap $0.005"


def test_each_cap_reached_is_named() -> None:
    turns = PRESENTER.budget(_budget(BudgetLedger(9, 1.0, 9, 5.0)))
    both = PRESENTER.budget(_budget(BudgetLedger(9, 6.0, 9, 5.0)))

    assert turns[3] == (
        "  The turn cap is reached: the next BUILD session will park a budget_exhausted gate."
    )
    assert both[3] == (
        "  The dollar cap and the turn cap are reached: the next BUILD session will park a "
        "budget_exhausted gate."
    )


def test_the_last_change_is_shown_with_the_count_as_recorded() -> None:
    lines = PRESENTER.budget(
        _budget(
            BudgetLedger(0, 0.0, 40, 15.0),
            CapHistoryEntry(AT, "adam", "max_cycle_dollars", None, 15.0),
            CapHistoryEntry(AT, "vibey-vscode", "max_cycle_turns", 200, 40),
        )
    )
    newer = PRESENTER.budget(
        _budget(
            BudgetLedger(0, 0.0, None, None),
            CapHistoryEntry(AT, None, "max_cycle_minutes", 30, 45),
        )
    )

    assert lines[-1] == (
        "  last change: turn cap 200 -> 40, by vibey-vscode, 2026-09-24 15:02 UTC (2 changes in all)"
    )
    # A cap a newer vibey added, recorded with no name: shown as stored.
    assert (
        newer[-1]
        == "  last change: max_cycle_minutes 30 -> 45, 2026-09-24 15:02 UTC (1 change in all)"
    )


def test_a_stored_dollar_value_that_is_not_a_number_is_shown_as_stored() -> None:
    lines = PRESENTER.budget(
        _budget(
            BudgetLedger(0, 0.0, None, None),
            CapHistoryEntry(AT, "a", "max_cycle_dollars", True, None),
        )
    )

    assert "dollar cap True -> none" in lines[-1]


def test_no_projects_says_how_to_make_one() -> None:
    assert PRESENTER.budgets([]) == [
        "no projects yet; create one with `vibey new <name> --repo <path>`"
    ]
    assert json.loads(PRESENTER.budgets_json([])) == []


def test_the_document_is_the_contract_shape() -> None:
    document = json.loads(
        PRESENTER.budget_json(
            _budget(
                BudgetLedger(41, 3.21, None, 15.0),
                CapHistoryEntry(AT, "adam", "max_cycle_dollars", None, 15.0),
            )
        )
    )

    assert document == {
        "project_id": str(PID),
        "name": "greeter",
        "cycle": 2,
        "caps": {"max_cycle_dollars": 15.0, "max_cycle_turns": None},
        "spend": {"dollars": 3.21, "turns": 41},
        "exhausted": False,
        "history": [
            {
                "at": "2026-09-24T15:02:00+00:00",
                "by": "adam",
                "field": "max_cycle_dollars",
                "old": None,
                "new": 15.0,
            }
        ],
    }


def test_a_change_lists_what_moved_then_the_budget_then_every_parked_job() -> None:
    gates = (
        UUID("00000000-0000-4000-8000-000000000001"),
        UUID("00000000-0000-4000-8000-000000000002"),
    )
    change = BudgetChange(
        after=_budget(BudgetLedger(0, 0.0, None, 30.0)),
        by="vibey-vscode",
        changes=(CapChange(CapField.MAX_CYCLE_DOLLARS, 2.0, 30.0),),
        parked=gates,
    )
    nothing = BudgetChange(after=_budget(BudgetLedger(0, 0.0, None, None)), by="adam")

    lines = PRESENTER.change(change)

    assert lines[:3] == ["Changed by vibey-vscode:", "  dollar cap: $2.00 -> $30.00", ""]
    assert lines[3] == f"greeter ({PID}), cycle 2"
    assert lines[-3:] == [
        "2 jobs are still parked on a budget_exhausted gate. A changed cap applies once the "
        "gate is answered:",
        f"  vibey answer {gates[0]} --raw '{{}}'",
        f"  vibey answer {gates[1]} --raw '{{}}'",
    ]
    assert PRESENTER.change(nothing)[0] == "Nothing changed: the caps were already as asked."
