# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""`UltraControlService`: the operator's start, Stop and no-cap declaration, each one
trusted ledger event naming who, when and which device (ADR-0063)."""

from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest

from tests.application.test_project_budget import _Ledger, _project, _Projects
from vibey.application.interfaces import UltraControlServiceInterface, UltraControlStore
from vibey.application.ultra_control import UltraControlService
from vibey.domain.engine import EngineId
from vibey.domain.errors import InvalidBudgetChange, UnknownProject
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.queue_priority import Caller
from vibey.domain.ultra import NO_CAP_PHRASE

NOW = datetime(2026, 9, 25, 12, tzinfo=UTC)


class _Store:
    """Appends to the `_Ledger` it shares, as trusted events, so status reads them."""

    def __init__(self, ledger: _Ledger) -> None:
        self.ledger = ledger
        self.calls: list[tuple[UUID, EventKind, Mapping[str, object], datetime]] = []

    async def record(
        self, project_id: UUID, kind: EventKind, payload: Mapping[str, object], *, at: datetime
    ) -> None:
        self.calls.append((project_id, kind, payload, at))
        events = self.ledger.events.setdefault(project_id, [])
        events.append(_event(project_id, len(events) + 1, kind, dict(payload), at))


def _event(
    project_id: UUID,
    seq: int,
    kind: EventKind,
    payload: dict[str, object],
    at: datetime = NOW,
    engine_id: EngineId | None = None,
) -> LedgerEvent:
    return LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        seq=seq,
        kind=kind,
        engine_id=engine_id,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,
        provenance=Provenance.TRUSTED,
        produced_at=at,
        payload=payload,
        digest=digest_event(payload),
    )


class _Caller:
    def current(self) -> Caller:
        return Caller(uid=501, name="adam")


class _Clock:
    def now(self) -> datetime:
        return NOW


def _service(*projects):  # type: ignore[no-untyped-def]
    ledger = _Ledger()
    store = _Store(ledger)
    service = UltraControlService(
        projects=_Projects(*projects),
        ledger=ledger,
        store=store,
        caller=_Caller(),
        clock=_Clock(),
        device="host-1",
    )
    return service, store, ledger


def test_the_service_and_store_satisfy_their_interfaces() -> None:
    service, store, _ = _service()
    assert isinstance(service, UltraControlServiceInterface)
    assert isinstance(store, UltraControlStore)


async def test_start_and_stop_record_who_when_and_which_device() -> None:
    project = _project("p", {"max_cycle_dollars": 5.0})
    service, store, _ = _service(project)

    started = await service.start(project.project_id)
    assert started.active and started.max_dollars == 5.0 and started.passes_completed == 0
    stopped = await service.stop(project.project_id, by="vibey-vscode")
    assert not stopped.active

    kinds = [call[1] for call in store.calls]
    assert kinds == [EventKind.ULTRA_STARTED, EventKind.ULTRA_STOPPED]
    assert store.calls[0][2] == {"by": "adam", "account": "adam", "device": "host-1"}
    assert store.calls[1][2]["by"] == "vibey-vscode"
    assert store.calls[1][3] == NOW


async def test_no_cap_needs_the_phrase_and_is_withdrawn_in_one_action() -> None:
    project = _project("p", {})
    service, store, _ = _service(project)

    with pytest.raises(InvalidBudgetChange, match=NO_CAP_PHRASE):
        await service.declare_no_cap(project.project_id, phrase="yes")
    assert store.calls == []

    declared = await service.declare_no_cap(project.project_id, phrase=NO_CAP_PHRASE)
    assert declared.no_cap_declared
    assert store.calls[-1][2]["enabled"] is True
    kept = await service.keep_cap(project.project_id)
    assert not kept.no_cap_declared
    assert store.calls[-1][2]["enabled"] is False


async def test_status_counts_passes_and_measures_the_rate() -> None:
    project = _project("p", {})
    service, _, ledger = _service(project)
    pid = project.project_id
    ledger.events[pid] = [
        _event(pid, 1, EventKind.ULTRA_PASS_COMPLETED, {"pass": 1}),
        _event(pid, 2, EventKind.ULTRA_PASS_COMPLETED, {"pass": 2}),
        _event(pid, 3, EventKind.TURN_COMPLETED, {"cost_usd": 2.0}, NOW),
        _event(
            pid,
            4,
            EventKind.TURN_COMPLETED,
            {"cost_usd": 2.0},
            datetime(2026, 9, 25, 14, tzinfo=UTC),
        ),
    ]
    status = await service.status(pid)
    assert status.passes_completed == 2
    assert status.rate_per_hour == pytest.approx(2.0)
    assert status.dollars_spent == pytest.approx(4.0)
    assert status.max_dollars is None


async def test_an_unknown_project_is_refused() -> None:
    service, _, _ = _service()
    with pytest.raises(UnknownProject):
        await service.status(uuid4())
