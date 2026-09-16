# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Per-job selection inputs, the selecting provider, and outcome recording."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from tests.application.test_engine_selector import (
    FakeEngineHealthRepository,
    FakeRotationCursorRepository,
    _healthy_record,
)
from vibey.application.dto import JobRecord
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.engine_selection import (
    RotationRecordingHandler,
    SelectingEngineProvider,
    selection_inputs_for_job,
)
from vibey.application.engine_selector import EngineSelector
from vibey.application.worker import CapacityDeferred, Defer, Failure, Outcome, Success
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId
from vibey.domain.job import FailureClass
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID

NOW = datetime(2026, 8, 19, tzinfo=UTC)


class FixedClock:
    def now(self) -> datetime:
        return NOW


def _implement_job(**overrides: object) -> JobRecord:
    return replace(make_job(uuid4(), attempts=1), **overrides)  # type: ignore[arg-type]


# ── selection_inputs_for_job ─────────────────────────────────────────────────


def test_first_attempt_has_no_affinity_and_no_exclusion() -> None:
    inputs = selection_inputs_for_job(_implement_job(attempts=1))

    assert inputs.requirement.effort is Effort.LOW
    assert inputs.requirement.excluded == frozenset()
    assert inputs.affinity is None


def test_same_tier_retry_sticks_to_the_previous_engine() -> None:
    job = _implement_job(attempts=2, assigned_engine="claudeloop")

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.effort is Effort.LOW
    assert inputs.affinity is EngineId.CLAUDELOOP
    assert inputs.requirement.excluded == frozenset()


def test_tier_crossing_forces_rotation_away_from_the_previous_engine() -> None:
    job = _implement_job(attempts=3, assigned_engine="claudeloop")

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.effort is Effort.STANDARD
    assert inputs.requirement.excluded == frozenset({EngineId.CLAUDELOOP})
    assert inputs.affinity is None


def test_attempt_four_is_a_same_tier_retry_again() -> None:
    job = _implement_job(attempts=4, assigned_engine="agyloop")

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.effort is Effort.STANDARD
    assert inputs.affinity is EngineId.AGYLOOP


def test_attempt_five_crosses_to_high_and_rotates() -> None:
    job = _implement_job(attempts=5, assigned_engine="agyloop")

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.effort is Effort.HIGH
    assert inputs.requirement.excluded == frozenset({EngineId.AGYLOOP})


def test_exhausted_ladder_selects_as_high_without_raising() -> None:
    """Attempt 7 is the handler's Park; selection must not preempt it."""
    job = _implement_job(attempts=7, assigned_engine="claudeloop")

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.effort is Effort.HIGH


def test_retry_without_a_recorded_previous_engine_has_no_constraints() -> None:
    inputs = selection_inputs_for_job(_implement_job(attempts=3, assigned_engine=None))

    assert inputs.requirement.excluded == frozenset()
    assert inputs.affinity is None


def test_verify_excludes_the_implementer_at_low_effort() -> None:
    job = replace(
        make_job(uuid4(), attempts=1),
        kind="build.verify",
        requirement={"implementer_engine_id": "codexloop"},
    )

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.effort is Effort.LOW
    assert inputs.requirement.excluded == frozenset({EngineId.CODEXLOOP})
    assert inputs.affinity is None


def test_verify_without_an_implementer_excludes_nothing() -> None:
    job = replace(make_job(uuid4(), attempts=1), kind="build.verify", requirement={})

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.excluded == frozenset()


# ── the one-engine pool's verify-independence waiver ─────────────────────────


def _verify_job(implementer: str, **overrides: object) -> JobRecord:
    requirement: dict[str, object] = {"implementer_engine_id": implementer}
    requirement.update(overrides)
    return replace(make_job(uuid4(), attempts=1), kind="build.verify", requirement=requirement)


def test_an_unknown_pool_keeps_verify_independence_absolute() -> None:
    """The default: a caller that cannot say what engines exist gets the
    strict rule, exclusion and all."""
    inputs = selection_inputs_for_job(_verify_job("codexloop"))

    assert inputs.requirement.excluded == frozenset({EngineId.CODEXLOOP})
    assert inputs.independence_waived is False


def test_a_pool_with_a_second_engine_still_excludes_the_implementer() -> None:
    inputs = selection_inputs_for_job(
        _verify_job("codexloop"),
        pool=frozenset({EngineId.CODEXLOOP, EngineId.CLAUDELOOP}),
    )

    assert inputs.requirement.excluded == frozenset({EngineId.CODEXLOOP})
    assert inputs.independence_waived is False


def test_a_one_engine_pool_lets_the_implementer_verify_its_own_work() -> None:
    """The wave-0 blocker: with `--engines qwenloop` the exclusion emptied
    the eligible set, NoEligibleEngine became a CapacityDeferred, and BUILD
    retried forever with no park and nothing in the ledger."""
    inputs = selection_inputs_for_job(_verify_job("qwenloop"), pool=frozenset({EngineId.QWENLOOP}))

    assert inputs.requirement.excluded == frozenset()
    assert inputs.requirement.effort is Effort.LOW
    assert inputs.independence_waived is True


def test_a_durable_exclusion_that_empties_the_pool_waives_independence_too() -> None:
    """The rule is "would this exclusion leave nobody", not "is the pool
    exactly one engine": a wind-down exclusion can take the last reviewer
    just as effectively as a small pool."""
    inputs = selection_inputs_for_job(
        _verify_job("claudeloop", excluded_engine_ids=["codexloop"]),
        pool=frozenset({EngineId.CLAUDELOOP, EngineId.CODEXLOOP}),
    )

    assert inputs.requirement.excluded == frozenset({EngineId.CODEXLOOP})
    assert inputs.independence_waived is True


def test_a_pool_that_does_not_contain_the_implementer_keeps_the_exclusion() -> None:
    """A stale implementer id (the engine has since been removed from the
    pool) leaves real reviewers available, so nothing is waived."""
    inputs = selection_inputs_for_job(_verify_job("agyloop"), pool=frozenset({EngineId.CLAUDELOOP}))

    assert inputs.requirement.excluded == frozenset({EngineId.AGYLOOP})
    assert inputs.independence_waived is False


def test_implement_jobs_never_waive_anything() -> None:
    inputs = selection_inputs_for_job(
        _implement_job(attempts=3, assigned_engine="claudeloop"),
        pool=frozenset({EngineId.CLAUDELOOP}),
    )

    assert inputs.requirement.excluded == frozenset({EngineId.CLAUDELOOP})
    assert inputs.independence_waived is False


# ── SelectingEngineProvider ──────────────────────────────────────────────────


class _Adapter:
    def __init__(self, engine_id: EngineId) -> None:
        self.descriptor = BY_ENGINE_ID[engine_id]


class _StandbyAdapter(_Adapter):
    async def preflight(self):  # type: ignore[no-untyped-def]
        from vibey.application.dto import PreflightResult

        return PreflightResult(installed=True, version="0.1.0", auth_ok=True)


async def _provider(
    engines: list[EngineId],
    *,
    adapters: dict[EngineId, _Adapter] | None = None,
    allow_list: frozenset[EngineId] | None = None,
) -> tuple[SelectingEngineProvider, EngineHealthService, FakeJobRepository, object]:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    for engine_id in engines:
        await repo.upsert(_healthy_record(project_id, engine_id))
    health = EngineHealthService(repo)
    selector = EngineSelector(
        health_service=health,
        cursor_repository=FakeRotationCursorRepository(),
        descriptors=BY_ENGINE_ID,
    )
    jobs = FakeJobRepository()
    provider = SelectingEngineProvider(
        selector=selector,
        health=health,
        adapters=adapters
        if adapters is not None
        else {engine_id: _Adapter(engine_id) for engine_id in engines},
        jobs=jobs,
        clock=FixedClock(),
        owner="w1",
        allow_list=allow_list,
    )
    return provider, health, jobs, project_id


async def test_select_for_records_selection_and_assigns_the_engine() -> None:
    provider, health, jobs, project_id = await _provider([EngineId.CLAUDELOOP])
    job = replace(make_job(project_id, attempts=1), project_id=project_id, lease_owner="w1")
    from vibey.domain.job import JobState

    job = replace(job, state=JobState.LEASED)
    jobs._jobs[job.id] = job

    adapter = await provider.select_for(jobs._jobs[job.id])

    assert adapter.descriptor.engine_id is EngineId.CLAUDELOOP
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)
    assert record.selected_count == 1
    stored = jobs._jobs[job.id]
    assert stored.assigned_engine == "claudeloop"


async def test_no_eligible_engine_becomes_capacity_deferred() -> None:
    provider, _, jobs, project_id = await _provider([])
    job = replace(make_job(project_id, attempts=1), project_id=project_id)

    with pytest.raises(CapacityDeferred) as excinfo:
        await provider.select_for(job)

    assert excinfo.value.retry_at == NOW + timedelta(minutes=5)


async def test_the_pool_is_the_adapters_narrowed_by_the_allow_list() -> None:
    provider, _, _, _ = await _provider(
        [EngineId.CLAUDELOOP, EngineId.CODEXLOOP],
        allow_list=frozenset({EngineId.CLAUDELOOP}),
    )

    assert provider.pool == frozenset({EngineId.CLAUDELOOP})


async def test_an_unrestricted_pool_is_every_configured_adapter() -> None:
    provider, _, _, _ = await _provider([EngineId.CLAUDELOOP, EngineId.CODEXLOOP])

    assert provider.pool == frozenset({EngineId.CLAUDELOOP, EngineId.CODEXLOOP})


async def test_a_one_engine_pool_selects_the_implementer_for_verify() -> None:
    """Regression: `--engines qwenloop` deferred every build.verify job
    forever, because the implementer exclusion left nothing eligible."""
    provider, _, _, project_id = await _provider(
        [EngineId.QWENLOOP], allow_list=frozenset({EngineId.QWENLOOP})
    )
    job = replace(
        make_job(project_id, attempts=1),
        project_id=project_id,
        kind="build.verify",
        requirement={"implementer_engine_id": "qwenloop"},
    )

    adapter = await provider.select_for(job)

    assert adapter.descriptor.engine_id is EngineId.QWENLOOP


async def test_a_two_engine_pool_still_rotates_the_verify_away() -> None:
    provider, _, _, project_id = await _provider([EngineId.CLAUDELOOP, EngineId.CODEXLOOP])
    job = replace(
        make_job(project_id, attempts=1),
        project_id=project_id,
        kind="build.verify",
        requirement={"implementer_engine_id": "codexloop"},
    )

    adapter = await provider.select_for(job)

    assert adapter.descriptor.engine_id is EngineId.CLAUDELOOP


async def test_selected_engine_without_a_configured_adapter_defers() -> None:
    provider, _, jobs, project_id = await _provider([EngineId.CLAUDELOOP], adapters={})
    job = replace(make_job(project_id, attempts=1), project_id=project_id)

    with pytest.raises(CapacityDeferred) as excinfo:
        await provider.select_for(job)

    assert "no configured adapter" in excinfo.value.detail


async def test_enabled_qwenloop_preflights_then_falls_back() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    health = EngineHealthService(repo)
    jobs = FakeJobRepository()
    standby = _StandbyAdapter(EngineId.QWENLOOP)
    provider = SelectingEngineProvider(
        selector=EngineSelector(
            health_service=health,
            cursor_repository=FakeRotationCursorRepository(),
            descriptors=BY_ENGINE_ID,
        ),
        health=health,
        adapters={EngineId.QWENLOOP: standby},
        jobs=jobs,
        clock=FixedClock(),
        owner="w1",
        standby_engine=EngineId.QWENLOOP,
    )
    job = replace(make_job(project_id, attempts=1), project_id=project_id)
    selected = await provider.select_for(job)
    assert selected is standby
    record = await health.get_or_create(project_id, EngineId.QWENLOOP)
    assert record.installed and record.conformance_ok


async def test_missing_standby_adapter_does_not_block_paid_selection() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    paid = _Adapter(EngineId.CLAUDELOOP)
    provider = SelectingEngineProvider(
        selector=EngineSelector(
            health_service=health,
            cursor_repository=FakeRotationCursorRepository(),
            descriptors=BY_ENGINE_ID,
        ),
        health=health,
        adapters={EngineId.CLAUDELOOP: paid},
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        owner="w1",
        standby_engine=EngineId.QWENLOOP,
    )

    selected = await provider.select_for(
        replace(make_job(project_id, attempts=1), project_id=project_id)
    )

    assert selected is paid


# ── RotationRecordingHandler ─────────────────────────────────────────────────


class _FixedInner:
    def __init__(self, outcome: Outcome) -> None:
        self._outcome = outcome

    async def handle(self, job: JobRecord) -> Outcome:
        return self._outcome


async def _recording(
    outcome: Outcome,
) -> tuple[RotationRecordingHandler, EngineHealthService, object]:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    handler = RotationRecordingHandler(
        inner=_FixedInner(outcome),
        health=health,
        project_id=project_id,  # type: ignore[arg-type]
        engine_id=EngineId.CLAUDELOOP,
    )
    return handler, health, project_id


async def test_success_closes_the_circuit_and_records() -> None:
    handler, health, project_id = await _recording(Success())

    outcome = await handler.handle(make_job(uuid4()))

    assert isinstance(outcome, Success)
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.circuit == "closed"
    assert record.consecutive_fail == 0


async def test_capacity_defer_opens_the_circuit_with_the_defer_deadline() -> None:
    retry_at = NOW + timedelta(minutes=5)
    handler, health, project_id = await _recording(Defer(retry_at, "capacity", capacity=True))

    outcome = await handler.handle(make_job(uuid4()))

    assert isinstance(outcome, Defer)
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.circuit == "open"
    assert record.resets_at == retry_at


async def test_failure_outcomes_record_nothing() -> None:
    handler, health, project_id = await _recording(Failure(FailureClass.WORK, "nope"))

    outcome = await handler.handle(make_job(uuid4()))

    assert isinstance(outcome, Failure)
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.circuit == "closed"
    assert record.selected_count == 0


def test_requirement_excluded_engine_ids_are_honored() -> None:
    """The wind-down follow-up's durable "never back to the engine that
    wound down" constraint rides on the job requirement."""
    job = replace(_implement_job(attempts=1), requirement={"excluded_engine_ids": ["claudeloop"]})

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.excluded == frozenset({EngineId.CLAUDELOOP})
    assert inputs.affinity is None


def test_requirement_exclusion_suppresses_same_tier_affinity() -> None:
    job = replace(
        _implement_job(attempts=2, assigned_engine="claudeloop"),
        requirement={"excluded_engine_ids": ("claudeloop",)},
    )

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.excluded == frozenset({EngineId.CLAUDELOOP})
    assert inputs.affinity is None


def test_requirement_exclusion_composes_with_the_verify_implementer_rule() -> None:
    job = replace(
        make_job(uuid4(), attempts=1),
        kind="build.verify",
        requirement={
            "implementer_engine_id": "codexloop",
            "excluded_engine_ids": ["claudeloop"],
        },
    )

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.excluded == frozenset({EngineId.CODEXLOOP, EngineId.CLAUDELOOP})


def test_non_list_excluded_engine_ids_are_ignored() -> None:
    job = replace(_implement_job(attempts=1), requirement={"excluded_engine_ids": "claudeloop"})

    inputs = selection_inputs_for_job(job)

    assert inputs.requirement.excluded == frozenset()


async def test_non_capacity_defer_never_opens_the_circuit() -> None:
    """Caught live: verify-repair waits are Defers too, and recording them
    as capacity rejections opened both engines' circuits and stalled the
    project on "No engines meet requirements"."""
    retry_at = NOW + timedelta(minutes=10)
    handler, health, project_id = await _recording(Defer(retry_at, "repair in flight"))

    outcome = await handler.handle(make_job(uuid4()))

    assert isinstance(outcome, Defer)
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.circuit == "closed"
    assert record.resets_at is None
