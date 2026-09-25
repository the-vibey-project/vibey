# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The ULTRA control store records nothing under a phase this vibey does not know."""

import dataclasses
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.application.dto import ProjectRecord
from vibey.domain.errors import WrongPhase
from vibey.domain.ledger import EventKind
from vibey.domain.phase import Phase, UnrecognizedPhase
from vibey.infrastructure.db.interfaces.ultra_control_store_interface import (
    PostgresUltraControlStoreInterface,
)
from vibey.infrastructure.db.ultra_control_store import PostgresUltraControlStore

NOW = datetime(2026, 9, 25, tzinfo=UTC)


class _Conn:
    async def fetchrow(self, query: str, *args: object) -> object:
        return {"row": True}

    @asynccontextmanager
    async def transaction(self):  # type: ignore[no-untyped-def]
        yield


class _Pool:
    @asynccontextmanager
    async def acquire(self):  # type: ignore[no-untyped-def]
        yield _Conn()


class _Rows:
    def __init__(self, record: ProjectRecord) -> None:
        self.record = record

    def to_record(self, row: object) -> ProjectRecord:
        return self.record


async def test_an_unknown_phase_is_refused_and_nothing_is_appended() -> None:
    record = ProjectRecord(
        project_id=uuid4(),
        name="p",
        repo_path=Path("/tmp/p"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    record = dataclasses.replace(record, phase=UnrecognizedPhase("hyperspace"))
    store = PostgresUltraControlStore(_Pool(), rows=_Rows(record))  # type: ignore[arg-type]
    assert isinstance(store, PostgresUltraControlStoreInterface)
    with pytest.raises(WrongPhase, match="hyperspace"):
        await store.record(record.project_id, EventKind.ULTRA_STOPPED, {}, at=NOW)
