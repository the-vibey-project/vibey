# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from vibey.application.dto import (
    EngineHealthRecord,
    FeasibilityAssessment,
    PreflightResult,
)
from vibey.application.interfaces.preflight_interface import (
    FeasibilityAssessmentInterface,
    StartupPreflightReportInterface,
)
from vibey.application.preflight import ConductorPreflight
from vibey.domain.circuit import CircuitState
from vibey.domain.engine import EngineId


def _health(engine_id: EngineId, *, conformant: bool) -> EngineHealthRecord:
    return EngineHealthRecord(
        project_id=uuid4(),
        engine_id=engine_id,
        installed=True,
        version="1",
        conformance_ok=conformant,
        conformance_at=datetime.now(UTC) if conformant else None,
        auth_ok_at=datetime.now(UTC),
        circuit=CircuitState.CLOSED,
        capacity_state=None,
        resets_at=None,
        probe_next_at=None,
        probe_attempt=0,
        consecutive_fail=0,
        ewma_failure=0.0,
        cost_usd_cycle=0.0,
        selected_count=0,
    )


async def test_conductor_preflight_refreshes_health_then_evaluates_the_same_evidence() -> None:
    project_id = uuid4()
    claude = PreflightResult(installed=True, version="1", auth_ok=True)
    codex = PreflightResult(installed=True, version="2", auth_ok=True)
    adapters = {
        EngineId.CLAUDELOOP: SimpleNamespace(preflight=AsyncMock(return_value=claude)),
        EngineId.CODEXLOOP: SimpleNamespace(preflight=AsyncMock(return_value=codex)),
    }
    records = (
        _health(EngineId.CLAUDELOOP, conformant=True),
        _health(EngineId.CODEXLOOP, conformant=False),
    )
    health = SimpleNamespace(
        record_preflight=AsyncMock(),
        list_for_project=AsyncMock(return_value=records),
    )
    assessment = FeasibilityAssessment(
        status="unknown",
        blocked_at=None,
        first_repair=None,
        confidence=0.5,
        required=6,
        required_measured=3,
    )
    feasibility = Mock()
    feasibility.evaluate.return_value = assessment

    preflight = ConductorPreflight(
        health=health,  # type: ignore[arg-type]
        feasibility=feasibility,
    )
    report = await preflight.run(
        project_id=project_id,
        adapters=adapters,  # type: ignore[arg-type]
    )

    health.record_preflight.assert_any_await(project_id, EngineId.CLAUDELOOP, claude)
    health.record_preflight.assert_any_await(project_id, EngineId.CODEXLOOP, codex)
    health.list_for_project.assert_awaited_once_with(project_id)
    feasibility.evaluate.assert_called_once_with(
        project_id=project_id,
        preflights={EngineId.CLAUDELOOP: claude, EngineId.CODEXLOOP: codex},
        health_records=records,
    )
    assert report.ineligible_engines == (EngineId.CODEXLOOP,)
    assert report.feasibility is assessment
    assert isinstance(assessment, FeasibilityAssessmentInterface)
    assert isinstance(report, StartupPreflightReportInterface)
