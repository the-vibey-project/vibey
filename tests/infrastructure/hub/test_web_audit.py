# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The hub's web tools on the ledger, against real PostgreSQL (ADR-0102, SP-ACP Task 9b): a use
is recorded on the named project's ledger, else on every project's, and found again by kind --
what `vibey ledger search --kind WebFetched` and `vibey_ledger` read.

Module-level test functions rather than a class with an interface beside it (ADR-0016)."""

import datetime as dt
import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import asyncpg
import pytest

from tests.db_roles import TestDatabaseRoles
from vibey.application.hub.interfaces.web_tools_service_interface import WebAuditPortInterface
from vibey.bootstrap import build_app, migrations_dir
from vibey.domain.errors import UnknownProject, WrongPhase
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.ledger_query import LedgerQuery
from vibey.domain.web_tools import WebToolUnavailable
from vibey.infrastructure.db.ledger_search_repository import PostgresLedgerSearchRepository
from vibey.infrastructure.hub.web_audit import PostgresWebAudit

AT = dt.datetime(2026, 11, 22, 12, 0, tzinfo=dt.UTC)
FETCH = {
    "tool": "fetch",
    "principal": "agent",
    "outcome": "ok",
    "backend": "direct",
    "hosts": ["docs.example"],
}


@pytest.fixture
async def _an_empty_database(monkeypatch: pytest.MonkeyPatch) -> None:
    owner = os.environ["VIBEY_TEST_DATABASE_URL"]
    conn = await asyncpg.connect(owner)
    try:
        await conn.execute("DROP SCHEMA IF EXISTS public CASCADE")
        await conn.execute("CREATE SCHEMA public")
    finally:
        await conn.close()
    await TestDatabaseRoles.from_environ(os.environ).restore(owner, migrations_dir())
    monkeypatch.setenv("VIBEY_PG_URL", os.environ["VIBEY_TEST_APP_DATABASE_URL"])


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_with_no_project_there_is_no_ledger_to_record_a_use_in() -> None:
    async with build_app() as resources:
        audit = PostgresWebAudit(resources.ledger._pool)
        assert isinstance(audit, WebAuditPortInterface)
        with pytest.raises(WebToolUnavailable, match="no project ledger"):
            await audit.ready(None)
        with pytest.raises(UnknownProject):
            await audit.ready(uuid4())
        with pytest.raises(WebToolUnavailable, match="no project ledger"):
            await audit.record(EventKind.WEB_SEARCHED, {"tool": "search"}, AT, None)


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_use_is_recorded_on_the_named_project_alone_and_found_by_its_kind(
    tmp_path: Path,
) -> None:
    async with build_app() as resources:
        named = await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        other = await resources.projects.create("b", tmp_path / "b", max_cycles=1, config={})
        audit = PostgresWebAudit(resources.ledger._pool)
        await audit.ready(named.project_id)
        assert await audit.record(EventKind.WEB_FETCHED, FETCH, AT, named.project_id) == 1
        events = await resources.ledger.all_for_project(named.project_id)
        (fetched,) = [e for e in events if e.kind is EventKind.WEB_FETCHED]
        assert fetched.payload == FETCH
        assert fetched.provenance is Provenance.TRUSTED
        assert fetched.engine_id is None and fetched.job_id is None
        others = await resources.ledger.all_for_project(other.project_id)
        assert not [e for e in others if e.kind is EventKind.WEB_FETCHED]
        found = await PostgresLedgerSearchRepository(resources.ledger._pool).search(
            named.project_id, LedgerQuery(kinds=frozenset({EventKind.WEB_FETCHED}))
        )
        assert [e.payload for e in found.events] == [FETCH]


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_use_no_project_was_named_for_is_recorded_on_every_projects_ledger(
    tmp_path: Path,
) -> None:
    async with build_app() as resources:
        first = await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        second = await resources.projects.create("b", tmp_path / "b", max_cycles=1, config={})
        audit = PostgresWebAudit(resources.ledger._pool)
        await audit.ready(None)
        payload = {"tool": "search", "principal": "agent", "outcome": "ok", "backend": "searxng"}
        assert await audit.record(EventKind.WEB_SEARCHED, payload, AT, None) == 2
        for project in (first, second):
            events = await resources.ledger.all_for_project(project.project_id)
            assert [e.payload for e in events if e.kind is EventKind.WEB_SEARCHED] == [payload]


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_project_named_that_does_not_exist_is_never_written(tmp_path: Path) -> None:
    async with build_app() as resources:
        await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        audit = PostgresWebAudit(resources.ledger._pool)
        with pytest.raises(UnknownProject):
            await audit.record(EventKind.WEB_FETCHED, FETCH, AT, uuid4())


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_project_in_an_unknown_phase_refuses_the_whole_record(tmp_path: Path) -> None:
    async with build_app() as resources:
        await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})

        class Rows:
            def to_record(self, row: Any) -> Any:
                return SimpleNamespace(project_id=row["id"], cycle=1, phase=_Unknown())

        audit = PostgresWebAudit(resources.ledger._pool, rows=Rows())  # type: ignore[arg-type]
        with pytest.raises(WrongPhase):
            await audit.record(EventKind.WEB_SEARCHED, {}, AT, None)


class _Unknown:
    value = "FUTURE"
