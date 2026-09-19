# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The seams for the conductor's before-work feasibility sweep (#134)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import (
    EngineHealthRecord,
    FeasibilityAssessment,
    PreflightResult,
    StartupPreflightReport,
)
from vibey.application.interfaces.engines import EngineAdapter
from vibey.domain.engine import EngineId


@runtime_checkable
class FeasibilityAssessmentInterface(Protocol):
    """The three-valued result exposed by the startup preflight."""

    @property
    def status(self) -> str: ...

    @property
    def blocked_at(self) -> str | None: ...

    @property
    def first_repair(self) -> str | None: ...

    @property
    def confidence(self) -> float: ...

    @property
    def required(self) -> int: ...

    @property
    def required_measured(self) -> int: ...


@runtime_checkable
class StartupPreflightReportInterface(Protocol):
    """The complete result of refreshing engines before worker startup."""

    @property
    def ineligible_engines(self) -> tuple[EngineId, ...]: ...

    @property
    def feasibility(self) -> FeasibilityAssessmentInterface: ...


@runtime_checkable
class RunFeasibilityEvaluatorInterface(Protocol):
    """Projects fresh engine evidence into a whole-path feasibility verdict."""

    def evaluate(
        self,
        *,
        project_id: UUID,
        preflights: Mapping[EngineId, PreflightResult],
        health_records: Sequence[EngineHealthRecord],
    ) -> FeasibilityAssessment:
        """Return only conclusions supported by the supplied measurements."""
        ...


@runtime_checkable
class PreflightHealthServiceInterface(Protocol):
    """The engine-health operations needed by the startup preflight."""

    async def record_preflight(
        self,
        project_id: UUID,
        engine_id: EngineId,
        preflight: PreflightResult,
    ) -> EngineHealthRecord: ...

    async def list_for_project(self, project_id: UUID) -> tuple[EngineHealthRecord, ...]: ...


@runtime_checkable
class ConductorPreflightInterface(Protocol):
    """Refresh every configured engine and evaluate the run before work starts."""

    async def run(
        self,
        *,
        project_id: UUID,
        adapters: Mapping[EngineId, EngineAdapter],
    ) -> StartupPreflightReport: ...
