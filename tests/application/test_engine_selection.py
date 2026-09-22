# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Per-job selection inputs, the selecting provider, and outcome recording."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from tests.application.fakes import FakeJobRepository, make_job
from tests.application.test_engine_selector import (
    FakeEngineHealthRepository,
    FakeRotationCursorRepository,
    _healthy_record,
)
from vibey.application.dto import EngineEvent, JobRecord
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.engine_selection import (
    RotationRecordingHandler,
    SelectingEngineProvider,
    SpendMeteringLedger,
    selection_inputs_for_job,
)
from vibey.application.engine_selector import EngineSelector
from vibey.application.interfaces import BuildLedger, SpendMeteringLedgerInterface
from vibey.application.worker import CapacityDeferred, Defer, Failure, Outcome, Success
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId
from vibey.domain.job import FailureClass
from vibey.domain.phase_timing import PhaseSpend
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID
from vibey.infrastructure.otel import TelemetryMetrics

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
    metrics: TelemetryMetrics | None = None,
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
        metrics=metrics,
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


async def test_select_for_records_telemetry_when_metrics_are_configured() -> None:
    metrics = TelemetryMetrics()
    provider, _, jobs, project_id = await _provider([EngineId.CLAUDELOOP], metrics=metrics)
    job = replace(make_job(project_id, attempts=1), project_id=project_id, lease_owner="w1")
    from vibey.domain.job import JobState

    jobs._jobs[job.id] = replace(job, state=JobState.LEASED)

    await provider.select_for(jobs._jobs[job.id])

    assert metrics.export_metrics(project_id)["engine_selections"] == {"claudeloop": 1}


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


class _SelectsAnEngineWithNoAdapter:
    """A selector that ignores the allow-list it is handed -- the defence below is for
    exactly the selector that misbehaves, so only a misbehaving one can reach it."""

    async def select_engine(self, project_id, requirement, **_: object):  # type: ignore[no-untyped-def]
        return EngineId.AGYLOOP, None


async def test_selected_engine_without_a_configured_adapter_defers() -> None:
    repo = FakeEngineHealthRepository()
    health = EngineHealthService(repo)
    provider = SelectingEngineProvider(
        selector=_SelectsAnEngineWithNoAdapter(),  # type: ignore[arg-type]
        health=health,
        adapters={EngineId.CLAUDELOOP: _Adapter(EngineId.CLAUDELOOP)},
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        owner="w1",
    )
    project_id = uuid4()
    job = replace(make_job(project_id, attempts=1), project_id=project_id)

    with pytest.raises(CapacityDeferred) as excinfo:
        await provider.select_for(job)

    assert "no configured adapter" in excinfo.value.detail


async def test_selection_is_confined_to_the_pool_not_every_health_row() -> None:
    """A health row outlives the switch that wrote it. A local engine switched off
    since -- and now *preferred* by tier -- must not be offered to a worker with no
    adapter for it: that deferred the job forever instead of running a paid engine."""
    provider, _, _, project_id = await _provider(
        [EngineId.CLAUDELOOP, EngineId.QWENLOOP],
        adapters={EngineId.CLAUDELOOP: _Adapter(EngineId.CLAUDELOOP)},
    )
    job = replace(make_job(project_id, attempts=1), project_id=project_id)

    adapter = await provider.select_for(job)

    assert adapter.descriptor.engine_id is EngineId.CLAUDELOOP


class _LocalAdapter(_Adapter):
    """A local engine whose `doctor` passes (or not), counting how often it is asked."""

    def __init__(self, engine_id: EngineId, *, ready: bool = True) -> None:
        super().__init__(engine_id)
        self.ready = ready
        self.preflights = 0

    async def preflight(self):  # type: ignore[no-untyped-def]
        from vibey.application.dto import PreflightResult

        self.preflights += 1
        return PreflightResult(installed=True, version="0.1.0", auth_ok=self.ready)


def _local_provider(
    health: EngineHealthService,
    adapters: dict[EngineId, _Adapter],
    *,
    local_engines: tuple[EngineId, ...],
    allow_list: frozenset[EngineId] | None = None,
) -> SelectingEngineProvider:
    return SelectingEngineProvider(
        selector=EngineSelector(
            health_service=health,
            cursor_repository=FakeRotationCursorRepository(),
            descriptors=BY_ENGINE_ID,
        ),
        health=health,
        adapters=adapters,
        jobs=FakeJobRepository(),
        clock=FixedClock(),
        owner="w1",
        allow_list=allow_list,
        local_engines=local_engines,
    )


async def test_an_enabled_local_engine_is_preflighted_then_preferred() -> None:
    """No cron records a local engine's health, so each selection refreshes it -- and
    once its `doctor` passes it is preferred over a healthy paid engine (8.a)."""
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    local = _LocalAdapter(EngineId.QWENLOOP)
    provider = _local_provider(
        health,
        {EngineId.CLAUDELOOP: _Adapter(EngineId.CLAUDELOOP), EngineId.QWENLOOP: local},
        local_engines=(EngineId.QWENLOOP,),
    )

    selected = await provider.select_for(
        replace(make_job(project_id, attempts=1), project_id=project_id)
    )

    assert selected is local
    assert local.preflights == 1
    record = await health.get_or_create(project_id, EngineId.QWENLOOP)
    assert record.installed and record.conformance_ok


async def test_a_local_engine_whose_doctor_fails_falls_back_to_paid() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    paid = _Adapter(EngineId.CLAUDELOOP)
    provider = _local_provider(
        health,
        {
            EngineId.CLAUDELOOP: paid,
            EngineId.QWENLOOP: _LocalAdapter(EngineId.QWENLOOP, ready=False),
        },
        local_engines=(EngineId.QWENLOOP,),
    )

    selected = await provider.select_for(
        replace(make_job(project_id, attempts=1), project_id=project_id)
    )

    assert selected is paid
    record = await health.get_or_create(project_id, EngineId.QWENLOOP)
    assert record.conformance_ok is False


async def test_every_enabled_local_engine_is_refreshed_not_just_qwenloop() -> None:
    health = EngineHealthService(FakeEngineHealthRepository())
    project_id = uuid4()
    qwen = _LocalAdapter(EngineId.QWENLOOP)
    claude_local = _LocalAdapter(EngineId.CLAUDELOOP_LOCAL)
    provider = _local_provider(
        health,
        {EngineId.QWENLOOP: qwen, EngineId.CLAUDELOOP_LOCAL: claude_local},
        local_engines=(EngineId.QWENLOOP, EngineId.CLAUDELOOP_LOCAL),
    )

    selected = await provider.select_for(
        replace(make_job(project_id, attempts=1), project_id=project_id)
    )

    assert selected in (qwen, claude_local)
    assert (qwen.preflights, claude_local.preflights) == (1, 1)


async def test_a_local_engine_outside_the_pool_is_neither_preflighted_nor_selected() -> None:
    """A switch that is on, narrowed away by `--engines`, and an enabled engine this
    worker has no adapter for: neither costs a `doctor` run, neither blocks selection."""
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    paid = _Adapter(EngineId.CLAUDELOOP)
    narrowed = _LocalAdapter(EngineId.QWENLOOP)
    provider = _local_provider(
        health,
        {EngineId.CLAUDELOOP: paid, EngineId.QWENLOOP: narrowed},
        local_engines=(EngineId.QWENLOOP, EngineId.CLAUDELOOP_LOCAL),
        allow_list=frozenset({EngineId.CLAUDELOOP}),
    )

    selected = await provider.select_for(
        replace(make_job(project_id, attempts=1), project_id=project_id)
    )

    assert selected is paid
    assert narrowed.preflights == 0


async def test_verify_rotates_from_one_local_engine_to_the_other() -> None:
    """Independence holds inside the local tier: qwenloop implemented, so the review
    goes to claudeloop-local, not back to qwenloop and not out to a paid engine."""
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    claude_local = _LocalAdapter(EngineId.CLAUDELOOP_LOCAL)
    provider = _local_provider(
        health,
        {
            EngineId.CLAUDELOOP: _Adapter(EngineId.CLAUDELOOP),
            EngineId.QWENLOOP: _LocalAdapter(EngineId.QWENLOOP),
            EngineId.CLAUDELOOP_LOCAL: claude_local,
        },
        local_engines=(EngineId.QWENLOOP, EngineId.CLAUDELOOP_LOCAL),
    )
    job = replace(
        make_job(project_id, attempts=1),
        project_id=project_id,
        kind="build.verify",
        requirement={"implementer_engine_id": "qwenloop"},
    )

    assert await provider.select_for(job) is claude_local


async def test_verify_falls_back_to_paid_when_the_implementer_is_the_only_local_engine() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    paid = _Adapter(EngineId.CLAUDELOOP)
    provider = _local_provider(
        health,
        {EngineId.CLAUDELOOP: paid, EngineId.QWENLOOP: _LocalAdapter(EngineId.QWENLOOP)},
        local_engines=(EngineId.QWENLOOP,),
    )
    job = replace(
        make_job(project_id, attempts=1),
        project_id=project_id,
        kind="build.verify",
        requirement={"implementer_engine_id": "qwenloop"},
    )

    assert await provider.select_for(job) is paid


async def test_a_qwenloop_only_pool_still_verifies_its_own_work() -> None:
    """#179's waiver survives the tiering: a sovereign single-engine pool reviews its own
    diff rather than deferring forever."""
    health = EngineHealthService(FakeEngineHealthRepository())
    project_id = uuid4()
    qwen = _LocalAdapter(EngineId.QWENLOOP)
    provider = _local_provider(
        health,
        {EngineId.QWENLOOP: qwen},
        local_engines=(EngineId.QWENLOOP,),
        allow_list=frozenset({EngineId.QWENLOOP}),
    )
    job = replace(
        make_job(project_id, attempts=1),
        project_id=project_id,
        kind="build.verify",
        requirement={"implementer_engine_id": "qwenloop"},
    )

    assert await provider.select_for(job) is qwen


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


@pytest.mark.parametrize("failure_class", [FailureClass.WORK, FailureClass.VIBEY])
async def test_work_and_vibey_failures_record_nothing(failure_class: FailureClass) -> None:
    """The code being wrong, or vibey being wrong, is never the engine's fault."""
    handler, health, project_id = await _recording(Failure(failure_class, "nope"))

    outcome = await handler.handle(make_job(uuid4()))

    assert isinstance(outcome, Failure)
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.circuit == "closed"
    assert record.consecutive_fail == 0
    assert record.selected_count == 0


async def test_an_engine_failure_is_recorded_against_the_engine() -> None:
    handler, health, project_id = await _recording(Failure(FailureClass.ENGINE, "exit 137"))

    outcome = await handler.handle(make_job(uuid4()))

    assert outcome == Failure(FailureClass.ENGINE, "exit 137")
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.consecutive_fail == 1
    assert record.circuit == "closed"


async def test_the_third_engine_failure_opens_the_circuit_with_a_probe_time() -> None:
    handler, health, project_id = await _recording(Failure(FailureClass.ENGINE, "exit 137"))

    for _ in range(3):
        await handler.handle(make_job(uuid4()))

    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.circuit == "open"
    assert record.consecutive_fail == 3
    assert record.probe_next_at is not None


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


async def test_a_capacity_rejected_diff_review_opens_the_reviewers_circuit(
    tmp_path: Path,
) -> None:
    """#215, end to end through the real verify handler: the reviewer that
    ran out must have its circuit opened, or the next claim selects the
    same exhausted engine for the same verify job again."""
    from tests.application.test_build_verify_handler import (
        FakeGateRunner,
        FakeLedger,
        FakeWorktrees,
        _capacity_rejected_review,
    )
    from tests.application.test_build_verify_handler import _job as _verify_job
    from vibey.application.build_verify_handler import BuildVerifyHandler
    from vibey.infrastructure.engines.descriptors import CODEXLOOP
    from vibey.infrastructure.engines.scripted import ScriptedEngine

    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CODEXLOOP))
    health = EngineHealthService(repo)
    handler = RotationRecordingHandler(
        inner=BuildVerifyHandler(
            worktrees=FakeWorktrees(tmp_path),
            gates=FakeGateRunner(),
            reviewer=ScriptedEngine(
                descriptor=CODEXLOOP,
                base_dir=tmp_path / "engine",
                script=_capacity_rejected_review(),
            ),
            ledger=FakeLedger(),
            jobs=FakeJobRepository(),
            clock=FixedClock(),
        ),
        health=health,
        project_id=project_id,
        engine_id=EngineId.CODEXLOOP,
    )

    outcome = await handler.handle(
        _verify_job(project_id=project_id, requirement={"implementer_engine_id": "claudeloop"})
    )

    assert isinstance(outcome, Defer)
    assert outcome.capacity is True
    record = await health.get_or_create(project_id, EngineId.CODEXLOOP)
    assert record.circuit == "open"
    assert record.capacity_state == "CreditsExhausted"
    # CreditsExhausted deliberately carries no resets_at (ADR-0040): the
    # type system forbids inventing a deadline; the probe is exponential.
    assert record.resets_at is None
    assert record.probe_next_at is not None


async def test_the_selecting_provider_satisfies_the_engine_provider_protocol() -> None:
    """ADR-0016: `pool` -- the surface `BuildVerifyHandler` reads to apply the
    independence waiver -- is declared on a protocol in
    `application/interfaces/`, not invented by its one implementation."""
    from vibey.application.interfaces.engines import EngineProvider

    provider, _, _, _ = await _provider([EngineId.CLAUDELOOP])

    assert isinstance(provider, EngineProvider)
    assert provider.pool == frozenset({EngineId.CLAUDELOOP})


# ── SpendMeteringLedger: per-job spend, by the brake's own rule (#209) ──────────


class _RecordingLedger:
    def __init__(self, *, fail: bool = False) -> None:
        self.calls: list[dict[str, object]] = []
        self._fail = fail

    async def record(self, **kwargs: object) -> None:
        if self._fail:
            raise RuntimeError("ledger append failed")
        self.calls.append(kwargs)


def _engine_event(kind: str, **payload: object) -> EngineEvent:
    return EngineEvent(kind=kind, at=NOW, payload=payload)


async def _record(ledger: BuildLedger, event: EngineEvent, **overrides: object) -> None:
    kwargs: dict[str, object] = {
        "project_id": uuid4(),
        "cycle": 2,
        "job_id": uuid4(),
        "engine_id": EngineId.CLAUDELOOP,
        "correlation_id": uuid4(),
        "causation_id": uuid4(),
        "event": event,
    }
    kwargs.update(overrides)
    await ledger.record(**kwargs)  # type: ignore[arg-type]


async def test_the_meter_forwards_every_event_unchanged_and_in_order() -> None:
    inner = _RecordingLedger()
    meter = SpendMeteringLedger(inner)
    events = [
        _engine_event("SessionSeeded", seed_digest="x"),
        _engine_event("TurnCompleted", cost_usd=0.01),
        _engine_event("NotAKindVibeyKnows", cost_usd=9.0),
        _engine_event("VerdictRendered", complete=True),
    ]
    project_id, job_id, correlation_id, causation_id = uuid4(), uuid4(), uuid4(), uuid4()

    for event in events:
        await meter.record(
            project_id=project_id,
            cycle=2,
            job_id=job_id,
            engine_id=EngineId.CODEXLOOP,
            correlation_id=correlation_id,
            causation_id=causation_id,
            event=event,
        )
    await meter.record(
        project_id=project_id,
        cycle=2,
        job_id=job_id,
        engine_id=None,
        correlation_id=correlation_id,
        event=events[0],
    )

    assert [call["event"] for call in inner.calls] == [*events, events[0]]
    assert inner.calls[0] == {
        "project_id": project_id,
        "cycle": 2,
        "job_id": job_id,
        "engine_id": EngineId.CODEXLOOP,
        "correlation_id": correlation_id,
        "causation_id": causation_id,
        "event": events[0],
    }
    assert inner.calls[-1]["causation_id"] is None
    assert inner.calls[-1]["engine_id"] is None


async def test_the_meter_sums_spend_by_the_one_ledger_spend_rule() -> None:
    meter = SpendMeteringLedger(_RecordingLedger())

    for event in (
        _engine_event("TurnCompleted", cost_usd=0.25),
        _engine_event("TurnCompleted"),  # chatter.assistant: a turn, no cost
        _engine_event("TurnCompleted", cost_usd=True),  # a bool is not a dollar
        _engine_event("TurnCompleted", cost_usd="n/a"),
        _engine_event("BudgetSpent", dollars=0.5, turns=2),
        _engine_event("BudgetSpent", headroom=0.9),  # capacity chatter
        _engine_event("VerdictRendered", cost_usd=100.0),  # not a spend kind
    ):
        await _record(meter, event)

    assert meter.dollars == pytest.approx(0.75)
    assert isinstance(meter, SpendMeteringLedgerInterface)


async def test_the_meter_records_cost_spend_telemetry() -> None:
    project_id = uuid4()
    metrics = TelemetryMetrics()
    meter = SpendMeteringLedger(_RecordingLedger(), metrics=metrics)

    await meter.record(
        project_id=project_id,
        cycle=2,
        job_id=uuid4(),
        engine_id=EngineId.CLAUDELOOP,
        correlation_id=uuid4(),
        event=_engine_event("BudgetSpent", dollars=0.5, turns=1),
    )

    assert metrics.export_metrics(project_id)["cost_spend"] == {"claudeloop": 0.5}


async def test_the_meter_never_counts_an_event_the_ledger_refused() -> None:
    meter = SpendMeteringLedger(_RecordingLedger(fail=True))

    with pytest.raises(RuntimeError, match="append failed"):
        await _record(meter, _engine_event("TurnCompleted", cost_usd=1.0))

    assert meter.dollars == 0.0


async def test_the_meters_spend_rule_is_a_constructor_argument() -> None:
    class FlatRule:
        def spend_of(self, event: object) -> PhaseSpend | None:
            return None  # the meter sees engine events, never ledger events

        def spend_of_payload(self, kind: str, payload: object) -> PhaseSpend | None:
            return PhaseSpend(dollars=1.5)

    meter = SpendMeteringLedger(_RecordingLedger(), spend_rule=FlatRule())

    await _record(meter, _engine_event("SessionSeeded"))

    assert meter.dollars == 1.5


# ── RotationRecordingHandler charges the meter to the engine ─────────────────


class _Meter:
    def __init__(self, dollars: float) -> None:
        self.dollars = dollars
        self.calls: list[EngineEvent] = []

    async def record(self, **kwargs: object) -> None:
        self.calls.append(kwargs["event"])  # type: ignore[arg-type]


class _RaisingInner:
    async def handle(self, job: JobRecord) -> Outcome:
        raise RuntimeError("handler blew up")


async def _metered(
    inner: object, meter: _Meter | None
) -> tuple[RotationRecordingHandler, EngineHealthService, object]:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    handler = RotationRecordingHandler(
        inner=inner,  # type: ignore[arg-type]
        health=health,
        project_id=project_id,  # type: ignore[arg-type]
        engine_id=EngineId.CLAUDELOOP,
        meter=meter,
    )
    return handler, health, project_id


@pytest.mark.parametrize(
    "outcome",
    [
        Success(),
        Failure(FailureClass.WORK, "tests failed"),
        Failure(FailureClass.ENGINE, "exit 137"),
        Defer(NOW + timedelta(minutes=5), "capacity", capacity=True),
        Defer(NOW + timedelta(minutes=5), "repair in flight"),
    ],
    ids=["success", "work-failure", "engine-failure", "capacity-defer", "plain-defer"],
)
async def test_the_jobs_spend_is_charged_to_the_engine_however_it_ends(outcome: Outcome) -> None:
    handler, health, project_id = await _metered(_FixedInner(outcome), _Meter(0.03))

    assert await handler.handle(make_job(uuid4())) == outcome

    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.cost_usd_cycle == pytest.approx(0.03)


async def test_spend_is_charged_even_when_the_handler_raises() -> None:
    """The money was spent whether or not vibey then crashed, and the
    handler's own exception still reaches the worker unchanged."""
    handler, health, project_id = await _metered(_RaisingInner(), _Meter(0.02))

    with pytest.raises(RuntimeError, match="handler blew up"):
        await handler.handle(make_job(uuid4()))

    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.cost_usd_cycle == pytest.approx(0.02)


@pytest.mark.parametrize("dollars", [0.0, -1.0, float("nan"), float("inf")])
async def test_a_meter_with_nothing_chargeable_writes_no_spend(dollars: float) -> None:
    handler, health, project_id = await _metered(_FixedInner(Success()), _Meter(dollars))

    await handler.handle(make_job(uuid4()))

    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.cost_usd_cycle == 0.0
    assert record.circuit == "closed"  # the outcome itself is still recorded


async def test_without_a_meter_no_spend_is_charged() -> None:
    handler, health, project_id = await _metered(_FixedInner(Success()), None)

    await handler.handle(make_job(uuid4()))

    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)  # type: ignore[arg-type]
    assert record.cost_usd_cycle == 0.0


async def test_a_real_implement_run_charges_its_engine_through_the_meter(
    tmp_path: Path,
) -> None:
    """The whole path in one: ScriptedEngine's default run reports $0.01 on
    its TurnCompleted, BuildImplementHandler writes through the meter, and the
    wrapper charges it -- where it used to read $0.00 forever (#209)."""
    from tests.application.test_build_implement_handler import (
        FakeLedger,
        FakeProvisioner,
        FakeWorktrees,
    )
    from tests.application.test_build_implement_handler import _job as _implement_item
    from vibey.application.build_implement_handler import BuildImplementHandler
    from vibey.infrastructure.engines.descriptors import CLAUDELOOP
    from vibey.infrastructure.engines.scripted import ScriptedEngine

    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_healthy_record(project_id, EngineId.CLAUDELOOP))
    health = EngineHealthService(repo)
    ledger = FakeLedger()
    meter = SpendMeteringLedger(ledger)
    handler = RotationRecordingHandler(
        inner=BuildImplementHandler(
            worktrees=FakeWorktrees(tmp_path),
            provisioner=FakeProvisioner(),
            engine=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine"),
            ledger=meter,
            jobs=FakeJobRepository(),
            clock=FixedClock(),
        ),
        health=health,
        project_id=project_id,
        engine_id=EngineId.CLAUDELOOP,
        meter=meter,
    )

    outcome = await handler.handle(_implement_item(project_id=project_id))

    assert isinstance(outcome, Success)
    assert any(event.kind == "TurnCompleted" for event in ledger.recorded)
    record = await health.get_or_create(project_id, EngineId.CLAUDELOOP)
    assert record.cost_usd_cycle == pytest.approx(0.01)
