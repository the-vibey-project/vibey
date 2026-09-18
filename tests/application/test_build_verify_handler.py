# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from vibey.application.build_verify_handler import (
    BuildVerifyHandler,
    GateResult,
    VerifyIndependencePolicy,
)
from vibey.application.dto import EngineEvent
from vibey.application.worker import Defer, Failure, Success
from vibey.domain.engine import EngineId
from vibey.domain.job import FailureClass
from vibey.infrastructure.engines.descriptors import CLAUDELOOP, CODEXLOOP
from vibey.infrastructure.engines.scripted import ScriptedEngine


class FakeWorktrees:
    def __init__(self, path: Path) -> None:
        self._path = path

    def path_for(self, item_id: str) -> Path:
        return self._path


class FakeGateRunner:
    def __init__(self, *, returncode: int = 0, stderr: str = "") -> None:
        self.returncode = returncode
        self.stderr = stderr
        self.calls: list[tuple[str, ...]] = []

    async def run(self, argv: tuple[str, ...], *, cwd: Path) -> GateResult:
        self.calls.append(argv)
        return GateResult(self.returncode, "", self.stderr)


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 8, 19, tzinfo=UTC)


class FakeLedger:
    def __init__(self) -> None:
        self.recorded: list[EngineEvent] = []
        self.correlation_ids: list[UUID] = []
        self.causation_ids: list[UUID | None] = []

    async def record(  # type: ignore[no-untyped-def]
        self, *, project_id, cycle, job_id, engine_id, correlation_id, event, causation_id=None
    ):
        self.recorded.append(event)
        self.correlation_ids.append(correlation_id)
        self.causation_ids.append(causation_id)


def _job(**overrides: object):  # type: ignore[no-untyped-def]
    job = replace(
        make_job(uuid4()),
        kind="build.verify",
        work_item_id="item-1",
        payload={"verification": {"commands": ("pytest",), "criteria_checked": ("AC-1",)}},
        requirement={"implementer_engine_id": "codexloop"},
    )
    return replace(job, **overrides) if overrides else job


async def test_successful_verify_runs_gates_reviews_the_diff_and_enqueues_integrate(
    tmp_path: Path,
) -> None:
    reviewer = ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    gates = FakeGateRunner()
    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=gates,
        reviewer=reviewer,
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
    )

    job = _job()
    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert outcome.result == {
        "work_item_id": "item-1",
        "gates_run": 1,
        "independent_review": True,
    }
    assert gates.calls[0] == ("pytest",)
    assert gates.calls[-1] == ("git", "diff", "HEAD")
    assert any(event.kind == "VerdictRendered" for event in ledger.recorded)

    enqueued = await jobs.claim(job.project_id, owner="t", lease=timedelta(seconds=5))
    assert enqueued is not None
    assert enqueued.kind == "build.integrate"
    assert enqueued.work_item_id == "item-1"


async def test_rejects_wrong_kind_and_missing_work_item_id(tmp_path: Path) -> None:
    reviewer = ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=reviewer,
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    wrong_kind = replace(make_job(uuid4()), kind="build.implement")
    assert await handler.handle(wrong_kind) == Failure(
        FailureClass.VIBEY, "expected build.verify job"
    )
    missing_item = replace(make_job(uuid4()), kind="build.verify", work_item_id=None)
    assert await handler.handle(missing_item) == Failure(
        FailureClass.VIBEY, "build.verify job is missing work_item_id"
    )


async def test_rejects_a_reviewer_that_matches_the_implementer(tmp_path: Path) -> None:
    reviewer = ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=reviewer,
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    job = _job(requirement={"implementer_engine_id": "claudeloop"})
    outcome = await handler.handle(job)

    assert outcome == Failure(FailureClass.VIBEY, "verifier must differ from the implementer")


async def test_a_one_engine_pool_verifies_its_own_work_and_says_so(tmp_path: Path) -> None:
    """The wave-0 blocker: with only one engine configured there is nobody
    else to review, and refusing meant BUILD never finished. The review is
    allowed -- and the weakened independence goes into the ledger as a
    decision and into the job result, so nobody has to guess."""
    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine"),
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
        independence=VerifyIndependencePolicy(
            pool=frozenset({EngineId.CLAUDELOOP}), clock=FixedClock()
        ),
    )

    job = _job(requirement={"implementer_engine_id": "claudeloop"})
    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert outcome.result == {
        "work_item_id": "item-1",
        "gates_run": 1,
        "independent_review": False,
    }
    (decision,) = [e for e in ledger.recorded if e.kind == "DecisionRecorded"]
    # Derived from the work item, not minted: a replayed verify job
    # restates this decision instead of growing a new one per attempt.
    assert decision.payload["decision_id"] == "d_verify_independence_item-1"
    assert decision.payload["independent_review"] is False
    assert decision.payload["pool"] == ["claudeloop"]
    assert "claudeloop" in str(decision.payload["title"])
    assert decision.at == datetime(2026, 8, 19, tzinfo=UTC)
    # The work still went all the way through.
    enqueued = await jobs.claim(job.project_id, owner="t", lease=timedelta(seconds=5))
    assert enqueued is not None
    assert enqueued.kind == "build.integrate"


async def test_a_pool_with_a_second_engine_still_rejects_a_self_review(tmp_path: Path) -> None:
    """The independence rule is untouched wherever it can be honored."""
    ledger = FakeLedger()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine"),
        ledger=ledger,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        independence=VerifyIndependencePolicy(
            pool=frozenset({EngineId.CLAUDELOOP, EngineId.CODEXLOOP}), clock=FixedClock()
        ),
    )

    outcome = await handler.handle(_job(requirement={"implementer_engine_id": "claudeloop"}))

    assert outcome == Failure(FailureClass.VIBEY, "verifier must differ from the implementer")
    assert ledger.recorded == []


async def test_a_rotated_reviewer_records_no_waiver(tmp_path: Path) -> None:
    """A solo-pool policy must not make every verify look non-independent:
    the waiver only ever fires when the reviewer *is* the implementer."""
    ledger = FakeLedger()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine"),
        ledger=ledger,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        independence=VerifyIndependencePolicy(
            pool=frozenset({EngineId.CLAUDELOOP}), clock=FixedClock()
        ),
    )

    outcome = await handler.handle(_job())

    assert isinstance(outcome, Success)
    assert outcome.result["independent_review"] is True
    assert [e for e in ledger.recorded if e.kind == "DecisionRecorded"] == []


async def test_a_failing_gate_command_fails_as_work(tmp_path: Path) -> None:
    reviewer = ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    gates = FakeGateRunner(returncode=1, stderr="assertion failed")
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=gates,
        reviewer=reviewer,
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    outcome = await handler.handle(_job())

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK
    assert "pytest" in outcome.detail
    assert "assertion failed" in outcome.detail
    assert gates.calls == [("pytest",)]  # git diff never runs after a gate failure


async def test_no_criteria_checked_fails_as_work(tmp_path: Path) -> None:
    reviewer = ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine")
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=reviewer,
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    job = _job(payload={"verification": {"commands": (), "criteria_checked": ()}})
    outcome = await handler.handle(job)

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK
    assert "no acceptance criteria" in outcome.detail


async def test_reviewer_rejection_fails_as_work(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    reviewer = ScriptedEngine(
        descriptor=CODEXLOOP,
        base_dir=tmp_path / "engine",
        script=[{"kind": "SessionSeeded", "at": now, "payload": {"seed_digest": "d1"}}],
    )
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=reviewer,
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    job = _job(requirement={"implementer_engine_id": "claudeloop"})
    outcome = await handler.handle(job)

    assert outcome == Failure(FailureClass.WORK, "diff review did not approve this work item")


@pytest.mark.parametrize(
    ("exit_code", "failure_class"),
    [(137, FailureClass.ENGINE), (-9, FailureClass.ENGINE), (1, FailureClass.WORK)],
)
async def test_a_reviewer_that_died_is_the_engines_failure_not_the_works(
    tmp_path: Path, exit_code: int, failure_class: FailureClass
) -> None:
    """#209: a reviewer killed mid-review used to fail the item as WORK --
    blaming the diff -- and never counted against the reviewer's circuit."""
    now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    reviewer = ScriptedEngine(
        descriptor=CODEXLOOP,
        base_dir=tmp_path / "engine",
        script=[{"kind": "SessionSeeded", "at": now, "payload": {"seed_digest": "d1"}}],
        exit_code_script=[exit_code],
    )
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=reviewer,
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    outcome = await handler.handle(_job(requirement={"implementer_engine_id": "claudeloop"}))

    assert outcome == Failure(
        failure_class, f"diff review did not approve this work item (exit code {exit_code})"
    )


def test_gate_output_tail_prefers_both_streams_and_labels_stdout() -> None:
    """pytest prints the actual failure to stdout; stderr often carries
    only warnings. Both must appear (tail-capped), or the operator sees a
    deprecation warning and no failure -- caught live."""
    from vibey.application.build_verify_handler import gate_output_tail

    both = gate_output_tail(GateResult(1, "FAILED test_x - assert 1 == 0", "some warning"))
    assert "some warning" in both
    assert "[stdout] FAILED test_x" in both

    stdout_only = gate_output_tail(GateResult(1, "FAILED test_y", ""))
    assert stdout_only == "[stdout] FAILED test_y"

    stderr_only = gate_output_tail(GateResult(1, "", "boom"))
    assert stderr_only == "boom"

    silent = gate_output_tail(GateResult(1, "", ""))
    assert silent == "(no output)"

    capped = gate_output_tail(GateResult(1, "x" * 5000, ""), limit=100)
    assert len(capped) <= 120


# ── the verify repair loop ───────────────────────────────────────────────────


def _repair_policy(events: list) -> "VerifyRepairPolicy":  # type: ignore[no-untyped-def]  # noqa: F821
    from datetime import UTC, datetime, timedelta

    from vibey.application.build_verify_handler import VerifyRepairPolicy

    class _Reader:
        async def all_for_project(self, project_id):  # type: ignore[no-untyped-def]
            return tuple(events)

    class _Clock:
        def now(self):  # type: ignore[no-untyped-def]
            return datetime(2026, 8, 19, tzinfo=UTC)

    return VerifyRepairPolicy(
        ledger_reader=_Reader(), clock=_Clock(), backoff=timedelta(minutes=10)
    )


def _finding_event(cycle: int, kind: "EventKind", finding_id: str):  # type: ignore[no-untyped-def]  # noqa: F821
    from uuid import uuid4 as _uuid4

    from vibey.domain.ledger import LedgerEvent, Provenance, digest_event
    from vibey.domain.phase import Phase as _Phase

    payload = {"finding_id": finding_id}
    return LedgerEvent(
        event_id=_uuid4(),
        project_id=_uuid4(),
        cycle=cycle,
        phase=_Phase.BUILD,
        seq=1,
        kind=kind,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=_uuid4(),
        provenance=Provenance.AGENT,
        produced_at=datetime(2026, 8, 19, tzinfo=UTC),
        payload=payload,
        digest=digest_event(payload),
    )


async def test_first_gate_failure_raises_a_finding_and_enqueues_a_repair(tmp_path: Path) -> None:
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(returncode=1, stderr="warning only"),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "r"),
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
        repair=_repair_policy([]),
    )

    outcome = await handler.handle(_job())

    from vibey.application.worker import Defer

    assert isinstance(outcome, Defer)
    assert outcome.retry_at == _dt(2026, 8, 19, tzinfo=_UTC) + _td(minutes=10)
    assert "repair" in outcome.detail

    (raised,) = [e for e in ledger.recorded if e.kind == "FindingRaised"]
    finding_id = str(raised.payload["finding_id"])
    assert finding_id.startswith("f_verify_item-1_")

    repair = next(iter(jobs._jobs.values()))
    assert repair.kind == "build.implement"
    assert repair.work_item_id == "item-1"
    assert repair.payload["repair_finding_id"] == finding_id
    assert "warning only" in str(repair.payload["repair_detail"])


async def test_gate_failure_with_a_repair_in_flight_only_defers(tmp_path: Path) -> None:
    from vibey.application.worker import Defer
    from vibey.domain.ledger import EventKind

    job = _job()
    open_finding = _finding_event(job.cycle, EventKind.FINDING_RAISED, "f_verify_item-1_aaaa1111")
    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(returncode=1),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "r"),
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
        repair=_repair_policy([open_finding]),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Defer)
    assert "in flight" in outcome.detail
    assert ledger.recorded == []
    assert jobs._jobs == {}


async def test_exhausted_repair_rounds_park_for_a_human(tmp_path: Path) -> None:
    from vibey.application.worker import Park
    from vibey.domain.ledger import EventKind

    job = _job()
    history = []
    for index in range(3):
        fid = f"f_verify_item-1_{index:08d}"
        history.append(_finding_event(job.cycle, EventKind.FINDING_RAISED, fid))
        history.append(_finding_event(job.cycle, EventKind.FINDING_RESOLVED, fid))
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(returncode=1),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "r"),
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        repair=_repair_policy(history),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Park)
    assert outcome.request.kind == "verify_repair_exhausted"


async def test_success_resolves_this_items_open_findings(tmp_path: Path) -> None:
    from vibey.domain.ledger import EventKind

    job = _job()
    events = [
        _finding_event(job.cycle, EventKind.FINDING_RAISED, "f_verify_item-1_11111111"),
        _finding_event(job.cycle, EventKind.FINDING_RAISED, "f_verify_item-1_22222222"),
        _finding_event(job.cycle, EventKind.FINDING_RESOLVED, "f_verify_item-1_11111111"),
        # A different item's and a different cycle's findings stay alone.
        _finding_event(job.cycle, EventKind.FINDING_RAISED, "f_verify_other_33333333"),
        _finding_event(job.cycle + 1, EventKind.FINDING_RAISED, "f_verify_item-1_44444444"),
        # A non-finding event that happens to carry a matching id is noise.
        _finding_event(job.cycle, EventKind.DECISION_RECORDED, "f_verify_item-1_55555555"),
    ]
    ledger = FakeLedger()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "r"),
        ledger=ledger,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        repair=_repair_policy(events),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    resolutions = [e for e in ledger.recorded if e.kind == "FindingResolved"]
    assert [e.payload["finding_id"] for e in resolutions] == ["f_verify_item-1_22222222"]


async def test_without_a_repair_policy_gate_failure_stays_a_plain_failure(
    tmp_path: Path,
) -> None:
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(returncode=1, stderr="boom"),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "r"),
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
    )

    outcome = await handler.handle(_job())

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK


async def test_an_answered_gate_can_grant_more_repair_rounds(tmp_path: Path) -> None:
    """The exhausted park was a dead end: answering un-parked the job,
    the bound re-tripped, and it parked again forever. A max_rounds grant
    in the answer raises the bound."""
    from datetime import UTC as _UTC
    from datetime import datetime as _dt
    from datetime import timedelta as _td

    from tests.application.fakes import FakeHumanGateRepository
    from vibey.application.build_verify_handler import VerifyRepairPolicy
    from vibey.application.worker import Defer, Park
    from vibey.domain.ledger import EventKind

    job = _job()
    history = []
    for index in range(3):
        fid = f"f_verify_item-1_{index:08d}"
        history.append(_finding_event(job.cycle, EventKind.FINDING_RAISED, fid))
        history.append(_finding_event(job.cycle, EventKind.FINDING_RESOLVED, fid))

    class _Reader:
        async def all_for_project(self, project_id):  # type: ignore[no-untyped-def]
            return tuple(history)

    class _Clock:
        def now(self):  # type: ignore[no-untyped-def]
            return _dt(2026, 8, 19, tzinfo=_UTC)

    gates = FakeHumanGateRepository()
    policy = VerifyRepairPolicy(
        ledger_reader=_Reader(), clock=_Clock(), backoff=_td(minutes=10), gates=gates
    )

    def _handler_with(policy):  # type: ignore[no-untyped-def]
        return BuildVerifyHandler(
            worktrees=FakeWorktrees(tmp_path),
            gates=FakeGateRunner(returncode=1),
            reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "r"),
            ledger=FakeLedger(),
            jobs=FakeJobRepository(),
            clock=FixedClock(),
            repair=policy,
        )

    # Without a grant: parks, and the prompt advertises the contract.
    parked = await _handler_with(policy).handle(job)
    assert isinstance(parked, Park)
    assert '"max_rounds"' in parked.request.prompt

    # The human answers the raised gate with a grant; the retry proceeds.
    gate = await gates.raise_gate(job.project_id, job.id, parked.request)
    await gates.answer(gate.gate_id, answer={"max_rounds": 6}, answered_by="operator")
    retried = await _handler_with(policy).handle(job)
    assert isinstance(retried, Defer)
    assert "repair" in retried.detail

    # A grant at or below the burned rounds still parks (pairs form too).
    await gates.answer(gate.gate_id, answer={"answers": {"max_rounds": "2"}}, answered_by="op")
    still_parked = await _handler_with(policy).handle(job)
    assert isinstance(still_parked, Park)


async def test_a_failing_gate_on_a_solo_pool_records_no_waiver(tmp_path: Path) -> None:
    """The ledger is append-only, so the waiver decision may only be written
    once the item really was verified. A solo-pool verify whose gate fails is
    not a verification; if the decision were written before the gates ran it
    would say `item-1` "was verified by its own implementer" forever, with no
    way to take it back."""
    ledger = FakeLedger()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(returncode=1, stderr="assertion failed"),
        reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine"),
        ledger=ledger,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        independence=VerifyIndependencePolicy(
            pool=frozenset({EngineId.CLAUDELOOP}), clock=FixedClock()
        ),
    )

    outcome = await handler.handle(_job(requirement={"implementer_engine_id": "claudeloop"}))

    assert isinstance(outcome, Failure)
    assert outcome.failure_class is FailureClass.WORK
    assert [e for e in ledger.recorded if e.kind == "DecisionRecorded"] == []


async def test_a_rejected_self_review_on_a_solo_pool_records_no_waiver(tmp_path: Path) -> None:
    """The other way a solo-pool verify can fail: the gates all pass, and the
    diff review itself says no. The waiver claims the item "was verified by its
    own implementer"; a rejected review verified nothing, so the append-only
    ledger must stay empty here too. This is the path the failing-gate test
    cannot reach -- it returns before the review ever runs."""
    now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    ledger = FakeLedger()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(
            descriptor=CLAUDELOOP,
            base_dir=tmp_path / "engine",
            script=[{"kind": "SessionSeeded", "at": now, "payload": {"seed_digest": "d1"}}],
        ),
        ledger=ledger,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        independence=VerifyIndependencePolicy(
            pool=frozenset({EngineId.CLAUDELOOP}), clock=FixedClock()
        ),
    )

    outcome = await handler.handle(_job(requirement={"implementer_engine_id": "claudeloop"}))

    assert outcome == Failure(FailureClass.WORK, "diff review did not approve this work item")
    assert [e for e in ledger.recorded if e.kind == "DecisionRecorded"] == []


def test_granted_max_rounds_parses_both_forms_and_rejects_junk() -> None:
    from vibey.application.build_verify_handler import granted_max_rounds

    assert granted_max_rounds({"max_rounds": 6}) == 6
    assert granted_max_rounds({"answers": {"max_rounds": "7"}}) == 7
    assert granted_max_rounds({"max_rounds": True}) is None
    assert granted_max_rounds({"max_rounds": "lots"}) is None
    assert granted_max_rounds({"resolution": "fixed by hand"}) is None


def test_granted_amount_parses_floats_and_rejects_junk() -> None:
    from vibey.application.build_verify_handler import granted_amount

    assert granted_amount({"max_dollars": 12.5}, "max_dollars") == 12.5
    assert granted_amount({"answers": {"max_dollars": "7.25"}}, "max_dollars") == 7.25
    assert granted_amount({"max_dollars": True}, "max_dollars") is None
    assert granted_amount({"max_dollars": "plenty"}, "max_dollars") is None
    assert granted_amount({"unrelated": 1}, "max_dollars") is None


# ── a capacity rejection outranks the diff review's verdict (#215) ───────────


def _capacity_rejected_review() -> list[dict[str, object]]:
    """A reviewer run that hits capacity AND claims completion in the same
    run -- the exact shape the non-negotiable is about: whatever the verdict
    says, the capacity rejection wins."""
    now = datetime(2026, 1, 1, tzinfo=UTC).isoformat()
    return [
        {"kind": "SessionSeeded", "at": now, "payload": {"seed_digest": "d1"}},
        {
            "kind": "CapacityRejected",
            "at": now,
            "payload": {"capacity_state": "CreditsExhausted", "can_purchase": True},
        },
        {
            "kind": "VerdictRendered",
            "at": now,
            "payload": {"complete": True, "remaining_work": [], "summary": "looks fine"},
        },
    ]


async def test_a_capacity_rejected_review_defers_as_capacity_not_a_work_failure(
    tmp_path: Path,
) -> None:
    """#215: verify discarded `capacity_rejected` and went straight to the
    verdict, so a reviewer out of credits either burned an attempt as a WORK
    failure or -- with a completing verdict beside it -- passed the item. It
    must be a capacity Defer (refunded attempt, circuit opened) and nothing
    downstream of an approval may happen."""
    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(
            descriptor=CODEXLOOP,
            base_dir=tmp_path / "engine",
            script=_capacity_rejected_review(),
        ),
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
    )

    outcome = await handler.handle(_job(requirement={"implementer_engine_id": "claudeloop"}))

    assert outcome == Defer(
        retry_at=FixedClock().now() + timedelta(minutes=5),
        detail="engine codexloop reported capacity rejection during the diff review",
        capacity=True,
    )
    # The rejection itself is still on the record; only the approval is not.
    assert any(event.kind == "CapacityRejected" for event in ledger.recorded)
    # No build.integrate: the item was never approved.
    assert jobs._jobs == {}


async def test_a_capacity_rejected_self_review_writes_no_waiver_and_resolves_nothing(
    tmp_path: Path,
) -> None:
    """The success path writes to an append-only ledger: it resolves this
    item's open repair findings and, on a solo pool, records that the item
    "was verified by its own implementer". A reviewer that ran out of
    capacity verified nothing, so neither entry may be written."""
    from vibey.domain.ledger import EventKind

    job = _job(requirement={"implementer_engine_id": "claudeloop"})
    open_finding = _finding_event(job.cycle, EventKind.FINDING_RAISED, "f_verify_item-1_aaaa1111")
    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(
            descriptor=CLAUDELOOP,
            base_dir=tmp_path / "engine",
            script=_capacity_rejected_review(),
        ),
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
        repair=_repair_policy([open_finding]),
        independence=VerifyIndependencePolicy(
            pool=frozenset({EngineId.CLAUDELOOP}), clock=FixedClock()
        ),
    )

    outcome = await handler.handle(job)

    assert isinstance(outcome, Defer)
    assert outcome.capacity is True
    assert "claudeloop" in outcome.detail
    kinds = [event.kind for event in ledger.recorded]
    assert "DecisionRecorded" not in kinds
    assert "FindingResolved" not in kinds
    assert jobs._jobs == {}


async def test_the_capacity_backoff_is_configurable(tmp_path: Path) -> None:
    handler = BuildVerifyHandler(
        worktrees=FakeWorktrees(tmp_path),
        gates=FakeGateRunner(),
        reviewer=ScriptedEngine(
            descriptor=CODEXLOOP,
            base_dir=tmp_path / "engine",
            script=_capacity_rejected_review(),
        ),
        ledger=FakeLedger(),
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        capacity_backoff=timedelta(minutes=17),
    )

    outcome = await handler.handle(_job(requirement={"implementer_engine_id": "claudeloop"}))

    assert isinstance(outcome, Defer)
    assert outcome.retry_at == FixedClock().now() + timedelta(minutes=17)
