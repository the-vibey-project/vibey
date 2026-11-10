# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seam of `infrastructure/otel.py` (ADR-0016). Interfaces declare; they never
consume."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import TYPE_CHECKING, Protocol
from uuid import UUID

if TYPE_CHECKING:
    from vibey.domain.effort import Effort
    from vibey.domain.engine import EngineId
    from vibey.domain.phase import Phase
    from vibey.infrastructure.otel import Span


class TelemetryTracerInterface(Protocol):
    """The in-process tracer: spans nest per asyncio context and finished ones are kept,
    the newest survive, up to a declared cap."""

    def start_span(
        self,
        name: str,
        *,
        parent_id: str | None = None,
        attributes: dict[str, object] | None = None,
    ) -> AbstractContextManager[Span]: ...

    def trace_job(
        self,
        *,
        project_id: UUID,
        cycle: int,
        phase: Phase | str,
        job_kind: str,
        engine_id: EngineId | str | None = None,
        effort: Effort | str | None = None,
        **extra_attributes: object,
    ) -> AbstractContextManager[Span]: ...

    def trace_turn(
        self,
        *,
        engine_id: EngineId | str | None = None,
        turn_number: int | None = None,
        **extra_attributes: object,
    ) -> AbstractContextManager[Span]: ...

    def trace_handoff(
        self,
        *,
        from_engine: EngineId | str | None = None,
        to_engine: EngineId | str | None = None,
        **extra_attributes: object,
    ) -> AbstractContextManager[Span]: ...

    def get_finished_spans(self) -> list[Span]: ...

    def clear(self) -> None: ...


class TelemetryMetricsInterface(Protocol):
    """The in-process production metrics recorder."""

    def record_engine_selection(self, project_id: UUID, engine_id: EngineId | str) -> None: ...

    def record_queue_latency(
        self, project_id: UUID, phase: Phase | str, job_kind: str, latency_seconds: float
    ) -> None: ...

    def record_phase_duration(
        self, project_id: UUID, cycle: int, phase: Phase | str, duration_seconds: float
    ) -> None: ...

    def record_handoff_gate_failure(self, project_id: UUID, rule_id: str) -> None: ...

    def record_cost_spend(
        self,
        project_id: UUID,
        cycle: int,
        phase: Phase | str,
        engine_id: EngineId | str,
        cost_usd: float,
    ) -> None: ...

    def export_metrics(self, project_id: UUID) -> dict[str, object]: ...
