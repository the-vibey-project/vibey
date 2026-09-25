# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The failover store writes its three trusted kinds and refuses every other (ADR-0070)."""

from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest

from vibey.application.dto import ProjectRecord
from vibey.application.interfaces import FailoverEventStore
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.failover_store import FAILOVER_KINDS, PostgresFailoverStore
from vibey.infrastructure.db.interfaces.failover_store_interface import (
    PostgresFailoverStoreInterface,
)

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


class _Appender:
    def __init__(self) -> None:
        self.drafts: list[object] = []

    async def append(self, conn: object, draft: object) -> None:
        self.drafts.append(draft)


def _store() -> tuple[PostgresFailoverStore, _Appender, ProjectRecord]:
    record = ProjectRecord(
        project_id=uuid4(),
        name="p",
        repo_path=Path("/w/p"),
        phase=Phase.BUILD,
        cycle=2,
        max_cycles=3,
        config={},
        created_at=NOW,
        updated_at=NOW,
    )
    appender = _Appender()
    store = PostgresFailoverStore(_Pool(), rows=_Rows(record), appender=appender)  # type: ignore[arg-type]
    return store, appender, record


async def test_each_failover_kind_is_appended_trusted() -> None:
    store, appender, record = _store()
    assert isinstance(store, PostgresFailoverStoreInterface)
    assert isinstance(store, FailoverEventStore)
    for kind in sorted(FAILOVER_KINDS):
        await store.record(record.project_id, kind, {"ok": True}, at=NOW)
    assert [d.kind for d in appender.drafts] == sorted(FAILOVER_KINDS)  # type: ignore[attr-defined]
    draft = appender.drafts[0]
    assert draft.provenance is Provenance.TRUSTED and draft.cycle == 2  # type: ignore[attr-defined]
    assert draft.phase is Phase.BUILD and draft.payload == {"ok": True}  # type: ignore[attr-defined]


async def test_an_ultra_control_is_not_a_failover_record() -> None:
    store, appender, record = _store()
    with pytest.raises(ValueError, match="not a failover record"):
        await store.record(record.project_id, EventKind.ULTRA_STARTED, {}, at=NOW)
    assert appender.drafts == []
