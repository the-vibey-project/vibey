# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind hybrid engine dispatch (ADR-0079).

Mirrors `vibey/domain/engine_dispatch.py` (ADR-0016). Interfaces declare; they never consume.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence
    from datetime import datetime, timedelta

    from vibey.domain.config import EngineDispatchConfig
    from vibey.domain.engine import EngineId, EngineTier
    from vibey.domain.engine_dispatch import (
        DispatchLoad,
        DispatchMeasurement,
        DispatchPlan,
        EngineDispatchPolicy,
        LocalSession,
        SlotHold,
    )
    from vibey.domain.rotation import Candidate


@runtime_checkable
class EngineDispatchPolicyInterface(Protocol):
    """The resolved policy one selection runs under."""

    def slots_for(self, engine_id: EngineId, tier: EngineTier) -> int:
        """The engine's declared concurrent slots, or its tier's default."""
        ...


@runtime_checkable
class EngineDispatcherInterface(Protocol):
    """Plans the candidates a selection may offer SWRR. Pure."""

    def plan(
        self,
        candidates: Sequence[Candidate],
        policy: EngineDispatchPolicy,
        load: DispatchLoad,
    ) -> DispatchPlan | SlotHold:
        """`singleton`: today's tier-first plan, exactly. `hybrid`: a free local slot
        first; a hold while overflow could follow and the job has not waited long
        enough; paid overflow once it has; otherwise today's plan."""
        ...


@runtime_checkable
class UtcDayInterface(Protocol):
    def start(self, at: datetime) -> datetime:
        """Midnight UTC at the start of `at`'s day."""
        ...

    def label(self, at: datetime) -> str: ...


@runtime_checkable
class DispatchMeasurementJudgeInterface(Protocol):
    """Measures local-slot contention and judges whether a measurement is current. Pure."""

    def fingerprint(
        self,
        config: EngineDispatchConfig,
        local_slots: Mapping[EngineId, int],
        implementation: str,
    ) -> str: ...

    def measure(
        self,
        sessions: Sequence[LocalSession],
        *,
        local_slots: Mapping[EngineId, int],
        config: EngineDispatchConfig,
        window_end: datetime,
        fingerprint: str,
    ) -> DispatchMeasurement: ...

    def current(
        self,
        measurement: DispatchMeasurement | None,
        *,
        now: datetime,
        fingerprint: str,
        max_age: timedelta,
    ) -> DispatchMeasurement | None:
        """None for a missing, mismatched, future or stale measurement."""
        ...
