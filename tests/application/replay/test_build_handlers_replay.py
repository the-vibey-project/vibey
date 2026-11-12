# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Replay cases for the BUILD handlers and the design interview (SP2-A Task 7).

Each case reuses the fakes of the handler's own test file, over one persisted set of fakes the
redelivered handler instance shares with the first (``harness.py``). The job sits READY in the
fake queue; the harness leases it, delivers it, lets the lease lapse and delivers the refreshed
row (attempt 2) to a new handler instance."""

import dataclasses
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from tests.application.replay.harness import (
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
from vibey.application.build_verify_handler import BuildVerifyHandler
from vibey.application.design import DESIGN_STAGES
from vibey.application.design_handler import DesignInterviewHandler
from vibey.application.worker import Park
from vibey.domain.engine import EngineId
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
            # Which items are merged, not how many times merge_item was called: the real
            # IntegrationBranch.merge_item runs `git merge --no-edit <branch>` and takes exit
            # 0 as ok (infrastructure/git/integration_branch.py:76-80), and git exits 0 with
            # "Already up to date." for a branch that is already merged. That is git's
            # behaviour, which this fake does not model.
            "merged": sorted(set(integration.merged)),
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
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.kind}: {case.name}")
async def test_a_redelivered_job_leaves_what_one_delivery_left(
    case: ReplayCase, tmp_path: Path
) -> None:
    await assert_replay_is_idempotent(case, tmp_path)


def test_every_case_defined_here_is_run() -> None:
    defined = [value for value in globals().values() if isinstance(value, ReplayCase)]
    assert defined == []  # no stray module-level case outside CASES
    assert len(CASES) == len({(case.kind, case.name) for case in CASES})
