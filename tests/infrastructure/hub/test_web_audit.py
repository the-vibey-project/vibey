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
from vibey.domain.errors import UnknownProject
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
        for named in (None, uuid4()):
            with pytest.raises(WebToolUnavailable, match="no project ledger"):
                await audit.ready(named)
            with pytest.raises(WebToolUnavailable, match="no project ledger"):
                await audit.record(EventKind.WEB_SEARCHED, {"tool": "search"}, AT, named)


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_use_is_recorded_on_the_latest_project_whatever_the_caller_names(
    tmp_path: Path,
) -> None:
    """A model steered to name an old project cannot keep the record out of the person's default
    view: the latest project's ledger, which `vibey ledger search` reads with no project named,
    always has it; the named one has it too."""
    async with build_app() as resources:
        old = await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        middle = await resources.projects.create("b", tmp_path / "b", max_cycles=1, config={})
        latest = await resources.projects.create("c", tmp_path / "c", max_cycles=1, config={})
        audit = PostgresWebAudit(resources.ledger._pool)
        await audit.ready(old.project_id)
        assert await audit.record(EventKind.WEB_FETCHED, FETCH, AT, old.project_id) == 2
        search = PostgresLedgerSearchRepository(resources.ledger._pool)
        for project in (old, latest):
            found = await search.search(
                project.project_id, LedgerQuery(kinds=frozenset({EventKind.WEB_FETCHED}))
            )
            assert [e.payload for e in found.events] == [FETCH]
            (fetched,) = found.events
            assert fetched.provenance is Provenance.TRUSTED
            assert fetched.engine_id is None and fetched.job_id is None
        # A project neither latest nor named is not written.
        between = await resources.ledger.all_for_project(middle.project_id)
        assert not [e for e in between if e.kind is EventKind.WEB_FETCHED]


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_no_project_named_or_the_latest_named_is_one_record_on_the_latest(
    tmp_path: Path,
) -> None:
    async with build_app() as resources:
        first = await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        second = await resources.projects.create("b", tmp_path / "b", max_cycles=1, config={})
        audit = PostgresWebAudit(resources.ledger._pool)
        await audit.ready(None)
        payload = {"tool": "search", "principal": "agent", "outcome": "ok", "backend": "searxng"}
        assert await audit.record(EventKind.WEB_SEARCHED, payload, AT, None) == 1
        assert await audit.record(EventKind.WEB_SEARCHED, payload, AT, second.project_id) == 1
        kinds = {EventKind.WEB_SEARCHED}
        mine = await resources.ledger.all_for_project(second.project_id)
        assert [e.payload for e in mine if e.kind in kinds] == [payload, payload]
        others = await resources.ledger.all_for_project(first.project_id)
        assert not [e for e in others if e.kind in kinds]


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_project_named_that_does_not_exist_is_never_written(tmp_path: Path) -> None:
    async with build_app() as resources:
        await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})
        audit = PostgresWebAudit(resources.ledger._pool)
        with pytest.raises(UnknownProject):
            await audit.ready(uuid4())
        with pytest.raises(UnknownProject):
            await audit.record(EventKind.WEB_FETCHED, FETCH, AT, uuid4())


@pytest.mark.integration
@pytest.mark.usefixtures("_an_empty_database")
async def test_a_project_in_an_unknown_phase_is_refused_before_the_act_and_at_the_write(
    tmp_path: Path,
) -> None:
    async with build_app() as resources:
        await resources.projects.create("a", tmp_path / "a", max_cycles=1, config={})

        class Rows:
            def to_record(self, row: Any) -> Any:
                return SimpleNamespace(project_id=row["id"], cycle=1, phase=_Unknown())

        audit = PostgresWebAudit(resources.ledger._pool, rows=Rows())  # type: ignore[arg-type]
        with pytest.raises(WebToolUnavailable, match="phase this vibey does not know"):
            await audit.ready(None)
        with pytest.raises(WebToolUnavailable, match="phase this vibey does not know"):
            await audit.record(EventKind.WEB_SEARCHED, {}, AT, None)


class _Unknown:
    value = "FUTURE"
