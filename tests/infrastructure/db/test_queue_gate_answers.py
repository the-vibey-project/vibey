# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An answer to the queue's own gate is never read as the job's answer (#1108 review, P7).

The queue parks a job with a gate of its own -- `delivery_exhausted` when its worker died
on every attempt (ADR-0056), `attempts_exhausted` when its handler failed on every one
(ADR-0024). Answering that gate buys the job another delivery; it answers nothing the job
itself asked. Before this, a `review.deployment_choice` job whose worker died before it
asked anything was parked, the exhaustion gate was answered "go", and the handler read that
as the deployment answer: it recorded `DeploymentDeclined` and moved REVIEW to DONE without
the question ever being asked.
"""

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

import asyncpg
import pytest

from vibey.application.dto import EnqueueRequest, HumanGateRequest
from vibey.application.review_deployment_choice_handler import ReviewDeploymentChoiceHandler
from vibey.application.worker import Park, Success
from vibey.domain.job import (
    ATTEMPTS_EXHAUSTED_GATE_KIND,
    DELIVERY_EXHAUSTED_GATE_KIND,
    QUEUE_GATE_KINDS,
)
from vibey.domain.ledger import EventKind, LedgerEvent
from vibey.domain.phase import Phase
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.job_repository import PostgresJobRepository

EXPIRED = timedelta(seconds=-1)


class _Clock:
    def now(self) -> datetime:
        return datetime(2026, 9, 24, tzinfo=UTC)


class _Ledger:
    def __init__(self) -> None:
        self.appended: list[EventKind] = []

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return ()

    async def append_event(
        self,
        project_id: UUID,
        cycle: int,
        job_id: UUID,
        kind: EventKind,
        payload: Mapping[str, object],
    ) -> None:
        self.appended.append(kind)


class _Projects:
    def __init__(self) -> None:
        self.transitions: list[Phase] = []

    async def transition(self, project_id: UUID, *, expected: Phase, to: Phase) -> None:
        self.transitions.append(to)


def test_the_queue_gate_kinds_are_the_two_exhaustion_gates() -> None:
    assert {ATTEMPTS_EXHAUSTED_GATE_KIND, DELIVERY_EXHAUSTED_GATE_KIND} == QUEUE_GATE_KINDS
    assert (ATTEMPTS_EXHAUSTED_GATE_KIND, DELIVERY_EXHAUSTED_GATE_KIND) == (
        "attempts_exhausted",
        "delivery_exhausted",
    )


async def test_p7_an_answered_delivery_exhausted_gate_does_not_answer_the_deploy_question(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.REVIEW,
            kind="review.deployment_choice",
            idempotency_key="choice",
            max_attempts=1,
        )
    )
    await repo.claim(project_id, owner="w", lease=EXPIRED)  # its worker dies
    assert await repo.reap() == 1
    (gate,) = await gates.open_for_project(project_id)
    assert gate.kind == DELIVERY_EXHAUSTED_GATE_KIND
    await gates.answer(gate.gate_id, answer={"text": "go"}, answered_by="operator")
    claimed = await repo.claim(project_id, owner="w2", lease=timedelta(minutes=2))
    assert claimed is not None and claimed.id == job.id

    ledger, projects = _Ledger(), _Projects()
    outcome = await ReviewDeploymentChoiceHandler(
        ledger=ledger, gates=gates, jobs=repo, projects=projects, clock=_Clock()
    ).handle(claimed)

    assert isinstance(outcome, Park), outcome
    assert outcome.request.kind == "choice"
    assert "Deploy to target infrastructure?" in outcome.request.prompt
    assert ledger.appended == []
    assert projects.transitions == []


async def test_an_answered_attempts_exhausted_gate_does_not_answer_the_deploy_question(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The worker's own exhaustion gate (ADR-0024) had the same flaw."""
    repo = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.REVIEW,
            kind="review.deployment_choice",
            idempotency_key="choice2",
        )
    )
    exhausted = await gates.raise_gate(
        project_id,
        job.id,
        HumanGateRequest(kind=ATTEMPTS_EXHAUSTED_GATE_KIND, prompt="attempts spent"),
    )
    await gates.answer(exhausted.gate_id, answer={"choice": "retry"}, answered_by="operator")
    claimed = await repo.claim(project_id, owner="w", lease=timedelta(minutes=2))
    assert claimed is not None

    ledger, projects = _Ledger(), _Projects()
    outcome = await ReviewDeploymentChoiceHandler(
        ledger=ledger, gates=gates, jobs=repo, projects=projects, clock=_Clock()
    ).handle(claimed)

    assert isinstance(outcome, Park)
    assert outcome.request.kind == "choice"
    assert ledger.appended == []


async def test_the_jobs_own_answer_still_reaches_it_past_a_later_queue_gate(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """Asked and answered `local_only`, then its worker died on every attempt and that gate
    was answered `deploy`: the handler acts on its own answer, never on the queue's."""
    repo = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.REVIEW,
            kind="review.deployment_choice",
            idempotency_key="choice3",
        )
    )
    choice = await gates.raise_gate(
        project_id, job.id, HumanGateRequest(kind="choice", prompt="Deploy?")
    )
    await gates.answer(choice.gate_id, answer={"choice": "local_only"}, answered_by="op")
    queue_gate = await gates.raise_gate(
        project_id, job.id, HumanGateRequest(kind=DELIVERY_EXHAUSTED_GATE_KIND, prompt="spent")
    )
    await gates.answer(queue_gate.gate_id, answer={"choice": "deploy"}, answered_by="op")

    own = await gates.latest_for_job(job.id)
    assert own is not None and own.gate_id == choice.gate_id
    everything = await gates.latest_for_job(job.id, include_queue_gates=True)
    assert everything is not None and everything.gate_id == queue_gate.gate_id

    claimed = await repo.claim(project_id, owner="w", lease=timedelta(minutes=2))
    assert claimed is not None
    ledger, projects = _Ledger(), _Projects()
    outcome = await ReviewDeploymentChoiceHandler(
        ledger=ledger, gates=gates, jobs=repo, projects=projects, clock=_Clock()
    ).handle(claimed)
    assert isinstance(outcome, Success)
    assert outcome.result["decision"] == "declined"
    assert ledger.appended == [EventKind.DEPLOYMENT_DECLINED]


@pytest.mark.parametrize("kind", sorted(QUEUE_GATE_KINDS))
async def test_a_job_with_only_a_queue_gate_has_no_gate_of_its_own(
    migrated_pool: asyncpg.Pool, project_id: UUID, kind: str
) -> None:
    repo = PostgresJobRepository(migrated_pool)
    gates = PostgresHumanGateRepository(migrated_pool)
    job = await repo.enqueue(
        EnqueueRequest(
            project_id=project_id,
            cycle=1,
            phase=Phase.BUILD,
            kind="build.implement",
            idempotency_key=f"only-{kind}",
        )
    )
    await gates.raise_gate(project_id, job.id, HumanGateRequest(kind=kind, prompt="spent"))
    assert await gates.latest_for_job(job.id) is None
    seen = await gates.latest_for_job(job.id, include_queue_gates=True)
    assert seen is not None and seen.kind == kind
