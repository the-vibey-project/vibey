# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Replay cases for the BUILD handlers and the design interview (SP2-A Task 7).

Each case reuses the fakes of the handler's own test file, over one persisted set of fakes the
redelivered handler instance shares with the first (``harness.py``). The job sits READY in the
fake queue; the harness leases it, delivers it, lets the lease lapse and delivers the refreshed
row (attempt 2) to a new handler instance."""

import dataclasses
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from tests.application.replay.harness import (
    CallBatches,
    ContentLedger,
    ReplayCase,
    ReplayRig,
    assert_replay_is_idempotent,
    jobs_content,
)
from tests.application.test_build_decompose_handler import Decomposer, Specs, _item, spec
from tests.application.test_build_implement_handler import FakeProvisioner, FakeWorktrees
from tests.application.test_build_integrate_handler import FakeGateRunner as IntegrateGates
from tests.application.test_build_integrate_handler import FakeIntegration, FakeTransitioner
from tests.application.test_build_verify_handler import FakeGateRunner as VerifyGates
from tests.application.test_build_verify_handler import FakeWorktrees as VerifyWorktrees
from tests.application.test_design_handler import FakeDesignLedger, ScriptedQuestionProvider
from vibey.application.build_decompose_handler import BuildDecomposeHandler
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.build_integrate_handler import BuildIntegrateHandler, MergeOutcome
from vibey.application.build_verify_handler import BuildVerifyHandler, VerifyRepairPolicy
from vibey.application.design import DESIGN_STAGES
from vibey.application.design_handler import DesignInterviewHandler
from vibey.application.worker import Park
from vibey.domain.engine import EngineId
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.scripted import ScriptedEngine


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 11, tzinfo=UTC)


def _decompose(scratch: Path) -> ReplayRig:
    job = replace(make_job(uuid4()), kind="build.decompose")
    jobs = FakeJobRepository([job])
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
        _item("item-3", depends_on=("item-2",)),
    )

    def handler() -> BuildDecomposeHandler:
        return BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        snapshot=lambda: {"jobs": jobs_content(jobs, job.id)},
        redeliver=handler,
    )


def _design_handler_factory(
    jobs: FakeJobRepository,
    gates: FakeHumanGateRepository,
    ledger: FakeDesignLedger,
    interviewer: EngineId,
):  # type: ignore[no-untyped-def]
    def handler() -> DesignInterviewHandler:
        return DesignInterviewHandler(
            ledger=ledger,
            jobs=jobs,
            gates=gates,
            questions=ScriptedQuestionProvider(),
            clock=_Clock(),
            interviewer=interviewer,
        )

    return handler


def _design_interview(scratch: Path) -> ReplayRig:
    """The interview complete: every stage asked and answered, so the delivery under replay
    is the one that fans out the research, synthesis and spec jobs."""
    project_id = uuid4()
    job = replace(make_job(project_id), phase=Phase.DESIGN, kind="design.interview")
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    ledger = FakeDesignLedger()
    handler = _design_handler_factory(jobs, gates, ledger, EngineId.CLAUDELOOP)

    async def answer_every_stage() -> None:
        scripted = handler()
        for index, _stage in enumerate(DESIGN_STAGES):
            parked = await scripted.handle(job)
            assert isinstance(parked, Park)
            raised = await gates.raise_gate(project_id, job.id, parked.request)
            await gates.answer(
                raised.gate_id,
                answer={"answers": {f"q-{index + 1}": f"answer-{index + 1}"}},
                answered_by="scripted-user",
            )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        prepare=answer_every_stage,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": [dataclasses.asdict(event) for event in ledger.events],
            "jobs": jobs_content(jobs, job.id),
            "gates": [dataclasses.asdict(record) for record in gates.raised],
        },
    )


def _design_question_batch(scratch: Path) -> ReplayRig:
    """The first delivery asks stage one and parks; the redelivery must not ask it again."""
    job = replace(make_job(uuid4()), phase=Phase.DESIGN, kind="design.interview")
    jobs = FakeJobRepository([job])
    ledger = FakeDesignLedger()
    handler = _design_handler_factory(jobs, FakeHumanGateRepository(), ledger, EngineId.CODEXLOOP)

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": [dataclasses.asdict(event) for event in ledger.events],
            "jobs": jobs_content(jobs, job.id),
        },
    )


def _implement(scratch: Path) -> ReplayRig:
    """A redelivery arrives as attempt 2, which the handler's effort ladder and cost
    projection branch on (``job.attempts``)."""
    ledger = ContentLedger()
    worktrees = FakeWorktrees(scratch)
    job = replace(
        make_job(uuid4()),
        kind="build.implement",
        work_item_id="item-1",
        payload={"title": "do the thing", "verification": {}},
    )
    jobs = FakeJobRepository([job])

    def handler() -> BuildImplementHandler:
        return BuildImplementHandler(
            worktrees=worktrees,
            provisioner=FakeProvisioner(),
            engine=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=scratch / "engine"),
            ledger=ledger,
            jobs=jobs,
            clock=_Clock(),
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        # see #1887; tighten to exact entries once the ledger dedupes on identity
        snapshot=lambda: {"ledger": ledger.after_delivery(), "jobs": jobs_content(jobs, job.id)},
    )


def _integrate(scratch: Path) -> ReplayRig:
    """The last integrate of the cycle: it records gate evidence, moves the project to
    REVIEW and enqueues the review entry."""
    ledger = ContentLedger()
    transitioner = FakeTransitioner()
    integration = FakeIntegration(merge_outcome=MergeOutcome(ok=True, detail=""), path=scratch)
    job = replace(
        make_job(uuid4()),
        kind="build.integrate",
        work_item_id="item-1",
        payload={"verification": {"commands": ("true",), "criteria_checked": ("AC-1",)}},
    )
    jobs = FakeJobRepository([job])

    def handler() -> BuildIntegrateHandler:
        return BuildIntegrateHandler(
            integration=integration,
            gates=IntegrateGates(),
            ledger=ledger,
            jobs=jobs,
            clock=_Clock(),
            projects=transitioner,
        )

    merges = CallBatches(lambda: integration.merged, expected_first=["item-1"])
    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        # see #1887; tighten to exact entries once the ledger dedupes on identity (the gate
        # evidence `integrate-gates-<item>` is written again, identically).
        snapshot=lambda: {
            "ledger": ledger.after_delivery(),
            "jobs": jobs_content(jobs, job.id),
            # The merges, in order, delivery by delivery (a redelivery calls merge_item for
            # the item again, and the real IntegrationBranch.merge_item runs `git merge
            # --no-edit <branch>` and takes exit 0 as ok (infrastructure/git/
            # integration_branch.py:76-80); git exits 0 with "Already up to date." for a branch
            # that is already merged. That is git's behaviour, which this fake does not model,
            # and it is why the redelivery's list is compared with the first's, not forbidden).
            # The fake appends on every call; a double merge inside one delivery fails.
            "merges": merges.after_delivery(),
        },
    )


def _verify(scratch: Path) -> ReplayRig:
    ledger = ContentLedger()
    job = replace(
        make_job(uuid4()),
        kind="build.verify",
        work_item_id="item-1",
        payload={"verification": {"commands": ("pytest",), "criteria_checked": ("AC-1",)}},
        requirement={"implementer_engine_id": "codexloop"},
    )
    jobs = FakeJobRepository([job])

    def handler() -> BuildVerifyHandler:
        return BuildVerifyHandler(
            worktrees=VerifyWorktrees(scratch),
            gates=VerifyGates(),
            reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=scratch / "engine"),
            ledger=ledger,
            jobs=jobs,
            clock=_Clock(),
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        # see #1887; tighten to exact entries once the ledger dedupes on identity
        snapshot=lambda: {"ledger": ledger.after_delivery(), "jobs": jobs_content(jobs, job.id)},
    )


# ----------------------------------------------------- the failing-gate (repair) paths


class _ReaderOverLedger:
    """What ``LedgerReader`` is in production (``resources.ledger``): it reads back what the
    handler's own ledger wrote, so a redelivery can see the finding its first delivery raised."""

    def __init__(self, ledger: ContentLedger) -> None:
        self._ledger = ledger

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(
            LedgerEvent(
                event_id=uuid4(),
                project_id=entry["project_id"],  # type: ignore[arg-type]
                cycle=entry["cycle"],  # type: ignore[arg-type]
                phase=Phase.BUILD,
                seq=seq,
                kind=EventKind(str(entry["kind"])),
                engine_id=None,
                job_id=entry["job_id"],  # type: ignore[arg-type]
                causation_id=entry["causation_id"],  # type: ignore[arg-type]
                correlation_id=entry["correlation_id"],  # type: ignore[arg-type]
                provenance=Provenance.AGENT,
                produced_at=entry["at"],  # type: ignore[arg-type]
                payload=entry["payload"],  # type: ignore[arg-type]
                digest=digest_event(entry["payload"]),  # type: ignore[arg-type]
            )
            for seq, entry in enumerate(self._ledger.entries, start=1)
        )


def _integrate_failing(*, wired_like_production: bool) -> Callable[[Path], ReplayRig]:
    """A merge that conflicts: the handler raises a finding and enqueues a repair session.

    ``wired_like_production`` gives it the ledger reader bootstrap wires (``ledger_reader=
    resources.ledger``): the redelivery reads its first delivery's open finding, enqueues
    nothing more and defers ("repair in flight"). Without a reader (the constructor's default)
    the handler has no memory of its own finding (finding F-8-4, #1890)."""

    def build(scratch: Path) -> ReplayRig:
        ledger = ContentLedger()
        job = replace(
            make_job(uuid4()),
            kind="build.integrate",
            work_item_id="item-1",
            payload={"verification": {"commands": ("true",), "criteria_checked": ("AC-1",)}},
        )
        jobs = FakeJobRepository([job])
        integration = FakeIntegration(
            merge_outcome=MergeOutcome(ok=False, detail="conflict in greet.py"), path=scratch
        )

        def handler() -> BuildIntegrateHandler:
            return BuildIntegrateHandler(
                integration=integration,
                gates=IntegrateGates(),
                ledger=ledger,
                jobs=jobs,
                clock=_Clock(),
                ledger_reader=_ReaderOverLedger(ledger) if wired_like_production else None,
            )

        return ReplayRig(
            handler=handler(),
            job=job,
            jobs=jobs,
            redeliver=handler,
            # see #1887; tighten to exact entries once the ledger dedupes on identity
            snapshot=lambda: {
                "ledger": ledger.after_delivery(),
                "jobs": jobs_content(jobs, job.id),
            },
        )

    return build


def _verify_failing(scratch: Path) -> ReplayRig:
    """A failing verification gate: the handler raises a finding and enqueues a repair session,
    reading its own finding back through the ``VerifyRepairPolicy`` ledger reader bootstrap
    wires, so a redelivery finds the repair in flight. (Without the policy it fails the job and
    raises nothing, so there is no duplicate to find on that path.)"""
    ledger = ContentLedger()
    job = replace(
        make_job(uuid4()),
        kind="build.verify",
        work_item_id="item-1",
        payload={"verification": {"commands": ("pytest",), "criteria_checked": ("AC-1",)}},
        requirement={"implementer_engine_id": "codexloop"},
    )
    jobs = FakeJobRepository([job])

    def handler() -> BuildVerifyHandler:
        return BuildVerifyHandler(
            worktrees=VerifyWorktrees(scratch),
            gates=VerifyGates(returncode=1, stderr="assert 1 == 2"),
            reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=scratch / "engine"),
            ledger=ledger,
            jobs=jobs,
            clock=_Clock(),
            repair=VerifyRepairPolicy(ledger_reader=_ReaderOverLedger(ledger), clock=_Clock()),
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        jobs=jobs,
        redeliver=handler,
        # see #1887; tighten to exact entries once the ledger dedupes on identity
        snapshot=lambda: {"ledger": ledger.after_delivery(), "jobs": jobs_content(jobs, job.id)},
    )


# The census (tests/meta/test_every_handler_has_a_replay_case.py) reads `kind="..."` of each
# ReplayCase( call inside the `CASES = (...)` of a test_*_replay.py by AST, so a kind is a
# string literal, not a variable, and a case only counts if it is in CASES and CASES is what
# the parametrized test below runs.
CASES = (
    ReplayCase(name="the fan-out of work items", kind="build_decompose", build=_decompose),
    ReplayCase(
        name="an interview that has asked and parked", kind="design", build=_design_question_batch
    ),
    ReplayCase(
        name="a finished interview that fans out the follow-up jobs",
        kind="design",
        build=_design_interview,
    ),
    ReplayCase(name="a session that enqueues its verify", kind="build_implement", build=_implement),
    ReplayCase(name="the last merge that enters REVIEW", kind="build_integrate", build=_integrate),
    ReplayCase(
        name="gates, an independent review and the integrate follow-up",
        kind="build_verify",
        build=_verify,
    ),
    ReplayCase(
        name="a failing gate raises a finding and enqueues one repair",
        kind="build_verify",
        build=_verify_failing,
    ),
    ReplayCase(
        name="a conflicting merge raises a finding and enqueues one repair",
        kind="build_integrate",
        build=_integrate_failing(wired_like_production=True),
    ),
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.kind}: {case.name}")
async def test_a_redelivered_job_leaves_what_one_delivery_left(
    case: ReplayCase, tmp_path: Path
) -> None:
    await assert_replay_is_idempotent(case, tmp_path)


# F-8-4 (#1890): a BuildIntegrateHandler built without a ledger reader (its constructor's
# default; bootstrap always passes one) mints `f_integrate_<item>_<uuid4>` and keys the repair
# `build.implement` on it, so a redelivery raises a second finding and enqueues a second
# repair job. With the reader the redelivery finds the open finding and defers, which is the
# production case above. build_verify has no such path: without its repair policy it fails
# the job and raises nothing, and its policy carries the reader. A strict xfail: the day the id
# is derived from the job, this passes, fails, and its mark has to go.
@pytest.mark.xfail(
    strict=True,
    raises=AssertionError,
    reason="F-8-4 #1890: no ledger reader, so a redelivery raises a second finding and repair",
)
async def test_an_integrate_without_a_ledger_reader_repairs_twice(tmp_path: Path) -> None:
    case = ReplayCase(
        name="a conflicting merge, no ledger reader",
        kind="finding",
        build=_integrate_failing(wired_like_production=False),
    )
    await assert_replay_is_idempotent(case, tmp_path)


def test_every_case_defined_here_is_run() -> None:
    defined = [value for value in globals().values() if isinstance(value, ReplayCase)]
    assert defined == []  # no stray module-level case outside CASES
    assert len(CASES) == len({(case.kind, case.name) for case in CASES})
