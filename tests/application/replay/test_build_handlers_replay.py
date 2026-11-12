# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Replay cases for the build_decompose handler and the design interview (SP2-A Task 7).

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
    ReplayCase,
    ReplayRig,
    assert_replay_is_idempotent,
    jobs_content,
)
from tests.application.test_build_decompose_handler import Decomposer, Specs, _item, spec
from tests.application.test_design_handler import (
    FakeDesignLedger,
    ScriptedQuestionProvider,
)
from vibey.application.build_decompose_handler import BuildDecomposeHandler
from vibey.application.design import DESIGN_STAGES
from vibey.application.design_handler import DesignInterviewHandler
from vibey.application.worker import Park
from vibey.domain.engine import EngineId
from vibey.domain.phase import Phase

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
)


@pytest.mark.parametrize("case", CASES, ids=lambda case: f"{case.kind}: {case.name}")
async def test_a_redelivered_job_leaves_what_one_delivery_left(case: ReplayCase) -> None:
    await assert_replay_is_idempotent(case)
