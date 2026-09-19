# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The conductor's one startup preflight: refresh health, then judge feasibility."""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from uuid import UUID

from vibey.application.dto import StartupPreflightReport
from vibey.application.interfaces.engines import EngineAdapter
from vibey.application.interfaces.preflight_interface import (
    ConductorPreflightInterface,
    PreflightHealthServiceInterface,
    RunFeasibilityEvaluatorInterface,
)
from vibey.domain.engine import EngineId


class ConductorPreflight(ConductorPreflightInterface):
    """Runs every engine probe concurrently and evaluates the resulting state.

    Conformance remains doctor's grant: startup refreshes installed/version/auth
    without forging it, then tells the feasibility adapter which engines still
    cannot take engine-driven work.
    """

    def __init__(
        self,
        *,
        health: PreflightHealthServiceInterface,
        feasibility: RunFeasibilityEvaluatorInterface,
    ) -> None:
        self._health = health
        self._feasibility = feasibility

    async def run(
        self,
        *,
        project_id: UUID,
        adapters: Mapping[EngineId, EngineAdapter],
    ) -> StartupPreflightReport:
        engine_ids = tuple(adapters)
        results = await asyncio.gather(
            *(adapters[engine_id].preflight() for engine_id in engine_ids)
        )
        preflights = dict(zip(engine_ids, results, strict=True))
        for engine_id, result in preflights.items():
            await self._health.record_preflight(project_id, engine_id, result)

        records = await self._health.list_for_project(project_id)
        by_id = {record.engine_id.value: record for record in records}
        ineligible = tuple(
            engine_id
            for engine_id in engine_ids
            if engine_id.value not in by_id or not by_id[engine_id.value].conformance_ok
        )
        feasibility = self._feasibility.evaluate(
            project_id=project_id,
            preflights=preflights,
            health_records=records,
        )
        return StartupPreflightReport(
            ineligible_engines=ineligible,
            feasibility=feasibility,
        )
