# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Diagnostics the application emits.

Diagnostics are distinct from the event ledger, which is durable domain history
rather than something an operator can turn down with a flag.  The concrete
notification and telemetry implementations live in ``infrastructure``; the
application only knows these small ports.
"""

from __future__ import annotations

from collections.abc import Mapping
from contextlib import AbstractContextManager
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId
from vibey.domain.phase import Phase


@runtime_checkable
class Logger(Protocol):
    """Structured application logging -- implemented by infrastructure/logging."""

    def bind(self, **kwargs: Any) -> Logger: ...
    def debug(self, event: str, **kwargs: Any) -> None: ...
    def info(self, event: str, **kwargs: Any) -> None: ...
    def warning(self, event: str, **kwargs: Any) -> None: ...
    def error(self, event: str, **kwargs: Any) -> None: ...


@runtime_checkable
class NotificationSink(Protocol):
    """Best-effort operator notification delivery.

    ``config`` is the project configuration that enabled the sink.  Keeping it
    on the call means a single application process can safely drive several
    projects with different webhook recipients without putting configuration
    policy in the application layer.
    """

    async def notify(
        self,
        *,
        project_id: UUID,
        kind: str,
        title: str,
        message: str,
        payload: Mapping[str, object] | None = None,
        config: Mapping[str, object] | None = None,
    ) -> Mapping[str, object]: ...


@runtime_checkable
class TelemetrySpan(Protocol):
    """The mutable part of a job/turn/handoff span."""

    def set_attribute(self, key: str, value: object) -> None: ...

    def add_event(self, name: str, attributes: dict[str, object] | None = None) -> None: ...


@runtime_checkable
class TelemetryTracer(Protocol):
    """Tracing port used by the application orchestration paths."""

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
    ) -> AbstractContextManager[TelemetrySpan]: ...

    def trace_turn(
        self,
        *,
        engine_id: EngineId | str | None = None,
        turn_number: int | None = None,
        **extra_attributes: object,
    ) -> AbstractContextManager[TelemetrySpan]: ...

    def trace_handoff(
        self,
        *,
        from_engine: EngineId | str | None = None,
        to_engine: EngineId | str | None = None,
        **extra_attributes: object,
    ) -> AbstractContextManager[TelemetrySpan]: ...


@runtime_checkable
class TelemetryMetrics(Protocol):
    """Metrics port for the production rotation and queue paths."""

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
