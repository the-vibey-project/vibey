# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import json
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from tests.application.fakes import FakeJobRepository
from vibey.application.dto import JobRecord
from vibey.application.ports import Clock
from vibey.application.review_demo_handler import (
    DesignSpecReader,
    PhaseLedger,
    ReviewArtifactWriter,
    ReviewDemoHandler,
)
from vibey.application.worker import Failure, Success
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId
from vibey.domain.integration_evidence import GateRun, ItemEvidence
from vibey.domain.job import FailureClass, JobState
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase
from vibey.domain.spec import AcceptanceCriterion, DesignSpec

NOW = datetime(2026, 8, 15, tzinfo=UTC)


class FixedClock(Clock):
    def now(self) -> datetime:
        return NOW


class FakeSpecRepository(DesignSpecReader):
    def __init__(self, spec: DesignSpec | None = None) -> None:
        self.spec = spec

    async def load(self, project_id: UUID, cycle: int) -> DesignSpec | None:
        return self.spec


class FakeReviewLedger(PhaseLedger):
    def __init__(self, events: Sequence[LedgerEvent] = ()) -> None:
        self._events: list[LedgerEvent] = list(events)
        self.appended: list[tuple[EventKind, Mapping[str, object]]] = []

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(self._events)

    async def append_event(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
    ) -> None:
        self.appended.append((kind, payload))


class FakeReviewArtifactWriter(ReviewArtifactWriter):
    def __init__(self) -> None:
        self.written: dict[str, str] = {}
        self.executables: list[str] = []

    async def write_review_artifacts(
        self,
        project_id: UUID,
        cycle: int,
        artifacts: Mapping[str, str],
        *,
        executable: Sequence[str] = (),
    ) -> Mapping[str, Path]:
        self.written.update(artifacts)
        self.executables.extend(executable)
        return {k: Path(f"/mock/.vibey/runs/{cycle}/review/{k}") for k in artifacts}


def _make_job(
    *,
    kind: str = "review.demo",
    phase: Phase = Phase.REVIEW,
    work_item_id: str | None = None,
    payload: dict[str, object] | None = None,
) -> JobRecord:
    now = NOW
    return JobRecord(
        id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=phase,
        kind=kind,
        state=JobState.READY,
        priority=0,
        work_item_id=work_item_id,
        payload=payload or {},
        requirement={"effort": Effort.HIGH.name.lower()},
        idempotency_key=f"key-{uuid4()}",
        attempts=0,
        max_attempts=7,
        run_after=now,
        lease_owner=None,
        lease_expires_at=None,
        assigned_engine=None,
        last_error=None,
        created_at=now,
        updated_at=now,
    )


async def test_review_demo_handler_rejects_wrong_kind() -> None:
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(),
        ledger=FakeReviewLedger(),
        artifacts=FakeReviewArtifactWriter(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )
    outcome = await handler.handle(_make_job(kind="build.verify"))
    assert isinstance(outcome, Failure)
    assert outcome.failure_class == FailureClass.VIBEY


async def test_review_demo_handler_fails_when_spec_missing() -> None:
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(spec=None),
        ledger=FakeReviewLedger(),
        artifacts=FakeReviewArtifactWriter(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )
    outcome = await handler.handle(_make_job())
    assert isinstance(outcome, Failure)
    assert outcome.failure_class == FailureClass.WORK
    assert "no accepted design spec" in outcome.detail


async def test_review_demo_handler_generates_all_artifacts_and_enqueues_collect() -> None:
    spec = DesignSpec(
        objective="Deliver notes app",
        constraints=(),
        non_goals=(),
        criteria=(
            AcceptanceCriterion(
                criterion_id="AC-1",
                given="a blank notebook",
                when="create note is clicked",
                then="a new note is opened",
                fit="created within 100ms",
            ),
        ),
        nfrs=(),
        walking_skeleton="walking skeleton",
    )
    events = (
        LedgerEvent(
            event_id=uuid4(),
            project_id=uuid4(),
            cycle=1,
            phase=Phase.DESIGN,
            seq=1,
            kind=EventKind.ASSUMPTION_STATED,
            engine_id=EngineId.CLAUDELOOP,
            job_id=uuid4(),
            causation_id=None,
            correlation_id=uuid4(),
            provenance=Provenance.TRUSTED,
            produced_at=NOW,
            payload={"assumption_id": "a-1", "text": "Local sqlite storage"},
            digest="abc",
        ),
    )
    specs = FakeSpecRepository(spec=spec)
    ledger = FakeReviewLedger(events=events)
    artifacts = FakeReviewArtifactWriter()
    jobs = FakeJobRepository()

    handler = ReviewDemoHandler(
        specs=specs,
        ledger=ledger,
        artifacts=artifacts,
        jobs=jobs,
        clock=FixedClock(),
    )

    job = _make_job()
    ledger._events.append(_gate_results_event(job, "wi-1", ("pytest tests/", 0, "3 passed")))
    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert "DEMO.md" in artifacts.written
    assert "run-it.sh" in artifacts.written
    assert "walkthrough.md" in artifacts.written
    assert "deltas.md" in artifacts.written
    assert "evidence/test-report.xml" in artifacts.written
    assert "evidence/coverage.json" in artifacts.written

    # Deltas contains the assumption from ledger
    assert "a-1" in artifacts.written["deltas.md"]
    assert "Local sqlite storage" in artifacts.written["deltas.md"]

    # run-it.sh marked executable
    assert "run-it.sh" in artifacts.executables

    # ARTIFACT_PRODUCED ledger event recorded
    assert any(kind == EventKind.ARTIFACT_PRODUCED for kind, _ in ledger.appended)

    # review.collect job enqueued
    enqueued = list(jobs._jobs.values())
    collect_job = next((j for j in enqueued if j.kind == "review.collect"), None)
    assert collect_job is not None
    assert collect_job.phase == Phase.REVIEW
    assert collect_job.requirement.get("effort") == "high"


class _FixedReviewer:
    def __init__(self, findings: tuple = ()) -> None:  # type: ignore[type-arg]
        self.findings = findings

    async def run_automated_reviews(self, project_id: UUID, cycle: int):  # type: ignore[no-untyped-def]
        return self.findings


def _finding_ledger_event(
    kind: EventKind, finding_id: str, *, automated: bool = True
) -> LedgerEvent:
    payload: dict[str, object] = {"finding_id": finding_id}
    if kind is EventKind.FINDING_RAISED and automated:
        payload["automated"] = True
    return LedgerEvent(
        event_id=uuid4(),
        project_id=uuid4(),
        cycle=1,
        phase=Phase.REVIEW,
        seq=1,
        kind=kind,
        engine_id=None,
        job_id=uuid4(),
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=NOW,
        payload=payload,
        digest="abc",
    )


async def test_fresh_scan_supersedes_stale_automated_findings() -> None:
    """A stale worktree's dead-code finding looped an accepted review
    back into BUILD live: anything still true is re-raised by the fresh
    scan, so everything older is superseded. User findings are never
    touched."""
    spec = DesignSpec(
        objective="x",
        constraints=(),
        non_goals=(),
        criteria=(),
        nfrs=(),
        walking_skeleton="ws",
    )
    events = (
        _finding_ledger_event(EventKind.FINDING_RAISED, "f_code_1_stale111"),
        _finding_ledger_event(EventKind.FINDING_RAISED, "f_code_1_fixed222"),
        _finding_ledger_event(EventKind.FINDING_RESOLVED, "f_code_1_fixed222"),
        _finding_ledger_event(EventKind.FINDING_RAISED, "f_user_1_human333", automated=False),
    )
    ledger = FakeReviewLedger(events=events)
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(spec=spec),
        ledger=ledger,
        artifacts=FakeReviewArtifactWriter(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        automated_reviewer=_FixedReviewer(),
    )

    outcome = await handler.handle(_make_job())

    assert isinstance(outcome, Success)
    resolutions = [
        payload for kind, payload in ledger.appended if kind is EventKind.FINDING_RESOLVED
    ]
    assert [p["finding_id"] for p in resolutions] == ["f_code_1_stale111"]
    assert "superseded" in str(resolutions[0]["resolution"])


def _gate_results_event(
    job: JobRecord, work_item_id: str, *runs: tuple[str, int, str], cycle: int | None = None
) -> LedgerEvent:
    """What a successful build.integrate records for one work item."""
    item = ItemEvidence(
        work_item_id=work_item_id,
        runs=tuple(GateRun(command, code, tail) for command, code, tail in runs),
    )
    payload = item.to_payload(cycle=job.cycle if cycle is None else cycle)
    return LedgerEvent(
        event_id=uuid4(),
        project_id=job.project_id,
        cycle=job.cycle if cycle is None else cycle,
        phase=Phase.BUILD,
        seq=1,
        kind=EventKind.ARTIFACT_PRODUCED,
        engine_id=None,
        job_id=uuid4(),
        causation_id=None,
        correlation_id=uuid4(),
        provenance=Provenance.TRUSTED,
        produced_at=NOW,
        payload=payload,
        digest="abc",
    )


def _notes_spec() -> DesignSpec:
    return DesignSpec(
        objective="Deliver notes app",
        constraints=(),
        non_goals=(),
        criteria=(
            AcceptanceCriterion(
                criterion_id="AC-1",
                given="a blank notebook",
                when="create note is clicked",
                then="a new note is opened",
                fit="created within 100ms",
            ),
        ),
        nfrs=(),
        walking_skeleton="walking skeleton",
    )


async def test_the_reviewer_sees_exactly_what_the_integration_gates_did() -> None:
    """review.demo was enqueued with no payload and showed a hard-coded
    "0 failures" report and 100% green coverage on every REVIEW."""
    job = _make_job()
    ledger = FakeReviewLedger(
        events=(
            _gate_results_event(job, "wi-1", ("pytest tests/", 0, "3 passed")),
            _gate_results_event(job, "wi-2", ("ruff check .", 0, "(no output)")),
            # Another cycle's record never counts.
            _gate_results_event(job, "wi-9", ("make", 0, ""), cycle=job.cycle + 1),
        )
    )
    artifacts = FakeReviewArtifactWriter()
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(spec=_notes_spec()),
        ledger=ledger,
        artifacts=artifacts,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert outcome.result["evidence_measured"] is True
    report = artifacts.written["evidence/test-report.xml"]
    assert 'name="pytest tests/"' in report
    assert 'name="ruff check ."' in report
    assert "wi-9" not in report
    assert 'tests="2" failures="0" skipped="0"' in report
    coverage = json.loads(artifacts.written["evidence/coverage.json"])
    assert coverage["measured"] is False
    assert (
        "2 integration gate run(s) across 2 work item(s); 0 failed."
        in (artifacts.written["DEMO.md"])
    )


async def test_a_payload_can_no_longer_supply_its_own_evidence() -> None:
    """Evidence comes from the ledger only: a job payload is not a measurement."""
    job = _make_job(payload={"test_report": "<xml>passed</xml>", "coverage": '{"coverage": 100}'})
    ledger = FakeReviewLedger(events=(_gate_results_event(job, "wi-1", ("pytest", 0, "ok")),))
    artifacts = FakeReviewArtifactWriter()
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(spec=_notes_spec()),
        ledger=ledger,
        artifacts=artifacts,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    await handler.handle(job)

    assert "<xml>passed</xml>" not in artifacts.written["evidence/test-report.xml"]
    assert '"coverage": 100' not in artifacts.written["evidence/coverage.json"]


async def test_a_cycle_with_no_record_reaches_the_reviewer_marked_unmeasured() -> None:
    """No integrate record is not a pass: every artifact says nothing was measured."""
    job = _make_job()
    artifacts = FakeReviewArtifactWriter()
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(spec=_notes_spec()),
        ledger=FakeReviewLedger(),
        artifacts=artifacts,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert outcome.result["evidence_measured"] is False
    report = artifacts.written["evidence/test-report.xml"]
    assert 'tests="0" failures="0"' in report
    assert "no integration gate evidence was recorded" in report
    assert "Unmeasured" in artifacts.written["DEMO.md"]
    assert "Verified by gate suite" not in artifacts.written["DEMO.md"]


async def test_an_item_that_ran_no_command_is_named_unmeasured() -> None:
    job = _make_job()
    artifacts = FakeReviewArtifactWriter()
    handler = ReviewDemoHandler(
        specs=FakeSpecRepository(spec=_notes_spec()),
        ledger=FakeReviewLedger(
            events=(
                _gate_results_event(job, "wi-1", ("pytest", 0, "ok")),
                _gate_results_event(job, "wi-2"),
            )
        ),
        artifacts=artifacts,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert outcome.result["evidence_measured"] is False
    assert 'skipped="1"' in artifacts.written["evidence/test-report.xml"]
    assert "no verification commands ran for: wi-2" in artifacts.written["DEMO.md"]
