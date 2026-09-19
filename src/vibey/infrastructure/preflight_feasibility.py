# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Adapter from conductor preflight evidence to vibey-gh's feasibility calculus.

The family already ships the eighteen-coordinate, three-valued evaluator for
#134.  This module is the outer-layer bridge required by ADR-0017: root
application code sees its own port and DTO, while only infrastructure imports
the absorbed tenant.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from vibey_gh.feasibility import (
    NO,
    UNKNOWN,
    YES,
    Coordinate,
    FeasibilityEvaluator,
    Pipeline,
    StateVector,
)
from vibey_gh.interfaces.feasibility_evaluator_interface import FeasibilityEvaluatorInterface
from vibey_gh.interfaces.pipeline_interface import PipelineInterface

from vibey.application.dto import EngineHealthRecord, FeasibilityAssessment, PreflightResult
from vibey.application.interfaces.preflight_interface import RunFeasibilityEvaluatorInterface
from vibey.domain.engine import EngineId

_STATUS = {YES: "feasible", NO: "infeasible", UNKNOWN: "unknown"}


class VibeyGhFeasibilityAdapter(RunFeasibilityEvaluatorInterface):
    """Judges the full default path using only facts the engine sweep measured.

    The worker has already been installed, so its default path begins at
    ``interview`` and runs through ``main-validation``.  Both endpoints and
    both collaborators are injectable for adopters with a different pipeline.
    """

    def __init__(
        self,
        *,
        operation: str = "main-validation",
        start: str | None = "interview",
        pipeline: PipelineInterface | None = None,
        evaluator: FeasibilityEvaluatorInterface | None = None,
    ) -> None:
        self._pipeline = Pipeline() if pipeline is None else pipeline
        self._evaluator = FeasibilityEvaluator() if evaluator is None else evaluator
        self._stages = self._pipeline.path(operation, start)

    def evaluate(
        self,
        *,
        project_id: UUID,
        preflights: Mapping[EngineId, PreflightResult],
        health_records: Sequence[EngineHealthRecord],
    ) -> FeasibilityAssessment:
        records = {record.engine_id.value: record for record in health_records}
        installed = tuple(engine_id for engine_id, result in preflights.items() if result.installed)
        conformant = tuple(
            engine_id
            for engine_id in installed
            if (record := records.get(engine_id.value)) is not None and record.conformance_ok
        )
        authenticated = tuple(
            engine_id for engine_id in conformant if preflights[engine_id].auth_ok
        )

        measurements = [
            Coordinate(
                "software",
                "availability",
                float(bool(installed)),
                self._software_source(preflights, installed),
            ),
            Coordinate(
                "agent",
                "availability",
                float(bool(conformant)),
                self._agent_source(project_id, preflights, installed, conformant),
            ),
        ]
        # Authentication is measured agency: permission to use an agent.  A passing
        # engine auth probe does NOT prove merge rights or token scopes, so success
        # leaves agency unknown.  Failure, however, proves one necessary permission
        # is absent and is therefore a real shortfall rather than an unknown.
        if conformant and not authenticated:
            measurements.append(
                Coordinate(
                    "agency",
                    "availability",
                    0.0,
                    f"Authenticate at least one conformant engine: {self._names(conformant)}.",
                )
            )

        state = StateVector.unknown().with_measurements(measurements)
        verdict = self._evaluator.evaluate(state, self._stages)
        first = verdict.shortfalls[0] if verdict.shortfalls else None
        return FeasibilityAssessment(
            status=_STATUS[verdict.verdict],
            blocked_at=verdict.blocked_at,
            first_repair=None if first is None else f"{first.name} — {first.source}",
            confidence=verdict.confidence,
            required=verdict.required,
            required_measured=verdict.required_measured,
        )

    @staticmethod
    def _names(engine_ids: Sequence[EngineId]) -> str:
        return ", ".join(sorted(engine_id.value for engine_id in engine_ids))

    def _software_source(
        self,
        preflights: Mapping[EngineId, PreflightResult],
        installed: Sequence[EngineId],
    ) -> str:
        if installed:
            return f"fresh preflight found installed engine(s): {self._names(installed)}"
        return (
            "Install at least one configured engine: "
            f"{self._names(tuple(preflights)) or 'the configured pool is empty'}."
        )

    def _agent_source(
        self,
        project_id: UUID,
        preflights: Mapping[EngineId, PreflightResult],
        installed: Sequence[EngineId],
        conformant: Sequence[EngineId],
    ) -> str:
        if conformant:
            return f"recorded conformance for agent(s): {self._names(conformant)}"
        if installed:
            return (
                "Run `vibey doctor --conformance --record "
                f"{project_id}` for at least one installed engine: {self._names(installed)}."
            )
        return (
            "Install at least one configured engine: "
            f"{self._names(tuple(preflights)) or 'the configured pool is empty'}."
        )
