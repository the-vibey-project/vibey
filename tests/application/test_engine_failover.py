# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Engine-level failover and handback over a project's ledger (ADR-0070)."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from vibey.application.dto import EngineFailoverDecision
from vibey.application.engine_failover import EngineFailoverService
from vibey.application.handoff_orchestration import HandoffOutcome
from vibey.application.interfaces.failover import (
    EngineFailoverServiceInterface,
    FailoverEventStore,
)
from vibey.domain.budget import BudgetLedger
from vibey.domain.capacity import AuthenticationFailed, CreditsExhausted, WindowExhausted
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId, JobRequirement
from vibey.domain.errors import HandbackRefused
from vibey.domain.failover import FailoverSettings
from vibey.domain.handoff import GateMode, GateResult, HandoffBrief, LedgerRef
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance
from vibey.domain.phase import Phase

T0 = datetime(2026, 9, 25, 18, 0, tzinfo=UTC)
PROJECT = uuid4()
BRIEF = HandoffBrief("o", (), (), (), (), (), (), (), (), (), (), "next")
REF = LedgerRef(uri="u", from_seq=0, to_seq=0, event_count=0, digest="d")
BUDGET = BudgetLedger(turns_spent=0, dollars_spent=0.0, max_turns=None, max_dollars=None)
REQ = JobRequirement(effort=Effort.LOW, excluded=frozenset({EngineId.CODEXLOOP}))


@dataclass
class Clock:
    at: datetime = T0

    def now(self) -> datetime:
        return self.at


@dataclass
class Ledger:
    events: list[LedgerEvent] = field(default_factory=list)

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(self.events)

    def add(
        self, kind: object, payload: Mapping[str, object], at: datetime, *, trusted: bool = True
    ) -> None:
        self.events.append(
            LedgerEvent(
                event_id=uuid4(),
                project_id=PROJECT,
                cycle=1,
                phase=Phase.BUILD,
                seq=len(self.events) + 1,
                kind=kind,  # type: ignore[arg-type]
                engine_id=None,
                job_id=None,
                causation_id=None,
                correlation_id=uuid4(),
                provenance=Provenance.TRUSTED if trusted else Provenance.UNTRUSTED,
                produced_at=at,
                payload=dict(payload),
                digest="x",
            )
        )


@dataclass
class Store:
    ledger: Ledger

    async def record(
        self, project_id: UUID, kind: EventKind, payload: Mapping[str, object], *, at: datetime
    ) -> None:
        self.ledger.add(kind, payload, at)


def _gate(mode: GateMode) -> Any:
    async def gate(**_: object) -> HandoffOutcome:
        return HandoffOutcome(
            result=GateResult(mode is not GateMode.HUMAN, mode, 1, (), ()), brief=BRIEF
        )

    return gate


def _service(
    mode: GateMode = GateMode.STRICT, **settings: Any
) -> tuple[EngineFailoverService, Ledger, Clock]:
    ledger, clock = Ledger(), Clock()
    service = EngineFailoverService(
        settings=FailoverSettings(**settings),
        ledger=ledger,
        store=Store(ledger),
        clock=clock,
        gate=_gate(mode),
    )
    return service, ledger, clock


async def _fail(service: EngineFailoverService, capacity: Any = None) -> EngineFailoverDecision:
    return await service.fail_over(
        PROJECT,
        from_engine=EngineId.CLAUDELOOP,
        capacity=capacity or CreditsExhausted(),
        requirement=REQ,
        producer=None,  # type: ignore[arg-type]
        ref=REF,
        budget=BUDGET,
    )


async def _back(service: EngineFailoverService) -> EngineFailoverDecision:
    return await service.hand_back(PROJECT, producer=None, ref=REF, budget=BUDGET)  # type: ignore[arg-type]


def test_interfaces() -> None:
    service, ledger, _ = _service()
    assert isinstance(service, EngineFailoverServiceInterface)
    assert isinstance(Store(ledger), FailoverEventStore)


async def test_credits_fail_over_to_gptossloop_at_ultra_with_the_engine_excluded() -> None:
    service, ledger, _ = _service()
    decision = await _fail(service)
    assert decision.result == "failed_over" and decision.next_engine is EngineId.GPTOSSLOOP
    assert decision.requirement == JobRequirement(
        effort=Effort.ULTRA, excluded=frozenset({EngineId.CODEXLOOP, EngineId.CLAUDELOOP})
    )
    assert decision.brief is BRIEF and decision.gate is not None and decision.gate.ok
    (event,) = ledger.events
    assert event.kind is EventKind.ENGINE_FAILED_OVER
    assert event.payload["from_engine"] == "claudeloop" and event.payload["effort"] == "ULTRA"
    assert event.payload["probe_not_before"] == (T0 + timedelta(minutes=30)).isoformat()
    assert (await service.status(PROJECT)).active
    again = await _fail(service, WindowExhausted())
    assert again.result == "already" and len(ledger.events) == 1


async def test_what_is_not_capacity_records_nothing() -> None:
    service, ledger, _ = _service()
    assert (await _fail(service, AuthenticationFailed())).result == "not_capacity"
    assert ledger.events == []


async def test_an_unknown_target_engine_is_refused() -> None:
    service, _, _ = _service(target_engine="no-such-loop")
    with pytest.raises(ValueError, match="no-such-loop"):
        await _fail(service)


async def test_a_parked_gate_records_nothing() -> None:
    service, ledger, _ = _service(GateMode.HUMAN)
    decision = await _fail(service)
    assert decision.result == "parked" and decision.gate is not None
    assert decision.gate.mode is GateMode.HUMAN and ledger.events == []


async def test_handback_only_after_a_recorded_ok_probe() -> None:
    service, ledger, clock = _service()
    with pytest.raises(HandbackRefused, match="no successful probe"):
        await _back(service)
    await _fail(service)
    clock.at = T0 + timedelta(hours=1)
    status = await service.record_probe(PROJECT, engine=EngineId.CLAUDELOOP, ok=False, detail="429")
    assert status.active and not status.may_hand_back
    with pytest.raises(HandbackRefused):
        await _back(service)
    status = await service.record_probe(PROJECT, engine=EngineId.CLAUDELOOP, ok=True)
    assert status.may_hand_back
    decision = await _back(service)
    assert decision.result == "handed_back" and decision.next_engine is EngineId.CLAUDELOOP
    assert ledger.events[-1].kind is EventKind.ENGINE_HANDED_BACK
    assert ledger.events[-1].payload["probe_at"] == clock.at.isoformat()
    assert not (await service.status(PROJECT)).active


async def test_a_handback_whose_gate_parks_records_nothing() -> None:
    service, ledger, _ = _service()
    ledger.add(EventKind.ENGINE_FAILED_OVER, {"from_engine": "claudeloop"}, T0)
    ledger.add(EventKind.ENGINE_PROBED, {"ok": True}, T0)
    parked = EngineFailoverService(
        settings=FailoverSettings(),
        ledger=ledger,
        store=Store(ledger),
        clock=Clock(),
        gate=_gate(GateMode.HUMAN),
    )
    assert (await _back(parked)).result == "parked"
    assert len(ledger.events) == 2
    assert (await _back(service)).result == "handed_back"


async def test_a_failover_naming_no_known_engine_cannot_hand_back() -> None:
    service, ledger, _ = _service()
    ledger.add(EventKind.ENGINE_FAILED_OVER, {"from_engine": "martian"}, T0)
    ledger.add(EventKind.ENGINE_PROBED, {"ok": True}, T0)
    with pytest.raises(HandbackRefused, match="no known engine"):
        await _back(service)


async def test_untrusted_and_unrelated_events_are_ignored() -> None:
    service, ledger, _ = _service()
    ledger.add(EventKind.ENGINE_FAILED_OVER, {"from_engine": "claudeloop"}, T0, trusted=False)
    ledger.add(EventKind.GATE_ANSWERED, {}, T0)
    assert not (await service.status(PROJECT)).active
