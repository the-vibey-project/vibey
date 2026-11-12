# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Replay cases for the BUILD handlers and the design interview (SP2-A Task 7).

Each case reuses the fakes of the handler's own test file, over one persisted set of fakes
the redelivered handler instance shares with the first (``harness.py``)."""

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
from tests.application.test_build_integrate_handler import (
    FakeGateRunner as IntegrateGates,
)
from tests.application.test_build_integrate_handler import (
    FakeIntegration,
    FakeTransitioner,
)
from tests.application.test_build_verify_handler import FakeGateRunner as VerifyGates
from tests.application.test_build_verify_handler import FakeWorktrees as VerifyWorktrees
from tests.application.test_design_handler import (
    FakeDesignLedger,
    ScriptedQuestionProvider,
)
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

_SCRATCH: list[Path] = []


@pytest.fixture(autouse=True)
def _scratch_directory(tmp_path: Path) -> None:
    """The per-test directory the engine and worktree fakes write under."""
    _SCRATCH[:] = [tmp_path]


def _tmp() -> Path:
    return _SCRATCH[0]


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 11, 11, tzinfo=UTC)


def _decompose() -> ReplayRig:
    jobs = FakeJobRepository()
    items = (
        _item("skeleton", acceptance_ids=("AC-1",)),
        _item("item-2", acceptance_ids=("AC-2",), depends_on=("skeleton",)),
        _item("item-3", depends_on=("item-2",)),
    )
    job = replace(make_job(uuid4()), kind="build.decompose")
    jobs.seed_leased(job)

    def handler() -> BuildDecomposeHandler:
        return BuildDecomposeHandler(specs=Specs(spec()), decomposer=Decomposer(items), jobs=jobs)

    return ReplayRig(
        handler=handler(),
        job=job,
        snapshot=lambda: {"jobs": jobs_content(jobs)},
        redeliver=handler,
    )


def _design_interview() -> ReplayRig:
    """The interview complete: every stage asked and answered, so the delivery under replay
    is the one that fans out the research, synthesis and spec jobs."""
    project_id = uuid4()
    job = replace(make_job(project_id), phase=Phase.DESIGN, kind="design.interview")
    jobs = FakeJobRepository()
    gates = FakeHumanGateRepository()
    ledger = FakeDesignLedger()

    def handler() -> DesignInterviewHandler:
        return DesignInterviewHandler(
            ledger=ledger,
            jobs=jobs,
            gates=gates,
            questions=ScriptedQuestionProvider(),
            clock=_Clock(),
            interviewer=EngineId.CLAUDELOOP,
        )

    async def answer_every_stage() -> None:
        jobs.seed_leased(job)
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
        prepare=answer_every_stage,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": [dataclasses.asdict(event) for event in ledger.events],
            "jobs": jobs_content(jobs),
            "gates": [dataclasses.asdict(record) for record in gates.raised],
        },
    )


def _design_question_batch() -> ReplayRig:
    """The first delivery asks stage one and parks; the redelivery must not ask it again."""
    job = replace(make_job(uuid4()), phase=Phase.DESIGN, kind="design.interview")
    jobs = FakeJobRepository()
    gates = FakeHumanGateRepository()
    ledger = FakeDesignLedger()

    def handler() -> DesignInterviewHandler:
        return DesignInterviewHandler(
            ledger=ledger,
            jobs=jobs,
            gates=gates,
            questions=ScriptedQuestionProvider(),
            clock=_Clock(),
            interviewer=EngineId.CODEXLOOP,
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        redeliver=handler,
        snapshot=lambda: {
            "ledger": [dataclasses.asdict(event) for event in ledger.events],
            "jobs": jobs_content(jobs),
        },
    )


def _implement() -> ReplayRig:
    ledger = ContentLedger()
    jobs = FakeJobRepository()
    worktrees = FakeWorktrees(_tmp())
    job = replace(
        make_job(uuid4()),
        kind="build.implement",
        work_item_id="item-1",
        attempts=1,
        payload={"title": "do the thing", "verification": {}},
    )
    jobs.seed_leased(job)

    def handler() -> BuildImplementHandler:
        return BuildImplementHandler(
            worktrees=worktrees,
            provisioner=FakeProvisioner(),
            engine=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=_tmp() / "engine"),
            ledger=ledger,
            jobs=jobs,
            clock=_Clock(),
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        redeliver=handler,
        snapshot=lambda: {"ledger": ledger.content(), "jobs": jobs_content(jobs)},
    )


def _integrate() -> ReplayRig:
    """The last integrate of the cycle: it records gate evidence, moves the project to
    REVIEW and enqueues the review entry."""
    ledger = ContentLedger()
    jobs = FakeJobRepository()
    transitioner = FakeTransitioner()
    integration = FakeIntegration(merge_outcome=MergeOutcome(ok=True, detail=""), path=_tmp())
    job = replace(
        make_job(uuid4()),
        kind="build.integrate",
        work_item_id="item-1",
        payload={"verification": {"commands": ("true",), "criteria_checked": ("AC-1",)}},
    )
    jobs.seed_leased(job)

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
        redeliver=handler,
        snapshot=lambda: {
            "ledger": ledger.content(),
            "jobs": jobs_content(jobs),
            # Which items are merged, not how many times merge_item was called: a merge of
            # a branch already merged is a no-op in git, which this fake does not model.
            "merged": sorted(set(integration.merged)),
        },
    )


def _verify() -> ReplayRig:
    ledger = ContentLedger()
    jobs = FakeJobRepository()
    job = replace(
        make_job(uuid4()),
        kind="build.verify",
        work_item_id="item-1",
        payload={"verification": {"commands": ("pytest",), "criteria_checked": ("AC-1",)}},
        requirement={"implementer_engine_id": "codexloop"},
    )
    jobs.seed_leased(job)

    def handler() -> BuildVerifyHandler:
        return BuildVerifyHandler(
            worktrees=VerifyWorktrees(_tmp()),
            gates=VerifyGates(),
            reviewer=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=_tmp() / "engine"),
            ledger=ledger,
            jobs=jobs,
            clock=_Clock(),
        )

    return ReplayRig(
        handler=handler(),
        job=job,
        redeliver=handler,
        snapshot=lambda: {"ledger": ledger.content(), "jobs": jobs_content(jobs)},
    )


# The census (tests/meta/test_every_handler_has_a_replay_case.py) reads `kind="..."` of each
# ReplayCase( call in this directory by AST, so a kind is a string literal, not a variable.
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
async def test_a_redelivered_job_leaves_what_one_delivery_left(case: ReplayCase) -> None:
    await assert_replay_is_idempotent(case)
