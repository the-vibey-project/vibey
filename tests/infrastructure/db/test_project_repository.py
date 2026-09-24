# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import logging
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import asyncpg
import pytest

from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.db.project_repository import PostgresProjectRepository
from vibey.infrastructure.interfaces import PostgresProjectRepositoryInterface

CREATED = datetime(2026, 9, 24, 9, 0, tzinfo=UTC)


async def _created_at(owner: asyncpg.Pool, project_id: UUID, at: datetime) -> None:
    """Pins a project's creation time, as the owner: the order under test is then
    `created_at`'s, never the order the rows happened to be inserted in."""
    async with owner.acquire() as conn:
        await conn.execute("UPDATE project SET created_at = $2 WHERE id = $1", project_id, at)


async def test_create_get_and_transition_project(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    created = await repo.create(
        "demo", tmp_path, max_cycles=7, config={"project": {"name": "demo"}}
    )
    assert isinstance(created.project_id, UUID)
    assert created.phase is Phase.INTAKE
    assert created.cycle == 1
    assert created.max_cycles == 7

    same = await repo.get(created.project_id)
    assert same == created

    transitioned = await repo.transition(created.project_id, expected=Phase.INTAKE, to=Phase.DESIGN)
    assert transitioned.phase is Phase.DESIGN
    assert transitioned.cycle == 1

    # Transition with cycle increment
    transitioned_loop = await repo.transition(
        created.project_id, expected=Phase.DESIGN, to=Phase.BUILD, cycle=2
    )
    assert transitioned_loop.phase is Phase.BUILD
    assert transitioned_loop.cycle == 2


async def test_transition_rejects_stale_expected_phase(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    try:
        await repo.transition(project_id, expected=Phase.DESIGN, to=Phase.BUILD)
    except ValueError as exc:
        assert "expected phase" in str(exc)
    else:
        raise AssertionError("expected stale transition rejection")


async def test_every_transition_lands_a_phase_transitioned_event(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    """The ledger is the only evidence a project's path through the six
    phases ever happened, so the move and its event are written together."""
    repo = PostgresProjectRepository(migrated_pool)
    ledger = PostgresLedgerRepository(migrated_pool)
    created = await repo.create("ledgered", tmp_path, max_cycles=7, config={})

    settled = await repo.transition(
        created.project_id, expected=Phase.INTAKE, to=Phase.DESIGN, guard="design accepted"
    )

    events = await ledger.all_for_project(created.project_id)
    assert [event.kind for event in events] == [EventKind.PHASE_TRANSITIONED]
    event = events[0]
    assert event.payload == {
        "from": "intake",
        "to": "design",
        "cycle": 1,
        "guard": "design accepted",
    }
    # Filed under the phase the project is now in, with the cycle and the
    # timestamp the same UPDATE returned -- row and event are one snapshot.
    assert event.phase is Phase.DESIGN
    assert event.cycle == 1
    assert event.produced_at == settled.updated_at
    assert event.provenance is Provenance.TRUSTED
    assert event.engine_id is None
    assert event.job_id is None


async def test_a_cycle_bumping_transition_records_the_new_cycle_and_no_guard(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    ledger = PostgresLedgerRepository(migrated_pool)
    created = await repo.create("looped", tmp_path, max_cycles=7, config={})
    await repo.transition(created.project_id, expected=Phase.INTAKE, to=Phase.DESIGN)

    await repo.transition(created.project_id, expected=Phase.DESIGN, to=Phase.BUILD, cycle=2)

    events = await ledger.all_for_project(created.project_id)
    assert [event.payload for event in events] == [
        {"from": "intake", "to": "design", "cycle": 1, "guard": None},
        {"from": "design", "to": "build", "cycle": 2, "guard": None},
    ]
    assert [event.seq for event in events] == [1, 2]


async def test_phase_transitions_notify_the_configured_project_sink(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    calls: list[dict[str, object]] = []

    class _Notifications:
        async def notify(self, **kwargs: object) -> dict[str, object]:
            calls.append(kwargs)
            return {"enabled": True}

    config = {
        "notifications": {
            "enabled": True,
            "desktop": False,
            "webhooks": [{"url": "https://example.test/hook"}],
        }
    }
    repo = PostgresProjectRepository(migrated_pool, notifications=_Notifications())
    created = await repo.create("notified", tmp_path, max_cycles=1, config=config)

    await repo.transition(created.project_id, expected=Phase.INTAKE, to=Phase.DESIGN)
    await repo.transition(created.project_id, expected=Phase.DESIGN, to=Phase.DONE)

    assert [call["kind"] for call in calls] == ["phase_transitioned", "run_completed"]
    assert calls[0]["config"] == config
    assert calls[1]["payload"] == {"from": "design", "to": "done", "cycle": 1}


async def test_failed_phase_notification_is_logged_without_rolling_back(
    migrated_pool: asyncpg.Pool, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    class _Notifications:
        async def notify(self, **kwargs: object) -> dict[str, object]:
            return {"enabled": True, "desktop": False, "webhooks": [False]}

    config = {"notifications": {"enabled": True}}
    repo = PostgresProjectRepository(migrated_pool, notifications=_Notifications())
    created = await repo.create("logged", tmp_path, max_cycles=1, config=config)

    with caplog.at_level(logging.WARNING, logger="vibey.infrastructure.db.project_repository"):
        settled = await repo.transition(created.project_id, expected=Phase.INTAKE, to=Phase.DESIGN)

    assert settled.phase is Phase.DESIGN
    assert "notification delivery failed" in caplog.text


def test_notification_failure_recognizes_reported_errors() -> None:
    assert PostgresProjectRepository._notification_failed(
        {"enabled": True, "error": "webhook unavailable"}, {}
    )


async def test_notification_exception_is_logged_without_rolling_back(
    migrated_pool: asyncpg.Pool, tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    class _Notifications:
        async def notify(self, **kwargs: object) -> dict[str, object]:
            raise RuntimeError("notification service is down")

    repo = PostgresProjectRepository(migrated_pool, notifications=_Notifications())
    created = await repo.create("raised", tmp_path, max_cycles=1, config={})

    with caplog.at_level(logging.WARNING, logger="vibey.infrastructure.db.project_repository"):
        settled = await repo.transition(created.project_id, expected=Phase.INTAKE, to=Phase.DESIGN)

    assert settled.phase is Phase.DESIGN
    assert "notification delivery raised" in caplog.text


async def test_a_rejected_transition_writes_no_event(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    ledger = PostgresLedgerRepository(migrated_pool)

    with pytest.raises(ValueError, match="expected phase"):
        await repo.transition(project_id, expected=Phase.DESIGN, to=Phase.BUILD)

    assert await ledger.all_for_project(project_id) == ()


async def test_a_failed_append_rolls_the_phase_change_back(
    migrated_pool: asyncpg.Pool, project_id: UUID
) -> None:
    """The proof that both writes share one transaction: if the event cannot
    be written, the phase must not have moved either."""

    class _ExplodingAppender:
        async def append(self, conn: object, draft: object) -> LedgerEvent:
            raise RuntimeError("ledger is down")

    # Substituted AT THE SEAM the repository declares, not by assigning over a
    # private attribute: the test depends on the EventAppender contract, so
    # renaming the field cannot quietly turn this into a test of nothing.
    repo = PostgresProjectRepository(migrated_pool, appender=_ExplodingAppender())

    with pytest.raises(RuntimeError, match="ledger is down"):
        await repo.transition(project_id, expected=Phase.INTAKE, to=Phase.DESIGN)

    unchanged = await repo.get(project_id)
    assert unchanged is not None
    assert unchanged.phase is Phase.INTAKE


async def test_get_missing_project_returns_none(migrated_pool: asyncpg.Pool) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    assert await repo.get(UUID(int=0)) is None


async def test_get_latest_returns_none_when_no_projects_exist(
    migrated_pool: asyncpg.Pool,
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    assert await repo.get_latest() is None


async def test_get_latest_returns_most_recent_project(
    migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    _first = await repo.create("first", tmp_path / "a", max_cycles=1, config={})
    second = await repo.create("second", tmp_path / "b", max_cycles=1, config={})

    latest = await repo.get_latest()
    assert latest is not None
    assert latest.project_id == second.project_id


async def test_create_raises_lookup_error_when_fetchrow_returns_none() -> None:
    class _NullConn:
        async def fetchrow(self, *a: object, **kw: object) -> None:
            return None

    class _NullPool:
        def acquire(self) -> "_NullPool":
            return self

        async def __aenter__(self) -> _NullConn:
            return _NullConn()

        async def __aexit__(self, *a: object) -> None:
            pass

    repo = PostgresProjectRepository(_NullPool())  # type: ignore[arg-type]
    with pytest.raises(LookupError, match="project insert returned no row"):
        await repo.create("test", Path("/tmp/test"), max_cycles=1, config={})


async def test_the_repository_satisfies_its_interface(migrated_pool: asyncpg.Pool) -> None:
    assert isinstance(PostgresProjectRepository(migrated_pool), PostgresProjectRepositoryInterface)


async def test_list_all_is_empty_when_no_project_exists(migrated_pool: asyncpg.Pool) -> None:
    assert await PostgresProjectRepository(migrated_pool).list_all() == ()


async def test_list_all_lists_every_project_newest_first(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    first = await repo.create("first", tmp_path / "a", max_cycles=1, config={})
    second = await repo.create("second", tmp_path / "b", max_cycles=2, config={})
    third = await repo.create("third", tmp_path / "c", max_cycles=3, config={})
    # Created in one order, dated in another: the listing follows the dates.
    await _created_at(owner_pool, first.project_id, CREATED + timedelta(minutes=2))
    await _created_at(owner_pool, second.project_id, CREATED)
    await _created_at(owner_pool, third.project_id, CREATED + timedelta(minutes=1))

    listed = await repo.list_all()

    assert [project.name for project in listed] == ["first", "third", "second"]
    assert list(listed) == [await repo.get(project.project_id) for project in listed]


async def test_list_all_breaks_a_created_at_tie_by_id(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    repo = PostgresProjectRepository(migrated_pool)
    one = await repo.create("one", tmp_path / "a", max_cycles=1, config={})
    two = await repo.create("two", tmp_path / "b", max_cycles=1, config={})
    for project in (one, two):
        await _created_at(owner_pool, project.project_id, CREATED)

    listed = await repo.list_all()

    assert [project.project_id for project in listed] == sorted(
        (one.project_id, two.project_id), reverse=True
    )


async def test_list_all_reads_a_phase_a_newer_vibey_wrote_as_its_stored_text(
    owner_pool: asyncpg.Pool, migrated_pool: asyncpg.Pool, tmp_path: Path
) -> None:
    """vibey#287: a phase this vibey has no member for is listed, never a crash."""
    repo = PostgresProjectRepository(migrated_pool)
    created = await repo.create("from-the-future", tmp_path, max_cycles=1, config={})
    # ALTER TYPE is the owner's (ADR-0055); the application role may not.
    async with owner_pool.acquire() as conn:
        await conn.execute("ALTER TYPE phase ADD VALUE IF NOT EXISTS 'future_phase_listing'")
        await conn.execute(
            "UPDATE project SET phase = 'future_phase_listing'::phase WHERE id = $1",
            created.project_id,
        )

    (listed,) = await repo.list_all()

    assert listed.project_id == created.project_id
    assert listed.phase == UnrecognizedPhase("future_phase_listing")
