# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""A gate is answered once, against the real database: the compare-and-set on
`answered_at IS NULL`, the replay of one request, the refusal of any other, and the
`GateAnswered` event written in the same transaction as the answer."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.application.dto import HumanGateRequest, ProjectRecord
from vibey.domain.errors import GateAlreadyAnswered, UnknownGate, WrongPhase
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, Provenance, digest_event
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.infrastructure.db.human_gate_repository import (
    GATE_ANSWERED_DRAFTS,
    PostgresHumanGateRepository,
)
from vibey.infrastructure.db.interfaces import (
    GateAnsweredDraftBuilderInterface,
    PostgresHumanGateRepositoryInterface,
)
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository

from .test_job_repository import LEASE, _request


async def _parked_gate(pool: asyncpg.Pool, project_id: UUID) -> tuple[UUID, UUID]:
    jobs = PostgresJobRepository(pool)
    job = await jobs.enqueue(_request(project_id))
    assert await jobs.claim(project_id, owner="w1", lease=LEASE) is not None
    assert await jobs.park(job.id, owner="w1")
    gate = await PostgresHumanGateRepository(pool).raise_gate(
        project_id, job.id, HumanGateRequest(kind="approval", prompt="ship it?")
    )
    return gate.gate_id, job.id


async def _answered_events(pool: asyncpg.Pool, project_id: UUID) -> list[dict[str, object]]:
    events = await PostgresLedgerRepository(pool).all_for_project(project_id)
    return [dict(e.payload) for e in events if e.kind is EventKind.GATE_ANSWERED]


def test_the_repository_and_its_builder_satisfy_their_interfaces(
    migrated_pool: asyncpg.Pool,
) -> None:
    assert isinstance(
        PostgresHumanGateRepository(migrated_pool), PostgresHumanGateRepositoryInterface
    )
    assert isinstance(GATE_ANSWERED_DRAFTS, GateAnsweredDraftBuilderInterface)


async def test_an_answer_lands_once_with_its_event_and_readies_the_job(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    gate_id, job_id = await _parked_gate(migrated_pool, project_id)
    gates = PostgresHumanGateRepository(migrated_pool)

    outcome = await gates.answer_once(
        gate_id,
        answer={"verdict": "accept"},
        answered_by="vibey-vscode",
        account="adam",
        request_id="req-1",
    )

    assert not outcome.replayed
    assert outcome.record.answer_request_id == "req-1"
    assert outcome.record.answered_by == "vibey-vscode"
    job = await PostgresJobRepository(migrated_pool).get(job_id)
    assert job is not None and job.state is JobState.READY
    (event,) = await _answered_events(migrated_pool, project_id)
    assert event == {
        "gate_id": str(gate_id),
        "gate_kind": "approval",
        "job_id": str(job_id),
        "request_id": "req-1",
        "by": "vibey-vscode",
        "account": "adam",
        "answer": {"verdict": "accept"},
    }


async def test_the_same_request_replayed_is_a_no_op_that_writes_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    gate_id, _ = await _parked_gate(migrated_pool, project_id)
    gates = PostgresHumanGateRepository(migrated_pool)
    first = await gates.answer_once(
        gate_id, answer={"choice": [1, 2]}, answered_by="adam", account="adam", request_id="r"
    )

    again = await gates.answer_once(
        gate_id, answer={"choice": (1, 2)}, answered_by="adam", account="adam", request_id="r"
    )

    assert again.replayed
    assert again.record == first.record
    assert len(await _answered_events(migrated_pool, project_id)) == 1


async def test_another_answer_is_refused_and_the_first_stands(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    gate_id, _ = await _parked_gate(migrated_pool, project_id)
    gates = PostgresHumanGateRepository(migrated_pool)
    await gates.answer(gate_id, answer={"verdict": "accept"}, answered_by="adam")

    with pytest.raises(GateAlreadyAnswered, match="a different request answered it first"):
        await gates.answer(gate_id, answer={"verdict": "reject"}, answered_by="mallory")
    with pytest.raises(GateAlreadyAnswered, match="already used for a different answer"):
        stored = await gates.get(gate_id)
        assert stored is not None and stored.answer_request_id is not None
        await gates.answer(
            gate_id,
            answer={"verdict": "reject"},
            answered_by="adam",
            request_id=stored.answer_request_id,
        )

    settled = await gates.get(gate_id)
    assert settled is not None
    assert settled.answer == {"verdict": "accept"}
    assert settled.answered_by == "adam"
    assert len(await _answered_events(migrated_pool, project_id)) == 1


async def test_a_gate_answered_before_request_ids_refuses_every_later_answer(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    async with owner_pool.acquire() as conn:
        gate_id = await conn.fetchval(
            "INSERT INTO human_gate (project_id, kind, prompt, answer, answered_at, answered_by) "
            "VALUES ($1, 'approval', 'go?', '{}'::jsonb, now(), 'cli') RETURNING gate_id",
            project_id,
        )

    with pytest.raises(GateAlreadyAnswered):
        await PostgresHumanGateRepository(migrated_pool).answer_once(
            gate_id, answer={}, answered_by="adam", account="adam", request_id="any"
        )


async def test_an_unknown_gate_is_refused(migrated_pool: asyncpg.Pool) -> None:
    with pytest.raises(UnknownGate):
        await PostgresHumanGateRepository(migrated_pool).answer_once(
            uuid4(), answer={}, answered_by="adam", account=None, request_id="r"
        )


async def test_two_concurrent_answers_land_exactly_one(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The race the compare-and-set exists for: many answers to one gate at once, each
    on its own connection. Exactly one lands, with exactly one event; every other is
    refused, and none overwrites the one that landed."""
    gate_id, _ = await _parked_gate(migrated_pool, project_id)
    gates = PostgresHumanGateRepository(migrated_pool)

    results = await asyncio.gather(
        *(
            gates.answer_once(
                gate_id,
                answer={"choice": f"answer-{n}"},
                answered_by=f"client-{n}",
                account="adam",
                request_id=f"req-{n}",
            )
            for n in range(8)
        ),
        return_exceptions=True,
    )

    landed = [r for r in results if not isinstance(r, BaseException)]
    refused = [r for r in results if isinstance(r, GateAlreadyAnswered)]
    assert len(landed) == 1
    assert len(refused) == 7
    (winner,) = landed
    settled = await gates.get(gate_id)
    assert settled is not None
    assert settled.answer == winner.record.answer
    assert settled.answered_by == winner.record.answered_by
    (event,) = await _answered_events(migrated_pool, project_id)
    assert event["request_id"] == winner.record.answer_request_id


async def test_a_replay_racing_its_own_first_answer_still_lands_once(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """A client that retries before its first attempt returned: both carry one request
    id, so one lands and the other is its replay -- never a refusal, never two events."""
    gate_id, _ = await _parked_gate(migrated_pool, project_id)
    gates = PostgresHumanGateRepository(migrated_pool)

    outcomes = await asyncio.gather(
        *(
            gates.answer_once(
                gate_id, answer={"ok": True}, answered_by="adam", account="adam", request_id="same"
            )
            for _ in range(4)
        )
    )

    assert sorted(o.replayed for o in outcomes) == [False, True, True, True]
    assert len(await _answered_events(migrated_pool, project_id)) == 1


def test_the_draft_refuses_a_phase_this_vibey_does_not_know() -> None:
    now = datetime(2026, 9, 25, tzinfo=UTC)
    project = ProjectRecord(
        project_id=uuid4(),
        name="p",
        repo_path=Path("/tmp/p"),
        phase=UnrecognizedPhase("FUTURE"),
        cycle=1,
        max_cycles=3,
        config={},
        created_at=now,
        updated_at=now,
    )
    gate = _gate_record(project.project_id, now)

    with pytest.raises(WrongPhase, match="will not record an answer"):
        GATE_ANSWERED_DRAFTS.build(project, gate, account="adam", at=now)


def test_the_draft_is_trusted_and_filed_under_the_project() -> None:
    now = datetime(2026, 9, 25, tzinfo=UTC)
    project = ProjectRecord(
        project_id=uuid4(),
        name="p",
        repo_path=Path("/tmp/p"),
        phase=Phase.BUILD,
        cycle=2,
        max_cycles=3,
        config={},
        created_at=now,
        updated_at=now,
    )
    draft = GATE_ANSWERED_DRAFTS.build(
        project, _gate_record(project.project_id, now), account=None, at=now
    )

    assert draft.kind is EventKind.GATE_ANSWERED
    assert draft.provenance is Provenance.TRUSTED
    assert (draft.cycle, draft.phase, draft.job_id, draft.engine_id) == (2, Phase.BUILD, None, None)
    assert draft.payload["job_id"] is None
    assert draft.payload["account"] is None
    assert draft.digest == digest_event(draft.payload)


def _gate_record(project_id: UUID, at: datetime):  # type: ignore[no-untyped-def]
    from vibey.application.dto import HumanGateRecord

    return HumanGateRecord(
        gate_id=uuid4(),
        project_id=project_id,
        job_id=None,
        kind="approval",
        prompt="go?",
        options=(),
        default_answer=None,
        answer={"ok": True},
        raised_at=at,
        timeout_at=None,
        answered_at=at,
        answered_by="adam",
        answer_request_id="r",
    )


def test_a_missing_row_is_a_lookup_error_naming_its_context() -> None:
    """The guard `_record` puts on the project read: the gate's foreign key holds the
    project for as long as the answer's transaction holds the gate, so only a broken
    schema could make it fire -- and then it names what was missing, not a None error."""
    from vibey.infrastructure.db.human_gate_repository import _require

    with pytest.raises(LookupError, match="answer: no project p: expected a row"):
        _require(None, context="answer: no project p")
