# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.application.dto import ProjectRecord, RotationCursor
from vibey.domain.engine import EngineId, UnrecognizedEngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, UnrecognizedProvenance
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.infrastructure.db.ledger_repository import to_drafts
from vibey.infrastructure.db.project_repository import PhaseTransitionedDraftBuilder
from vibey.infrastructure.db.rotation_cursor_repository import PostgresRotationCursorRepository

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def test_ledger_repository_to_drafts_refuses_unrecognized_columns() -> None:
    project_id = uuid4()

    bad_phase_event = LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=UnrecognizedPhase("unknown-phase"),
        seq=1,
        kind=EventKind.QUESTION_ASKED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload={"question_id": "q1", "text": "test"},
        digest="digest-1",
    )

    with pytest.raises(
        ValueError, match="carries a phase, engine id or provenance this vibey does not know"
    ):
        to_drafts([bad_phase_event])

    bad_engine_event = LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        seq=2,
        kind=EventKind.QUESTION_ASKED,
        engine_id=UnrecognizedEngineId("unknown-engine"),
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload={"question_id": "q1", "text": "test"},
        digest="digest-2",
    )

    with pytest.raises(
        ValueError, match="carries a phase, engine id or provenance this vibey does not know"
    ):
        to_drafts([bad_engine_event])

    bad_prov_event = LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        seq=3,
        kind=EventKind.QUESTION_ASKED,
        engine_id=EngineId.CLAUDELOOP,
        job_id=None,
        causation_id=None,
        correlation_id=uuid4(),
        provenance=UnrecognizedProvenance("unknown-prov"),
        produced_at=NOW,
        payload={"question_id": "q1", "text": "test"},
        digest="digest-3",
    )

    with pytest.raises(
        ValueError, match="carries a phase, engine id or provenance this vibey does not know"
    ):
        to_drafts([bad_prov_event])


def test_phase_transitioned_draft_builder_refuses_unrecognized_phase() -> None:
    builder = PhaseTransitionedDraftBuilder()
    settled = ProjectRecord(
        project_id=uuid4(),
        name="test-proj",
        repo_path=Path("/tmp/test"),
        phase=UnrecognizedPhase("future_phase"),
        cycle=1,
        max_cycles=3,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    with pytest.raises(
        ValueError, match="which this vibey does not know; it will not ledger a move into it"
    ):
        builder.build(settled, expected=Phase.DESIGN, guard="test")


@pytest.mark.asyncio
async def test_rotation_cursor_repository_refuses_unrecognized_engine_id() -> None:
    repo = PostgresRotationCursorRepository(None)  # type: ignore[arg-type]
    project_id = uuid4()
    bad_cursor = RotationCursor(
        project_id=project_id,
        engine_id=UnrecognizedEngineId("unknown-engine"),  # type: ignore[arg-type]
        current=1,
        order=0,
    )

    with pytest.raises(
        ValueError, match="refusing to write the rotation cursor of engine 'unknown-engine'"
    ):
        PostgresRotationCursorRepository._writable(bad_cursor)

    with pytest.raises(
        ValueError, match="refusing to write the rotation cursor of engine 'unknown-engine'"
    ):
        await repo.upsert(bad_cursor)

    with pytest.raises(
        ValueError, match="refusing to write the rotation cursor of engine 'unknown-engine'"
    ):
        await repo.update_many(project_id, (bad_cursor,))


@pytest.mark.asyncio
async def test_engine_health_repository_refuses_unrecognized_circuit_and_engine() -> None:
    from vibey.application.dto import EngineHealthRecord
    from vibey.domain.circuit import CircuitState, UnrecognizedCircuitState
    from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository

    repo = PostgresEngineHealthRepository(None)  # type: ignore[arg-type]
    project_id = uuid4()

    bad_circuit_record = EngineHealthRecord(
        project_id=project_id,
        engine_id=EngineId.CLAUDELOOP,
        installed=True,
        version="1.0",
        conformance_ok=True,
        conformance_at=NOW,
        auth_ok_at=NOW,
        circuit=UnrecognizedCircuitState("unknown_circuit"),
        capacity_state=None,
        resets_at=None,
        probe_next_at=None,
        probe_attempt=0,
        consecutive_fail=0,
        ewma_failure=0.0,
        cost_usd_cycle=0.0,
        selected_count=0,
    )

    with pytest.raises(ValueError, match="refusing to write unknown circuit"):
        await repo.upsert(bad_circuit_record)

    bad_engine_record = EngineHealthRecord(
        project_id=project_id,
        engine_id=UnrecognizedEngineId("unknown_engine"),
        installed=True,
        version="1.0",
        conformance_ok=True,
        conformance_at=NOW,
        auth_ok_at=NOW,
        circuit=CircuitState.CLOSED,
        capacity_state=None,
        resets_at=None,
        probe_next_at=None,
        probe_attempt=0,
        consecutive_fail=0,
        ewma_failure=0.0,
        cost_usd_cycle=0.0,
        selected_count=0,
    )

    with pytest.raises(ValueError, match="refusing to write health for engine 'unknown_engine'"):
        await repo.upsert(bad_engine_record)
