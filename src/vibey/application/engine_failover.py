# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Engine-level failover and handback for a vibey project's jobs (ADR-0070).

The same policy as the driver's (`vibey/domain/failover.py`), over the project's own
Postgres ledger and the project's own `HandoffBrief` gate
(`handoff_orchestration.produce_and_verify_handoff`: STRICT x3, FULL_TRANSCRIPT, then
HUMAN):

- `fail_over` -- a paid engine's capacity rejection. The gate runs first; on HUMAN the
  decision is `parked` and nothing is recorded. Otherwise a trusted `EngineFailedOver`
  names the engine that ran out, the target (`[failover] target_engine`), the effort
  (`target_effort`, ULTRA) and when a probe may first run, and the decision carries the
  requirement the next selection must honour: the target's effort, the exhausted engine
  excluded. A second rejection while a failover is active records nothing.
- `record_probe` -- a probe of the exhausted engine, ok or not, as `EngineProbed`.
- `hand_back` -- refused unless an ok probe is recorded after the latest failover
  (sub-doctrine 10.f); then gated again, and `EngineHandedBack` names the engine the work
  returns to.
"""

from collections.abc import Awaitable, Callable, Sequence
from typing import Final
from uuid import UUID

from vibey.application.dto import EngineFailoverDecision
from vibey.application.handoff_orchestration import HandoffOutcome, produce_and_verify_handoff
from vibey.application.interfaces.failover import FailoverEventStore
from vibey.application.interfaces.ledger import BriefProducer, LedgerReader
from vibey.application.interfaces.system import Clock
from vibey.domain.capacity import CapacityState
from vibey.domain.engine import ENGINE_ID_PARSER, EngineId, JobRequirement
from vibey.domain.errors import HandbackRefused
from vibey.domain.failover import (
    FAILOVER_POLICY,
    FailoverRecord,
    FailoverSettings,
    FailoverStatus,
)
from vibey.domain.handoff import BudgetSnapshot, GateMode, LedgerRef
from vibey.domain.interfaces.failover_interface import FailoverPolicyInterface
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance

_KINDS: Final = {
    EventKind.ENGINE_FAILED_OVER.value,
    EventKind.ENGINE_PROBED.value,
    EventKind.ENGINE_HANDED_BACK.value,
}


class EngineFailoverService:
    """Declared by `interfaces/failover.py::EngineFailoverServiceInterface`."""

    def __init__(
        self,
        *,
        settings: FailoverSettings,
        ledger: LedgerReader,
        store: FailoverEventStore,
        clock: Clock,
        policy: FailoverPolicyInterface = FAILOVER_POLICY,
        gate: Callable[..., Awaitable[HandoffOutcome]] = produce_and_verify_handoff,
    ) -> None:
        self._settings = settings
        self._ledger = ledger
        self._store = store
        self._clock = clock
        self._policy = policy
        self._gate = gate

    async def status(self, project_id: UUID) -> FailoverStatus:
        return self._policy.status(self._records(await self._ledger.all_for_project(project_id)))

    async def fail_over(
        self,
        project_id: UUID,
        *,
        from_engine: EngineId,
        capacity: CapacityState,
        requirement: JobRequirement,
        producer: BriefProducer,
        ref: LedgerRef,
        budget: BudgetSnapshot,
    ) -> EngineFailoverDecision:
        now = self._clock.now()
        plan = self._policy.plan(capacity, now=now, settings=self._settings)
        if plan is None:
            return EngineFailoverDecision("not_capacity")
        target = ENGINE_ID_PARSER.known(plan.target_engine)
        if target is None:
            raise ValueError(f"[failover] target_engine {plan.target_engine!r} is not an engine")
        events = await self._ledger.all_for_project(project_id)
        if self._policy.status(self._records(events)).active:
            return EngineFailoverDecision("already", next_engine=target)
        outcome = await self._gate(producer=producer, ledger=events, ref=ref, budget=budget)
        if outcome.result.mode is GateMode.HUMAN:
            return EngineFailoverDecision("parked", gate=outcome.result, brief=outcome.brief)
        await self._store.record(
            project_id,
            EventKind.ENGINE_FAILED_OVER,
            {
                "from_engine": from_engine.value,
                "target": target.value,
                "effort": plan.effort.name,
                "cause": plan.cause.value,
                "probe_not_before": plan.probe_not_before.isoformat(),
                "gate_mode": outcome.result.mode.value,
                "gate_attempts": outcome.result.attempts,
            },
            at=now,
        )
        return EngineFailoverDecision(
            "failed_over",
            next_engine=target,
            requirement=JobRequirement(
                effort=plan.effort,
                capabilities=requirement.capabilities,
                excluded=requirement.excluded | {from_engine},
            ),
            gate=outcome.result,
            brief=outcome.brief,
        )

    async def record_probe(
        self, project_id: UUID, *, engine: EngineId, ok: bool, detail: str = ""
    ) -> FailoverStatus:
        await self._store.record(
            project_id,
            EventKind.ENGINE_PROBED,
            {"engine": engine.value, "ok": ok, "detail": detail},
            at=self._clock.now(),
        )
        return await self.status(project_id)

    async def hand_back(
        self,
        project_id: UUID,
        *,
        producer: BriefProducer,
        ref: LedgerRef,
        budget: BudgetSnapshot,
    ) -> EngineFailoverDecision:
        events = await self._ledger.all_for_project(project_id)
        status = self._policy.status(self._records(events))
        if not status.may_hand_back or status.failover is None or status.probe_ok is None:
            raise HandbackRefused(
                f"project {project_id}: no successful probe is recorded after the failover"
            )
        back = ENGINE_ID_PARSER.known(str(status.failover.payload.get("from_engine", "")))
        if back is None:
            raise HandbackRefused(f"project {project_id}: the failover names no known engine")
        outcome = await self._gate(producer=producer, ledger=events, ref=ref, budget=budget)
        if outcome.result.mode is GateMode.HUMAN:
            return EngineFailoverDecision("parked", gate=outcome.result, brief=outcome.brief)
        await self._store.record(
            project_id,
            EventKind.ENGINE_HANDED_BACK,
            {
                "to_engine": back.value,
                "probe_at": status.probe_ok.at.isoformat(),
                "gate_mode": outcome.result.mode.value,
                "gate_attempts": outcome.result.attempts,
            },
            at=self._clock.now(),
        )
        return EngineFailoverDecision(
            "handed_back", next_engine=back, gate=outcome.result, brief=outcome.brief
        )

    def _records(self, events: Sequence[LedgerEvent]) -> tuple[FailoverRecord, ...]:
        return self._policy.read_rows(
            [
                {
                    "kind": str(event.kind),
                    "at": event.produced_at.isoformat(),
                    "payload": event.payload,
                    "trusted": event.provenance is Provenance.TRUSTED,
                }
                for event in events
                if str(event.kind) in _KINDS
            ]
        )
