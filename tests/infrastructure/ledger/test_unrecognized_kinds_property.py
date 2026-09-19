# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""vibey#275, as a property: whatever text a newer vibey puts in `event.kind`, no
reader between the row and the next engine crashes on it, and none loses it.

The chain under test is the production one, minus Postgres: the row mapper every
reader of the `event` table shares, the full ledger written into a receiving
worktree, the budget brake, and the operator's search output. The pure domain
readers have their own property in tests/domain/test_forward_compatible_readers.py.
"""

import asyncio
import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from hypothesis import given, settings
from hypothesis import strategies as st

from vibey.application.budget_source import LedgerBudgetSource
from vibey.cli.ledger_search import LedgerSearchPresenter
from vibey.domain.ledger import (
    EventKind,
    LedgerEvent,
    UnrecognizedEventKind,
    digest_event,
    digest_range,
)
from vibey.domain.ledger_query import LedgerSearchResult
from vibey.infrastructure.db.ledger_repository import EVENT_ROWS, EventRowMapper
from vibey.infrastructure.ledger.full_ledger_writer import write_full_ledger

PROJECT = UUID("6f1c2a0e-0000-4000-8000-000000000275")
T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
KNOWN_VALUES = frozenset(kind.value for kind in EventKind)

_raw_kinds = st.text().filter(lambda value: value not in KNOWN_VALUES)


def _row(seq: int, kind: str, payload: dict[str, object]) -> dict[str, object]:
    """One `event` row as asyncpg hands it over: columns by name, payload as JSON text."""
    return {
        "event_id": uuid4(),
        "project_id": PROJECT,
        "cycle": 1,
        "phase": "build",
        "seq": seq,
        "kind": kind,
        "engine_id": "claudeloop",
        "job_id": None,
        "causation_id": None,
        "correlation_id": PROJECT,
        "provenance": "agent",
        "produced_at": T0,
        "payload": json.dumps(payload),
        "digest": digest_event(payload),
    }


class _Reader:
    def __init__(self, events: tuple[LedgerEvent, ...]) -> None:
        self._events = events

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return self._events


@settings(max_examples=150, deadline=None)
@given(raw=_raw_kinds, cost=st.floats(0, 1000, allow_nan=False))
def test_no_reader_crashes_on_or_drops_an_unrecognized_kind(raw: str, cost: float) -> None:
    spend = {"cost_usd": cost, "dollars": cost, "turns": 7}
    rows = [
        _row(1, EventKind.BUDGET_SPENT.value, {"dollars": 0.5, "turns": 1}),
        _row(2, raw, spend),
        _row(3, EventKind.TURN_COMPLETED.value, {"cost_usd": 0.25}),
    ]

    # The row mapper keeps it, every column intact.
    events = tuple(EVENT_ROWS.to_event(row) for row in rows)  # type: ignore[arg-type]
    stranger = events[1]
    assert stranger.kind == UnrecognizedEventKind(raw)
    assert stranger.event_id == rows[1]["event_id"]
    assert stranger.payload == spend
    assert stranger.digest == rows[1]["digest"]

    # The full ledger handed to the next engine carries it, under its own text.
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "ledger.jsonl"
        ref = write_full_ledger(events, path)
        lines = [json.loads(line) for line in path.read_text().splitlines()]
    assert [line["kind"] for line in lines] == [row["kind"] for row in rows]
    assert ref.event_count == 3
    assert ref.digest == digest_range(events)

    # The budget brake does not count it.
    budget = asyncio.run(LedgerBudgetSource(_Reader(events)).current(PROJECT, 1))
    assert budget.turns_spent == 2
    assert budget.dollars_spent == 0.75

    # The operator can read it, both ways.
    result = LedgerSearchResult(events=events, truncated=False)
    presenter = LedgerSearchPresenter()
    human = presenter.human(result)
    assert human[-1] == "3 matching events"
    machine = json.loads(presenter.machine(PROJECT, result))
    assert machine["events"][1]["kind"] == raw


def test_the_row_mapper_reads_kinds_through_the_parser_it_was_given() -> None:
    class _EverythingIsNew:
        def parse(self, raw: str) -> UnrecognizedEventKind:
            return UnrecognizedEventKind(f"v2:{raw}")

    event = EventRowMapper(kinds=_EverythingIsNew()).to_event(  # type: ignore[arg-type]
        _row(1, "SessionSeeded", {})
    )
    assert event.kind == UnrecognizedEventKind("v2:SessionSeeded")
