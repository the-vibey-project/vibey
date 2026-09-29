# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Gate notices on a real ledger: recorded once per gate and notice number, fleet-wide,
and read back by project."""

import asyncio
import json
from uuid import UUID, uuid4

import asyncpg
import pytest

from vibey.domain.gate_notice import GateNotice, NoticeReason
from vibey.infrastructure.db.gate_notice_store import (
    GATE_NOTICE_DRAFTS,
    PostgresGateNoticeStore,
)
from vibey.infrastructure.db.interfaces import (
    GateNoticeDraftBuilderInterface,
    PostgresGateNoticeStoreInterface,
)


def _notice(project_id: UUID, gate_id: UUID, number: int, **values: object) -> GateNotice:
    return GateNotice(
        project_id=project_id,
        gate_id=gate_id,
        gate_kind="approval",
        job_id=uuid4(),
        notice=number,
        **values,  # type: ignore[arg-type]
    )


async def _events(pool: asyncpg.Pool, project_id: UUID) -> list[asyncpg.Record]:
    async with pool.acquire() as conn:
        return list(
            await conn.fetch(
                "SELECT kind, job_id, provenance::text AS provenance, payload FROM event "
                "WHERE project_id = $1 ORDER BY seq",
                project_id,
            )
        )


def test_the_store_and_its_drafts_satisfy_their_declared_seams(
    migrated_pool: asyncpg.Pool,
) -> None:
    assert isinstance(PostgresGateNoticeStore(migrated_pool), PostgresGateNoticeStoreInterface)
    assert isinstance(GATE_NOTICE_DRAFTS, GateNoticeDraftBuilderInterface)


async def test_each_notice_is_recorded_once(migrated_pool: asyncpg.Pool, project_id: UUID) -> None:
    store = PostgresGateNoticeStore(migrated_pool)
    gate_id = uuid4()
    delivered = _notice(project_id, gate_id, 0, channels={"desktop": True})
    undeliverable = _notice(
        project_id, gate_id, 1, reason=NoticeReason.DISABLED, detail="nobody will be told"
    )

    assert await store.record(delivered) is True
    assert await store.record(delivered) is False  # a replay records nothing
    # Delivered or not, one record per gate and notice number.
    assert await store.record(_notice(project_id, gate_id, 0, reason=NoticeReason.FAILED)) is False
    assert await store.record(undeliverable) is True

    events = await _events(migrated_pool, project_id)
    assert [row["kind"] for row in events] == ["GateNotified", "GateNoticeUndeliverable"]
    assert {row["provenance"] for row in events} == {"trusted"}
    # Filed like GateAnswered: the gate's job in the payload, none of its own.
    assert {row["job_id"] for row in events} == {None}
    assert json.loads(events[1]["payload"])["reason"] == "disabled"


async def test_two_sweeps_racing_on_one_notice_record_it_once(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresGateNoticeStore(migrated_pool)
    notice = _notice(project_id, uuid4(), 3)
    results = await asyncio.gather(*(store.record(notice) for _ in range(4)))
    assert sorted(results) == [False, False, False, True]


async def test_the_notices_on_record_are_read_by_gate(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    store = PostgresGateNoticeStore(migrated_pool)
    first, second = uuid4(), uuid4()
    for gate_id, number in ((first, 0), (first, 1), (second, 0)):
        await store.record(_notice(project_id, gate_id, number))
    # A payload no vibey wrote as a notice is skipped, not guessed at.
    async with migrated_pool.acquire() as conn:
        await conn.execute(
            """
            SELECT append_event($1, 1, 'build', 'GateNotified', NULL, NULL, NULL, $2,
                                'trusted', '{"gate_id": "not-a-uuid", "notice": "x"}'::jsonb,
                                'digest')
            """,
            project_id,
            uuid4(),
        )

    assert await store.recorded(project_id) == {
        first: frozenset({0, 1}),
        second: frozenset({0}),
    }
    assert await store.recorded(uuid4()) == {}


async def test_a_notice_for_a_project_that_is_gone_is_refused(
    migrated_pool: asyncpg.Pool,
) -> None:
    with pytest.raises(LookupError, match="no project"):
        await PostgresGateNoticeStore(migrated_pool).record(_notice(uuid4(), uuid4(), 0))
