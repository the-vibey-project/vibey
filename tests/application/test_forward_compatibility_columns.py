# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import EngineHealthRecord, JobRecord, PreflightResult
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.engine_selector import EngineSelector
from vibey.application.ports import Clock
from vibey.application.review_demo_handler import (
    DesignSpecReader,
    PhaseLedger,
    ReviewArtifactWriter,
    ReviewDemoHandler,
)
from vibey.domain.capacity import Available
from vibey.domain.circuit import CircuitState, UnrecognizedCircuitState
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId, UnrecognizedEngineId
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.domain.spec import AcceptanceCriterion, DesignSpec

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


class FakeHealthRepo:
    def __init__(self, records: list[EngineHealthRecord]) -> None:
        self.records = {r.engine_id: r for r in records}
        self.upserted: list[EngineHealthRecord] = []

    async def get(self, project_id: UUID, engine_id: str) -> EngineHealthRecord | None:
        for k, v in self.records.items():
            if str(k) == engine_id:
                return v
        return None

    async def list_for_project(self, project_id: UUID) -> tuple[EngineHealthRecord, ...]:
        return tuple(self.records.values())

    async def upsert(self, record: EngineHealthRecord) -> EngineHealthRecord:
        self.records[record.engine_id] = record
        self.upserted.append(record)
        return record


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


@pytest.mark.asyncio
async def test_engine_health_service_preserves_unrecognized_circuits() -> None:
    project_id = uuid4()
    unknown_circuit_record = EngineHealthRecord(
        project_id=project_id,
        engine_id=EngineId.CLAUDELOOP,
        installed=True,
        version="1.0",
        conformance_ok=True,
        conformance_at=NOW,
        auth_ok_at=NOW,
        circuit=UnrecognizedCircuitState("quantum_circuit"),
        capacity_state=None,
        resets_at=None,
        probe_next_at=None,
        probe_attempt=0,
        consecutive_fail=0,
        ewma_failure=0.0,
        cost_usd_cycle=0.0,
        selected_count=0,
    )
    repo = FakeHealthRepo([unknown_circuit_record])
    service = EngineHealthService(repo)  # type: ignore[arg-type]

    preflight = PreflightResult(installed=True, version="1.0", auth_ok=True)

    # 1. record_preflight returns record unmodified (line 108)
    res1 = await service.record_preflight(project_id, EngineId.CLAUDELOOP, preflight)
    assert res1 == unknown_circuit_record

    # 2. update_from_preflight returns record unmodified (line 141)
    res2 = await service.update_from_preflight(
        project_id, EngineId.CLAUDELOOP, preflight, conformance_ok=True
    )
    assert res2 == unknown_circuit_record

    # 3. record_capacity_rejection returns record unmodified (line 176)
    res3 = await service.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, Available())
    assert res3 == unknown_circuit_record

    # 4. record_selection returns record unmodified
    res4 = await service.record_selection(project_id, EngineId.CLAUDELOOP)
    assert res4 == unknown_circuit_record

    # 5. spend and failures never rewrite a row owned by a newer circuit model.
    res5 = await service.record_spend(project_id, EngineId.CLAUDELOOP, 0.1)
    assert res5 == unknown_circuit_record

    res6 = await service.record_failure(project_id, EngineId.CLAUDELOOP)
    assert res6 == unknown_circuit_record

    # 6. record_success returns record unmodified
    res7 = await service.record_success(project_id, EngineId.CLAUDELOOP)
    assert res7 == unknown_circuit_record


@pytest.mark.asyncio
async def test_engine_selector_skips_unrecognized_engines_and_circuits() -> None:
    from vibey.domain.engine import JobRequirement
    from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID

    project_id = uuid4()
    # 1. Unknown engine record (line 122)
    unknown_engine_record = EngineHealthRecord(
        project_id=project_id,
        engine_id=UnrecognizedEngineId("unknown-engine"),
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
    # 2. Known engine but unrecognized circuit state (line 128)
    unknown_circuit_record = EngineHealthRecord(
        project_id=project_id,
        engine_id=EngineId.CODEXLOOP,
        installed=True,
        version="1.0",
        conformance_ok=True,
        conformance_at=NOW,
        auth_ok_at=NOW,
        circuit=UnrecognizedCircuitState("quantum_circuit"),
        capacity_state=None,
        resets_at=None,
        probe_next_at=None,
        probe_attempt=0,
        consecutive_fail=0,
        ewma_failure=0.0,
        cost_usd_cycle=0.0,
        selected_count=0,
    )
    # 3. Valid known engine record
    fresh_auth = datetime.now(UTC)
    valid_record = EngineHealthRecord(
        project_id=project_id,
        engine_id=EngineId.CLAUDELOOP,
        installed=True,
        version="1.0",
        conformance_ok=True,
        conformance_at=NOW,
        auth_ok_at=fresh_auth,
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

    repo = FakeHealthRepo([unknown_engine_record, unknown_circuit_record, valid_record])
    service = EngineHealthService(repo)  # type: ignore[arg-type]

    class FakeCursorRepo:
        async def list_for_project(self, pid: UUID):
            return ()

        async def initialize_for_project(self, pid: UUID, engine_ids):
            return ()

        async def update_many(self, pid: UUID, cursors):
            return ()

    selector = EngineSelector(
        health_service=service,
        cursor_repository=FakeCursorRepo(),  # type: ignore[arg-type]
        descriptors=BY_ENGINE_ID,
    )

    selected, _ = await selector.select_engine(project_id, JobRequirement(effort=Effort.LOW))
    assert selected == EngineId.CLAUDELOOP


@pytest.mark.asyncio
async def test_review_demo_handler_skips_uninterpretable_events() -> None:
    from vibey.application.worker import Success

    spec = DesignSpec(
        objective="Deliver notes app",
        constraints=(),
        non_goals=(),
        criteria=(
            AcceptanceCriterion(
                criterion_id="AC-1",
                given="blank note",
                when="create clicked",
                then="note created",
                fit="under 100ms",
            ),
        ),
        nfrs=(),
        walking_skeleton="walking skeleton",
    )

    class FakeSpecRepo(DesignSpecReader):
        async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None:
            return spec

    class FakeReviewLedger(PhaseLedger):
        def __init__(self) -> None:
            self.appended: list[tuple[UUID, int, UUID, EventKind, dict[str, object]]] = []

        async def append_event(self, project_id, cycle, job_id, kind, payload) -> None:
            self.appended.append((project_id, cycle, job_id, kind, dict(payload)))

        async def all_for_project(self, project_id: UUID):
            return [
                # Uninterpretable event
                LedgerEvent(
                    event_id=uuid4(),
                    project_id=project_id,
                    cycle=1,
                    phase=UnrecognizedPhase("future-phase"),
                    seq=1,
                    kind=EventKind.FINDING_RAISED,
                    engine_id=None,
                    job_id=uuid4(),
                    causation_id=None,
                    correlation_id=uuid4(),
                    provenance=Provenance.AGENT,
                    produced_at=NOW,
                    payload={"finding_id": "f1", "text": "future finding"},
                    digest="d1",
                ),
                # Interpretable event but empty finding_id
                LedgerEvent(
                    event_id=uuid4(),
                    project_id=project_id,
                    cycle=1,
                    phase=Phase.REVIEW,
                    seq=2,
                    kind=EventKind.QUESTION_ASKED,
                    engine_id=None,
                    job_id=uuid4(),
                    causation_id=None,
                    correlation_id=uuid4(),
                    provenance=Provenance.AGENT,
                    produced_at=NOW,
                    payload={},
                    digest="d2",
                ),
                # Automated finding raised and resolved
                LedgerEvent(
                    event_id=uuid4(),
                    project_id=project_id,
                    cycle=1,
                    phase=Phase.REVIEW,
                    seq=3,
                    kind=EventKind.FINDING_RAISED,
                    engine_id=None,
                    job_id=uuid4(),
                    causation_id=None,
                    correlation_id=uuid4(),
                    provenance=Provenance.AGENT,
                    produced_at=NOW,
                    payload={"finding_id": "f2", "automated": True},
                    digest="d3",
                ),
                LedgerEvent(
                    event_id=uuid4(),
                    project_id=project_id,
                    cycle=1,
                    phase=Phase.REVIEW,
                    seq=4,
                    kind=EventKind.FINDING_RESOLVED,
                    engine_id=None,
                    job_id=uuid4(),
                    causation_id=None,
                    correlation_id=uuid4(),
                    provenance=Provenance.AGENT,
                    produced_at=NOW,
                    payload={"finding_id": "f2"},
                    digest="d4",
                ),
                # Automated finding raised but NOT resolved (will be superseded)
                LedgerEvent(
                    event_id=uuid4(),
                    project_id=project_id,
                    cycle=1,
                    phase=Phase.REVIEW,
                    seq=5,
                    kind=EventKind.FINDING_RAISED,
                    engine_id=None,
                    job_id=uuid4(),
                    causation_id=None,
                    correlation_id=uuid4(),
                    provenance=Provenance.AGENT,
                    produced_at=NOW,
                    payload={"finding_id": "f3", "automated": True},
                    digest="d5",
                ),
            ]

    class FakeArtifacts(ReviewArtifactWriter):
        def __init__(self):
            self.written = {}

        async def write_review_artifacts(self, project_id, cycle, artifacts, *, executable=()):
            self.written.update(artifacts)
            return {}

    class FakeReviewer:
        async def run_automated_reviews(self, project_id, cycle):
            return ()

    ledger = FakeReviewLedger()
    handler = ReviewDemoHandler(
        specs=FakeSpecRepo(),
        ledger=ledger,
        artifacts=FakeArtifacts(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        automated_reviewer=FakeReviewer(),  # type: ignore[arg-type]
    )

    job = JobRecord(
        id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=Phase.REVIEW,
        kind="review.demo",
        state=JobState.READY,
        priority=0,
        work_item_id=None,
        payload={},
        requirement={"effort": Effort.HIGH.name.lower()},
        idempotency_key=f"key-{uuid4()}",
        attempts=0,
        max_attempts=3,
        run_after=NOW,
        lease_owner=None,
        lease_expires_at=None,
        assigned_engine=None,
        last_error=None,
        created_at=NOW,
        updated_at=NOW,
    )
    outcome = await handler.handle(job)
    assert isinstance(outcome, Success)
    assert any(
        item[3] is EventKind.FINDING_RESOLVED and item[4]["finding_id"] == "f3"
        for item in ledger.appended
    )


@pytest.mark.asyncio
async def test_enqueue_design_interview_transitions_and_rejects_wrong_phase() -> None:
    from pathlib import Path

    from vibey.application.dto import ProjectRecord
    from vibey.application.project_kickoff import enqueue_design_interview
    from vibey.domain.errors import UnknownProject, WrongPhase

    class FakeProjectStore:
        def __init__(self) -> None:
            self.projects: dict[UUID, ProjectRecord] = {}

        async def get(self, project_id: UUID) -> ProjectRecord | None:
            return self.projects.get(project_id)

        async def transition(self, project_id: UUID, expected: Phase, to: Phase) -> ProjectRecord:
            proj = self.projects[project_id]
            updated = ProjectRecord(
                project_id=proj.project_id,
                name=proj.name,
                repo_path=proj.repo_path,
                phase=to,
                cycle=proj.cycle,
                max_cycles=proj.max_cycles,
                config=proj.config,
                created_at=proj.created_at,
                updated_at=proj.updated_at,
            )
            self.projects[project_id] = updated
            return updated

    store = FakeProjectStore()
    jobs = FakeJobRepository()
    pid = uuid4()

    # 1. Unknown project
    with pytest.raises(UnknownProject):
        await enqueue_design_interview(projects=store, jobs=jobs, project_id=pid)  # type: ignore[arg-type]

    # 2. Project in INTAKE transitions to DESIGN
    proj = ProjectRecord(
        project_id=pid,
        name="test",
        repo_path=Path("/tmp"),
        phase=Phase.INTAKE,
        cycle=1,
        max_cycles=3,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    store.projects[pid] = proj
    job_id = await enqueue_design_interview(projects=store, jobs=jobs, project_id=pid)  # type: ignore[arg-type]
    assert job_id is not None
    assert store.projects[pid].phase == Phase.DESIGN

    # 3. Project already in DESIGN
    job_id2 = await enqueue_design_interview(projects=store, jobs=jobs, project_id=pid)  # type: ignore[arg-type]
    assert job_id2 is not None

    # 4. Project in unrecognized phase raises WrongPhase
    store.projects[pid] = ProjectRecord(
        project_id=pid,
        name="test",
        repo_path=Path("/tmp"),
        phase=UnrecognizedPhase("future-phase"),
        cycle=1,
        max_cycles=3,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    with pytest.raises(WrongPhase):
        await enqueue_design_interview(projects=store, jobs=jobs, project_id=pid)  # type: ignore[arg-type]
