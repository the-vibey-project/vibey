# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Abandoning a project against real PostgreSQL, as the application role.

The store runs under `migrated_pool` -- the restricted role production connects as
(ADR-0055) -- so the privileges it needs are the declared ones. One transaction moves the
project into abandoned through the guarded compare-and-set, cancels every unsettled job,
withdraws every open gate and appends the move's `PhaseTransitioned` and one
`GateWithdrawn` per gate; a failure anywhere leaves all of it as it was; a replay writes
nothing; and nothing is deleted.
"""

import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest

from vibey.application.dto import HumanGateRecord, HumanGateRequest, ProjectRecord
from vibey.domain.errors import AbandonmentRefused, GateAlreadyAnswered, UnknownProject
from vibey.domain.job import JobState
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.interfaces import (
    GateWithdrawnDraftBuilderInterface,
    PostgresProjectAbandonmentStoreInterface,
    ProjectTransitionOnConnectionInterface,
)
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.db.project_abandonment_store import (
    GATE_WITHDRAWN_DRAFTS,
    PostgresProjectAbandonmentStore,
)
from vibey.infrastructure.db.project_repository import PostgresProjectRepository
from vibey.infrastructure.engines.loop_events import LOOP_EVENT_MAP
from vibey.infrastructure.engines.tailer import LedgerEventDraft

from .test_job_repository import LEASE, _request

AT = datetime(2026, 9, 29, 12, 0, tzinfo=UTC)
UNSETTLED = ("ready", "leased", "awaiting_human", "awaiting_capacity")
SETTLED = ("succeeded", "failed", "cancelled")


def _store(pool: asyncpg.Pool, **kwargs: object) -> PostgresProjectAbandonmentStore:
    return PostgresProjectAbandonmentStore(
        pool,
        projects=PostgresProjectRepository(pool),
        **kwargs,  # type: ignore[arg-type]
    )


async def _set_phase(pool: asyncpg.Pool, project_id: UUID, phase: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute("UPDATE project SET phase = $2 WHERE id = $1", project_id, phase)


async def _job(pool: asyncpg.Pool, project_id: UUID, state: str) -> UUID:
    """One job in `state`, leased ones with the lease a worker would hold."""
    job = await PostgresJobRepository(pool).enqueue(_request(project_id, subject=state))
    async with pool.acquire() as conn:
        await conn.execute(
            """
            UPDATE job SET state = $2::job_state,
                lease_owner = CASE WHEN $2 = 'leased' THEN 'w1' END,
                lease_expires_at = CASE WHEN $2 = 'leased' THEN now() + interval '30 s' END
            WHERE id = $1
            """,
            job.id,
            state,
        )
    return job.id


async def _gate(pool: asyncpg.Pool, project_id: UUID, job_id: UUID | None, kind: str) -> UUID:
    gate = await PostgresHumanGateRepository(pool).raise_gate(
        project_id, job_id, HumanGateRequest(kind=kind, prompt=f"{kind}?")
    )
    return gate.gate_id


async def _row(pool: asyncpg.Pool, sql: str, *args: object) -> asyncpg.Record:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, *args)
    assert row is not None
    return row


async def _events(pool: asyncpg.Pool, project_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "SELECT seq, kind, cycle, phase::text AS phase, engine_id, job_id, "
                "provenance::text AS provenance, produced_at, payload FROM event "
                "WHERE project_id = $1 ORDER BY seq",
                project_id,
            )
        )


async def _counts(pool: asyncpg.Pool, project_id: UUID) -> tuple[int, int, int]:
    """Events, open gates and unsettled jobs: what an abandonment would change."""
    row = await _row(
        pool,
        """
        SELECT (SELECT count(*) FROM event WHERE project_id = $1) AS events,
               (SELECT count(*) FROM human_gate
                WHERE project_id = $1 AND answered_at IS NULL) AS gates,
               (SELECT count(*) FROM job
                WHERE project_id = $1 AND state::text = ANY($2::text[])) AS jobs
        """,
        project_id,
        list(UNSETTLED),
    )
    return row["events"], row["gates"], row["jobs"]


async def _a_project_mid_build(pool: asyncpg.Pool, project_id: UUID) -> dict[str, UUID]:
    """A project in BUILD with a job in every state, a gate on its parked job, a gate with
    no job, and a gate already answered."""
    await _set_phase(pool, project_id, "build")
    ids = {state: await _job(pool, project_id, state) for state in (*UNSETTLED, *SETTLED)}
    ids["job_gate"] = await _gate(pool, project_id, ids["awaiting_human"], "defect")
    ids["project_gate"] = await _gate(pool, project_id, None, "approval")
    ids["answered_gate"] = await _gate(pool, project_id, ids["succeeded"], "approval")
    await PostgresHumanGateRepository(pool).answer(
        ids["answered_gate"], answer={"verdict": "accept"}, answered_by="adam"
    )
    return ids


def test_the_store_and_its_draft_builder_satisfy_their_seams() -> None:
    assert isinstance(GATE_WITHDRAWN_DRAFTS, GateWithdrawnDraftBuilderInterface)
    assert isinstance(_store(pool=None), PostgresProjectAbandonmentStoreInterface)  # type: ignore[arg-type]
    assert isinstance(
        PostgresProjectRepository(pool=None),  # type: ignore[arg-type]
        ProjectTransitionOnConnectionInterface,
    )


def test_no_engine_event_is_ever_translated_into_a_withdrawal() -> None:
    """Only vibey's own command writes the kind: no loop's event type maps onto it."""
    for engine_map in LOOP_EVENT_MAP.values():
        assert EventKind.GATE_WITHDRAWN not in engine_map.values()


async def test_abandoning_moves_the_phase_cancels_the_jobs_and_withdraws_the_gates_in_one_step(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    ids = await _a_project_mid_build(migrated_pool, project_id)
    before = await _events(migrated_pool, project_id)

    report = await _store(migrated_pool).abandon(
        project_id, reason="built on a foreign spec", by="vibey-vscode", account="adam"
    )

    # The project.
    assert (report.left, report.project.phase) == (Phase.BUILD, Phase.ABANDONED)
    assert report.written and not report.already_abandoned
    assert (report.reason, report.by, report.account) == (
        "built on a foreign spec",
        "vibey-vscode",
        "adam",
    )
    stored = await _row(
        migrated_pool,
        "SELECT phase::text AS phase, updated_at FROM project WHERE id = $1",
        project_id,
    )
    assert stored["phase"] == "abandoned"
    # Every unsettled job cancelled, its lease cleared, and reported as it stood before.
    assert [(job.id, job.state) for job in report.jobs] == [
        (ids[state], JobState(state)) for state in UNSETTLED
    ]
    for state in UNSETTLED:
        job = await _row(
            migrated_pool,
            "SELECT state::text AS state, lease_owner, lease_expires_at, updated_at "
            "FROM job WHERE id = $1",
            ids[state],
        )
        assert (job["state"], job["lease_owner"], job["lease_expires_at"]) == (
            "cancelled",
            None,
            None,
        )
        assert job["updated_at"] == stored["updated_at"]
    # Settled jobs are history: left exactly as they were.
    for state in SETTLED:
        job = await _row(
            migrated_pool, "SELECT state::text AS s FROM job WHERE id = $1", ids[state]
        )
        assert job["s"] == state
    # Every open gate withdrawn, never deleted; the answered one untouched.
    assert [gate.gate_id for gate in report.gates] == [ids["job_gate"], ids["project_gate"]]
    gates = PostgresHumanGateRepository(migrated_pool)
    for key in ("job_gate", "project_gate"):
        gate = await gates.get(ids[key])
        assert gate is not None
        assert gate.answer == {"withdrawn": True, "reason": "project abandoned"}
        assert gate.answered_by == "vibey-vscode"
        assert gate.answer_request_id == f"abandon:{project_id}"
        assert gate.answered_at == stored["updated_at"]
    answered = await gates.get(ids["answered_gate"])
    assert answered is not None and answered.answer == {"verdict": "accept"}
    assert await gates.open_for_project(project_id) == ()
    # The record: the move, then one withdrawal per gate, appended after what was there.
    events = await _events(migrated_pool, project_id)
    assert events[: len(before)] == before
    move, *withdrawals = events[len(before) :]
    assert move["kind"] == EventKind.PHASE_TRANSITIONED.value
    assert json.loads(move["payload"]) == {
        "from": "build",
        "to": "abandoned",
        "cycle": 1,
        "guard": "operator abandoned",
        "reason": "built on a foreign spec",
        "by": "vibey-vscode",
        "account": "adam",
        "cancelled_jobs": [str(ids[state]) for state in UNSETTLED],
        "withdrawn_gates": [str(ids["job_gate"]), str(ids["project_gate"])],
    }
    assert [json.loads(event["payload"]) for event in withdrawals] == [
        {
            "gate_id": str(ids[key]),
            "gate_kind": kind,
            "job_id": job,
            "request_id": f"abandon:{project_id}",
            "reason": "project abandoned",
            "by": "vibey-vscode",
            "account": "adam",
        }
        for key, kind, job in (
            ("job_gate", "defect", str(ids["awaiting_human"])),
            ("project_gate", "approval", None),
        )
    ]
    for event in (move, *withdrawals):
        assert (event["phase"], event["cycle"], event["provenance"]) == ("abandoned", 1, "trusted")
        assert (event["engine_id"], event["job_id"]) == (None, None)
        assert event["produced_at"] == stored["updated_at"]
    assert {event["kind"] for event in withdrawals} == {EventKind.GATE_WITHDRAWN.value}


async def test_a_project_with_nothing_running_is_still_moved_and_recorded(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _set_phase(migrated_pool, project_id, "design")

    report = await _store(migrated_pool).abandon(
        project_id, reason="superseded", by="adam", account="adam"
    )

    assert (report.left, report.jobs, report.gates) == (Phase.DESIGN, (), ())
    (move,) = await _events(migrated_pool, project_id)
    payload = json.loads(move["payload"])
    assert (payload["from"], payload["cancelled_jobs"], payload["withdrawn_gates"]) == (
        "design",
        [],
        [],
    )


async def test_abandoning_twice_is_a_no_op_that_writes_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _a_project_mid_build(migrated_pool, project_id)
    store = _store(migrated_pool)
    await store.abandon(project_id, reason="foreign spec", by="adam", account="adam")
    settled = await _counts(migrated_pool, project_id)
    updated = await _row(migrated_pool, "SELECT updated_at FROM project WHERE id = $1", project_id)

    again = await store.abandon(project_id, reason="again", by="mallory", account="mallory")

    assert again.already_abandoned and not again.written
    assert (again.left, again.project.phase, again.jobs, again.gates) == (
        Phase.ABANDONED,
        Phase.ABANDONED,
        (),
        (),
    )
    assert (again.reason, again.by, again.account) == ("again", "mallory", "mallory")
    assert await _counts(migrated_pool, project_id) == settled
    assert (await _row(migrated_pool, "SELECT updated_at FROM project WHERE id = $1", project_id))[
        "updated_at"
    ] == updated["updated_at"]


async def test_two_abandonments_racing_serialise_and_exactly_one_writes(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _a_project_mid_build(migrated_pool, project_id)
    store = _store(migrated_pool)

    reports = await asyncio.gather(
        *(store.abandon(project_id, reason=f"r{i}", by="adam", account="adam") for i in range(4))
    )

    assert sorted(report.written for report in reports) == [False, False, False, True]
    events = await PostgresLedgerRepository(migrated_pool).all_for_project(project_id)
    moves = [e for e in events if e.kind is EventKind.PHASE_TRANSITIONED]
    assert len(moves) == 1 and moves[0].provenance is Provenance.TRUSTED


@pytest.mark.parametrize(
    ("phase", "why"),
    [("done", "the project is done"), ("intake", "intake -> abandoned is not a legal edge")],
)
async def test_a_project_that_cannot_be_abandoned_is_refused_and_nothing_is_written(
    migrated_pool: asyncpg.Pool, project_id: UUID, phase: str, why: str
) -> None:
    await _a_project_mid_build(migrated_pool, project_id)
    await _set_phase(migrated_pool, project_id, phase)
    before = await _counts(migrated_pool, project_id)
    store = _store(migrated_pool)

    with pytest.raises(AbandonmentRefused, match=why):
        await store.abandon(project_id, reason="no", by="adam", account="adam")
    with pytest.raises(AbandonmentRefused, match=why):
        await store.preview(project_id)

    assert await _counts(migrated_pool, project_id) == before
    stored = await _row(
        migrated_pool, "SELECT phase::text AS p FROM project WHERE id = $1", project_id
    )
    assert stored["p"] == phase


async def test_an_unknown_project_is_named(migrated_pool: asyncpg.Pool) -> None:
    missing = UUID(int=7)
    store = _store(migrated_pool)
    with pytest.raises(UnknownProject, match=str(missing)):
        await store.abandon(missing, reason="no", by="adam", account="adam")
    with pytest.raises(UnknownProject, match=str(missing)):
        await store.preview(missing)


async def test_a_failure_part_way_leaves_the_project_its_jobs_and_its_gates_as_they_were(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The last write of the transaction fails: the move, the cancellations, the
    withdrawals and the `PhaseTransitioned` already written roll back with it."""
    await _a_project_mid_build(migrated_pool, project_id)
    before = await _counts(migrated_pool, project_id)

    class _BrokenAppender:
        async def append(self, conn: asyncpg.Connection, draft: LedgerEventDraft) -> None:
            raise RuntimeError("the disk filled")

    with pytest.raises(RuntimeError, match="the disk filled"):
        await _store(migrated_pool, appender=_BrokenAppender()).abandon(
            project_id, reason="no", by="adam", account="adam"
        )

    assert await _counts(migrated_pool, project_id) == before
    stored = await _row(
        migrated_pool, "SELECT phase::text AS p FROM project WHERE id = $1", project_id
    )
    assert stored["p"] == "build"


async def test_a_dry_run_lists_what_would_stop_and_writes_nothing(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    ids = await _a_project_mid_build(migrated_pool, project_id)
    before = await _counts(migrated_pool, project_id)

    report = await _store(migrated_pool).preview(project_id)

    assert not report.written and not report.already_abandoned
    assert (report.left, report.project.phase) == (Phase.BUILD, Phase.BUILD)
    assert [job.id for job in report.jobs] == [ids[state] for state in UNSETTLED]
    assert [gate.gate_id for gate in report.gates] == [ids["job_gate"], ids["project_gate"]]
    assert await _counts(migrated_pool, project_id) == before


async def test_a_dry_run_of_an_abandoned_project_says_so(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _set_phase(migrated_pool, project_id, "abandoned")

    report = await _store(migrated_pool).preview(project_id)

    assert report.already_abandoned and not report.written
    assert (report.jobs, report.gates) == ((), ())


async def test_a_worker_still_running_a_cancelled_job_cannot_revive_it(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    await _set_phase(migrated_pool, project_id, "build")
    jobs = PostgresJobRepository(migrated_pool)
    job = await jobs.enqueue(_request(project_id))
    assert await jobs.claim(project_id, owner="w1", lease=LEASE) is not None

    await _store(migrated_pool).abandon(project_id, reason="stop", by="adam", account="adam")

    assert not await jobs.heartbeat(job.id, owner="w1", lease=LEASE)
    assert not await jobs.nack(job.id, owner="w1", error={"message": "late"})
    assert not await jobs.ack(job.id, owner="w1")
    assert not await jobs.park(job.id, owner="w1")
    stored = await jobs.get(job.id)
    assert stored is not None and stored.state is JobState.CANCELLED


async def test_a_withdrawn_gate_refuses_a_later_answer_as_a_second_one(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    ids = await _a_project_mid_build(migrated_pool, project_id)
    await _store(migrated_pool).abandon(project_id, reason="stop", by="adam", account="adam")

    with pytest.raises(GateAlreadyAnswered, match="a different request answered it first"):
        await PostgresHumanGateRepository(migrated_pool).answer(
            ids["job_gate"], answer={"choice": "requeue"}, answered_by="adam"
        )
    job = await PostgresJobRepository(migrated_pool).get(ids["awaiting_human"])
    assert job is not None and job.state is JobState.CANCELLED


async def test_the_claim_never_hands_out_a_job_of_an_abandoned_project(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """A handler still running when the project was abandoned may enqueue its follow-up
    after the abandonment committed: the job exists, and it never runs."""
    await _set_phase(migrated_pool, project_id, "build")
    await _store(migrated_pool).abandon(project_id, reason="stop", by="adam", account="adam")
    jobs = PostgresJobRepository(migrated_pool)
    straggler = await jobs.enqueue(_request(project_id, subject="straggler"))

    assert await jobs.claim(project_id, owner="w1", lease=LEASE) is None
    assert project_id not in await jobs.claimable_projects()
    stored = await jobs.get(straggler.id)
    assert stored is not None and stored.state is JobState.READY


async def test_the_move_is_announced_once_it_has_committed(
    migrated_pool: asyncpg.Pool, project_id: UUID, tmp_path: Path
) -> None:
    sent: list[dict[str, object]] = []

    class _Notifications:
        async def notify(self, **kwargs: object) -> dict[str, object]:
            sent.append(kwargs)
            return {"enabled": True}

    projects = PostgresProjectRepository(migrated_pool, notifications=_Notifications())
    project = await projects.create("notified", tmp_path, max_cycles=1, config={})
    await _set_phase(migrated_pool, project.project_id, "review")
    store = PostgresProjectAbandonmentStore(migrated_pool, projects=projects)

    await store.abandon(project.project_id, reason="stop", by="adam", account="adam")

    (notice,) = sent
    assert (notice["kind"], notice["message"]) == (
        "phase_transitioned",
        "Project entered abandoned",
    )
    assert notice["payload"] == {"from": "review", "to": "abandoned", "cycle": 1}


def test_the_withdrawal_draft_is_filed_under_abandoned_at_the_move_s_own_time(
    project_record: ProjectRecord,
) -> None:
    gate = _gate_record(project_record.project_id)
    draft = GATE_WITHDRAWN_DRAFTS.build(project_record, gate, by="adam", account="adam")

    assert draft.kind is EventKind.GATE_WITHDRAWN
    assert (draft.phase, draft.cycle, draft.produced_at) == (
        Phase.ABANDONED,
        project_record.cycle,
        project_record.updated_at,
    )
    assert draft.provenance is Provenance.TRUSTED
    assert draft.payload["gate_id"] == str(gate.gate_id)


@pytest.fixture
def project_record() -> ProjectRecord:
    return ProjectRecord(
        project_id=UUID(int=1),
        name="greeter",
        repo_path=Path("/srv/greeter"),
        phase=Phase.ABANDONED,
        cycle=2,
        max_cycles=3,
        config={},
        created_at=AT,
        updated_at=AT + timedelta(minutes=5),
    )


def _gate_record(project_id: UUID) -> HumanGateRecord:
    return HumanGateRecord(
        gate_id=UUID(int=2),
        project_id=project_id,
        job_id=None,
        kind="approval",
        prompt="ship it?",
        options=(),
        default_answer=None,
        answer={"withdrawn": True},
        raised_at=AT,
        timeout_at=None,
        answered_at=AT,
        answered_by="adam",
    )
