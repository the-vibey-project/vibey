# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The dashboard derives the visual and deployment decisions from the kinds it knows, and
a `BudgetCapChanged` event is shown in the tail without moving either."""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from vibey.application.dto import ProjectRecord
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.tui.dashboard import build_replay_states, format_event_row


def _event(
    seq: int, kind: EventKind, payload: dict[str, object], project_id: object
) -> LedgerEvent:
    return LedgerEvent(
        seq=seq,
        event_id=uuid4(),
        project_id=project_id,  # type: ignore[arg-type]
        cycle=1,
        phase=Phase.BUILD,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,  # type: ignore[arg-type]
        provenance=Provenance.TRUSTED,
        produced_at=datetime(2026, 9, 24, 12, seq, tzinfo=UTC),
        payload=payload,
        digest=digest_event(payload),
    )


def test_a_cap_change_is_in_the_tail_and_moves_no_decision() -> None:
    project_id = uuid4()
    project = ProjectRecord(
        project_id=project_id,
        name="budget-replay",
        repo_path=Path("/tmp/repo"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    declined = _event(1, EventKind.DEPLOYMENT_DECLINED, {"choice": "local_only"}, project_id)
    change = _event(
        2,
        EventKind.BUDGET_CAP_CHANGED,
        {"field": "max_cycle_dollars", "old": None, "new": 15.0, "by": "adam", "account": "adam"},
        project_id,
    )

    states = build_replay_states(project, [declined, change])

    assert "BudgetCapChanged" in format_event_row(change)
    assert states[-1].deployment_decision == states[-2].deployment_decision == "DECLINED"
    assert states[-1].visual_decision is None
    assert states[-1].ledger_tail[-1] is change
