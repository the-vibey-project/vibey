# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from uuid import UUID, uuid4

from vibey_gh.feasibility import FeasibilityEvaluator, Pipeline, Stage

from vibey.application.dto import EngineHealthRecord, PreflightResult
from vibey.application.interfaces.preflight_interface import RunFeasibilityEvaluatorInterface
from vibey.domain.circuit import CircuitState
from vibey.domain.engine import EngineId
from vibey.infrastructure.preflight_feasibility import VibeyGhFeasibilityAdapter


def _health(
    project_id: UUID,
    engine_id: EngineId,
    *,
    conformant: bool,
) -> EngineHealthRecord:
    return EngineHealthRecord(
        project_id=project_id,
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


def _preflight(*, installed: bool = True, authenticated: bool = True) -> PreflightResult:
    return PreflightResult(
        installed=installed, version="1" if installed else None, auth_ok=authenticated
    )


def test_adapter_satisfies_the_conductor_port() -> None:
    assert isinstance(VibeyGhFeasibilityAdapter(), RunFeasibilityEvaluatorInterface)


def test_no_installed_engine_is_infeasible_and_names_installation_first() -> None:
    project_id = uuid4()
    assessment = VibeyGhFeasibilityAdapter().evaluate(
        project_id=project_id,
        preflights={
            EngineId.CLAUDELOOP: _preflight(installed=False, authenticated=False),
            EngineId.CODEXLOOP: _preflight(installed=False, authenticated=False),
        },
        health_records=(),
    )

    assert assessment.status == "infeasible"
    assert assessment.blocked_at == "interview"
    assert assessment.first_repair is not None
    assert assessment.first_repair.startswith("software.availability — Install")
    assert "claudeloop, codexloop" in assessment.first_repair


def test_empty_engine_pool_is_a_measured_floor_not_an_exception() -> None:
    assessment = VibeyGhFeasibilityAdapter().evaluate(
        project_id=uuid4(),
        preflights={},
        health_records=(),
    )

    assert assessment.status == "infeasible"
    assert assessment.first_repair is not None
    assert "configured pool is empty" in assessment.first_repair


def test_installed_engine_without_a_health_row_names_conformance_as_the_repair() -> None:
    project_id = uuid4()
    assessment = VibeyGhFeasibilityAdapter().evaluate(
        project_id=project_id,
        preflights={EngineId.CLAUDELOOP: _preflight()},
        health_records=(),
    )

    assert assessment.status == "infeasible"
    assert assessment.first_repair is not None
    assert f"vibey doctor --conformance --record {project_id}" in assessment.first_repair


def test_fresh_auth_failure_is_an_agency_shortfall_and_leads_the_repairs() -> None:
    project_id = uuid4()
    assessment = VibeyGhFeasibilityAdapter().evaluate(
        project_id=project_id,
        preflights={EngineId.CLAUDELOOP: _preflight(authenticated=False)},
        health_records=(_health(project_id, EngineId.CLAUDELOOP, conformant=True),),
    )

    assert assessment.status == "infeasible"
    assert assessment.blocked_at == "feature-branch"
    assert assessment.first_repair is not None
    assert assessment.first_repair.startswith("agency.availability — Authenticate")


def test_usable_engine_leaves_unmeasured_coordinates_unknown() -> None:
    project_id = uuid4()
    assessment = VibeyGhFeasibilityAdapter().evaluate(
        project_id=project_id,
        preflights={EngineId.CLAUDELOOP: _preflight()},
        health_records=(_health(project_id, EngineId.CLAUDELOOP, conformant=True),),
    )

    assert assessment.status == "unknown"
    assert assessment.blocked_at is None
    assert assessment.first_repair is None
    assert assessment.required == 6
    assert assessment.required_measured == 2
    assert assessment.confidence == 0.3333


def test_injected_pipeline_can_produce_a_fully_measured_feasible_verdict() -> None:
    project_id = uuid4()
    pipeline = Pipeline(
        (
            Stage.needing(
                "run",
                "one engine-driven run",
                "agent",
                "software",
            ),
        )
    )
    adapter = VibeyGhFeasibilityAdapter(
        operation="run",
        start=None,
        pipeline=pipeline,
        evaluator=FeasibilityEvaluator(),
    )

    assessment = adapter.evaluate(
        project_id=project_id,
        preflights={EngineId.CLAUDELOOP: _preflight()},
        health_records=(_health(project_id, EngineId.CLAUDELOOP, conformant=True),),
    )

    assert assessment.status == "feasible"
    assert assessment.confidence == 1.0
    assert assessment.required == assessment.required_measured == 2
