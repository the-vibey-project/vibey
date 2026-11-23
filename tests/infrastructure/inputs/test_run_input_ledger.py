# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The run input ledger adapter: one BUILD-phase event, no job, no engine (SP-LOOPS Phase 3).
The ledger repository is a fake that keeps the drafts it is given."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import cast
from uuid import uuid4

import pytest

from vibey.application.dto import EngineEvent
from vibey.application.interfaces.run_input_ledger_interface import RunInputLedgerInterface
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.ledger import EventKind, Provenance
from vibey.domain.phase import Phase
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.engines.tailer import LedgerEventDraft
from vibey.infrastructure.inputs.interfaces.run_input_ledger_interface import (
    PostgresRunInputLedgerInterface,
)
from vibey.infrastructure.inputs.run_input_ledger import PostgresRunInputLedger

AT = datetime(2026, 11, 23, 12, 0, tzinfo=UTC)


class _Ledger:
    def __init__(self) -> None:
        self.drafts: list[LedgerEventDraft] = []

    async def append(self, draft: LedgerEventDraft) -> None:
        self.drafts.append(draft)


def _adapter(fake: _Ledger) -> PostgresRunInputLedger:
    return PostgresRunInputLedger(cast(PostgresLedgerRepository, fake))


def test_an_input_event_is_one_trusted_build_event_with_no_job_and_no_engine() -> None:
    fake = _Ledger()
    project_id = uuid4()
    payload = {"artifact_type": "vibey_run_input", "digest": "a" * 64, "kind": "file", "size": 3}
    event = EngineEvent(kind=EventKind.ARTIFACT_PRODUCED.value, at=AT, payload=payload)
    asyncio.run(_adapter(fake).record(project_id=project_id, cycle=4, event=event))
    [draft] = fake.drafts
    assert (draft.project_id, draft.cycle, draft.phase) == (project_id, 4, Phase.BUILD)
    assert (draft.kind, draft.job_id, draft.engine_id) == (EventKind.ARTIFACT_PRODUCED, None, None)
    assert draft.causation_id is None
    assert draft.provenance is Provenance.TRUSTED
    assert draft.correlation_id == DELIVERY_CORRELATION.for_project(project_id).value
    assert draft.payload == payload
    assert draft.produced_at == AT


def test_an_event_kind_the_ledger_does_not_know_is_refused_not_dropped() -> None:
    fake = _Ledger()
    event = EngineEvent(kind="NoSuchKind", at=AT, payload={})
    with pytest.raises(ValueError, match="NoSuchKind"):
        asyncio.run(_adapter(fake).record(project_id=uuid4(), cycle=1, event=event))
    assert fake.drafts == []


def test_the_adapter_meets_both_interfaces() -> None:
    adapter = _adapter(_Ledger())
    assert isinstance(adapter, RunInputLedgerInterface)
    assert isinstance(adapter, PostgresRunInputLedgerInterface)


def test_a_run_event_carries_the_job_id_it_is_given() -> None:
    fake = _Ledger()
    job_id = uuid4()
    event = EngineEvent(kind=EventKind.ARTIFACT_PRODUCED.value, at=AT, payload={})
    asyncio.run(_adapter(fake).record(project_id=uuid4(), cycle=1, event=event, job_id=job_id))
    assert fake.drafts[0].job_id == job_id


class _ReadingLedger(_Ledger):
    def __init__(self, events: list[object]) -> None:
        super().__init__()
        self.events = events
        self.asked: list[tuple[object, tuple[str, ...]]] = []

    async def artifacts_of_type(self, project_id: object, types: tuple[str, ...]) -> list[object]:
        self.asked.append((project_id, tuple(types)))
        return self.events


def test_added_is_the_digests_of_every_add_and_repair_event() -> None:
    from types import SimpleNamespace

    project_id = uuid4()
    fake = _ReadingLedger(
        [
            SimpleNamespace(payload={"artifact_type": "vibey_run_input", "digest": "a" * 64}),
            SimpleNamespace(
                payload={"artifact_type": "vibey_run_input_repaired", "digest": "b" * 64}
            ),
            SimpleNamespace(payload={"artifact_type": "vibey_run_input", "digest": 7}),
            SimpleNamespace(payload={"artifact_type": "vibey_run_input"}),
        ]
    )
    added = asyncio.run(
        PostgresRunInputLedger(cast(PostgresLedgerRepository, fake)).added(project_id)
    )
    assert added == frozenset({"a" * 64, "b" * 64})
    assert fake.asked == [(project_id, ("vibey_run_input", "vibey_run_input_repaired"))]
