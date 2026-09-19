# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Tests for application/engine_health_service.py — the business logic
wrapper around EngineHealthRepository."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from vibey.application.dto import EngineHealthRecord, PreflightResult
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.interfaces.engines import EngineHealthServiceInterface
from vibey.domain.capacity import (
    AuthenticationFailed,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.circuit import EngineFailurePolicy
from vibey.domain.engine import EngineId


class FakeEngineHealthRepository:
    def __init__(self) -> None:
        self._records: dict[tuple[object, str], EngineHealthRecord] = {}

    async def get(self, project_id: object, engine_id: str) -> EngineHealthRecord | None:
        return self._records.get((project_id, engine_id))

    async def upsert(self, record: EngineHealthRecord) -> EngineHealthRecord:
        self._records[(record.project_id, record.engine_id.value)] = record
        return record

    async def list_for_project(self, project_id: object) -> tuple[EngineHealthRecord, ...]:
        return tuple(r for (pid, _), r in self._records.items() if pid == project_id)


def _make_record(
    project_id: object | None = None,
    engine_id: EngineId = EngineId.CLAUDELOOP,
    **overrides: object,
) -> EngineHealthRecord:
    defaults: dict[str, object] = {
        "project_id": project_id or uuid4(),
        "engine_id": engine_id,
        "installed": True,
        "version": "1.0.0",
        "conformance_ok": True,
        "conformance_at": datetime.now(UTC),
        "auth_ok_at": datetime.now(UTC),
        "circuit": "closed",
        "capacity_state": None,
        "resets_at": None,
        "probe_next_at": None,
        "probe_attempt": 0,
        "consecutive_fail": 0,
        "ewma_failure": 0.0,
        "cost_usd_cycle": 0.0,
        "selected_count": 0,
    }
    defaults.update(overrides)
    return EngineHealthRecord(**defaults)  # type: ignore[arg-type]


# --- get_or_create ---


async def test_get_or_create_returns_existing_record() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    existing = _make_record(project_id=project_id, version="2.0.0")
    await repo.upsert(existing)

    svc = EngineHealthService(repo)
    result = await svc.get_or_create(project_id, EngineId.CLAUDELOOP)

    assert result.version == "2.0.0"


async def test_get_or_create_returns_defaults_when_missing() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)

    result = await svc.get_or_create(uuid4(), EngineId.CLAUDELOOP)

    assert result.installed is False
    assert result.circuit == "closed"
    assert result.ewma_failure == 0.0


# --- update_from_preflight ---


async def test_update_from_preflight_sets_installed_and_version() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    result = await svc.update_from_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="3.5.0", auth_ok=True),
        conformance_ok=True,
    )

    assert result.installed is True
    assert result.version == "3.5.0"
    assert result.conformance_ok is True
    assert result.auth_ok_at is not None


async def test_update_from_preflight_auth_not_ok_clears_auth_ok_at() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    result = await svc.update_from_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=False),
        conformance_ok=False,
    )

    assert result.auth_ok_at is None


async def test_update_from_preflight_conformance_fail_preserves_old_conformance_at() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    old_time = datetime(2026, 1, 1, tzinfo=UTC)
    existing = _make_record(project_id=project_id, conformance_at=old_time)
    await repo.upsert(existing)

    svc = EngineHealthService(repo)
    result = await svc.update_from_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
        conformance_ok=False,
    )

    assert result.conformance_ok is False
    assert result.conformance_at == old_time


# --- record_capacity_rejection ---


async def test_record_capacity_rejection_credits_exhausted() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    result = await svc.record_capacity_rejection(
        project_id, EngineId.CLAUDELOOP, CreditsExhausted()
    )

    assert result.circuit == "open"
    assert result.capacity_state == "CreditsExhausted"
    assert result.resets_at is None
    assert result.probe_next_at is not None
    assert result.consecutive_fail == 1
    assert result.ewma_failure > 0.0


async def test_record_capacity_rejection_window_exhausted() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()
    resets = datetime.now(UTC) + timedelta(hours=1)

    result = await svc.record_capacity_rejection(
        project_id, EngineId.CLAUDELOOP, WindowExhausted(resets_at=resets)
    )

    assert result.circuit == "open"
    assert result.capacity_state == "WindowExhausted"
    assert result.resets_at == resets
    assert result.probe_next_at == resets


async def test_record_capacity_rejection_authentication_failed() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    result = await svc.record_capacity_rejection(
        project_id, EngineId.CLAUDELOOP, AuthenticationFailed(detail="bad token")
    )

    assert result.circuit == "open"
    assert result.capacity_state == "AuthenticationFailed"
    assert result.probe_next_at is None


async def test_capacity_rejection_with_available_is_noop() -> None:
    from vibey.domain.capacity import Available

    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    result = await svc.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, Available())

    assert result.circuit == "closed"
    assert result.capacity_state is None


async def test_capacity_rejection_exponential_backoff_for_credits() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    r1 = await svc.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, CreditsExhausted())
    r2 = await svc.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, CreditsExhausted())

    assert r2.probe_attempt == 2
    assert r2.consecutive_fail == 2
    assert r2.probe_next_at is not None
    assert r1.probe_next_at is not None
    # Second probe should be further out (exponential backoff)


async def test_ewma_failure_increases_on_rejection() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    r1 = await svc.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, CreditsExhausted())
    r2 = await svc.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, CreditsExhausted())

    assert r2.ewma_failure > r1.ewma_failure


# --- record_selection ---


async def test_record_selection_counts_selections_and_leaves_spend_alone() -> None:
    """A selection has cost nothing yet. Its old `cost_usd` parameter was
    never passed by its one caller, which is why every engine read $0.00
    (#209); spend now arrives through `record_spend` once the run is over."""
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()
    await repo.upsert(_make_record(project_id=project_id, cost_usd_cycle=1.25))

    r1 = await svc.record_selection(project_id, EngineId.CLAUDELOOP)
    r2 = await svc.record_selection(project_id, EngineId.CLAUDELOOP)

    assert (r1.selected_count, r2.selected_count) == (1, 2)
    assert r2.cost_usd_cycle == pytest.approx(1.25)


# --- record_spend ---


async def test_record_spend_accumulates_and_touches_nothing_else() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()
    before = await repo.upsert(
        _make_record(project_id=project_id, consecutive_fail=2, selected_count=3)
    )

    await svc.record_spend(project_id, EngineId.CLAUDELOOP, 0.50)
    after = await svc.record_spend(project_id, EngineId.CLAUDELOOP, 0.25)

    assert after.cost_usd_cycle == pytest.approx(0.75)
    assert replace(after, cost_usd_cycle=0.0) == before


async def test_record_spend_creates_the_record_it_charges() -> None:
    svc = EngineHealthService(FakeEngineHealthRepository())

    result = await svc.record_spend(uuid4(), EngineId.CODEXLOOP, 0.01)

    assert result.cost_usd_cycle == pytest.approx(0.01)


@pytest.mark.parametrize("amount", [-0.01, float("nan"), float("inf")])
async def test_record_spend_refuses_an_amount_that_is_not_money(amount: float) -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)

    with pytest.raises(ValueError, match="finite amount"):
        await svc.record_spend(uuid4(), EngineId.CLAUDELOOP, amount)
    assert await repo.list_for_project(uuid4()) == ()


# --- record_failure ---

T0 = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


class _Clock:
    def __init__(self, now: datetime) -> None:
        self._now = now

    def now(self) -> datetime:
        return self._now


async def test_an_engine_failure_below_the_threshold_only_moves_the_counters() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    before = await repo.upsert(_make_record(project_id=project_id))
    svc = EngineHealthService(repo, clock=_Clock(T0))

    first = await svc.record_failure(project_id, EngineId.CLAUDELOOP)
    second = await svc.record_failure(project_id, EngineId.CLAUDELOOP)

    assert (first.consecutive_fail, second.consecutive_fail) == (1, 2)
    assert first.ewma_failure == pytest.approx(0.1)
    assert second.ewma_failure == pytest.approx(0.19)
    assert replace(second, consecutive_fail=0, ewma_failure=0.0) == before
    assert second.circuit == "closed"
    assert second.probe_next_at is None


async def test_the_third_engine_failure_opens_the_circuit_and_schedules_its_probe() -> None:
    """Opening alone would be a one-way door: the selector never picks an
    OPEN engine and half-opens one only once a scheduled time passes."""
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_make_record(project_id=project_id, consecutive_fail=2, probe_attempt=1))
    svc = EngineHealthService(repo, clock=_Clock(T0))

    result = await svc.record_failure(project_id, EngineId.CLAUDELOOP)

    assert result.circuit == "open"
    assert result.consecutive_fail == 3
    assert result.probe_next_at == T0 + timedelta(minutes=5)
    assert result.probe_attempt == 2
    assert result.capacity_state is None
    assert result.resets_at is None


async def test_a_trip_clears_a_stale_capacity_window_that_would_half_open_it_at_once() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(
        _make_record(
            project_id=project_id,
            circuit="open",
            capacity_state="WindowExhausted",
            resets_at=T0 - timedelta(hours=1),
            probe_next_at=T0 - timedelta(hours=1),
            consecutive_fail=2,
        )
    )
    svc = EngineHealthService(repo, clock=_Clock(T0))

    result = await svc.record_failure(project_id, EngineId.CLAUDELOOP)

    assert result.circuit == "open"
    assert (result.capacity_state, result.resets_at) == (None, None)
    assert result.probe_next_at == T0 + timedelta(minutes=5)


async def test_each_failure_past_the_threshold_backs_the_probe_off_further() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_make_record(project_id=project_id, consecutive_fail=3, circuit="open"))
    svc = EngineHealthService(repo, clock=_Clock(T0))

    result = await svc.record_failure(project_id, EngineId.CLAUDELOOP)

    assert result.consecutive_fail == 4
    assert result.probe_next_at == T0 + timedelta(minutes=10)


async def test_the_failure_policy_is_a_constructor_argument() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    svc = EngineHealthService(
        repo,
        failure_policy=EngineFailurePolicy(threshold=1, probe_base=timedelta(seconds=30)),
        clock=_Clock(T0),
    )

    result = await svc.record_failure(project_id, EngineId.CLAUDELOOP)

    assert result.circuit == "open"
    assert result.probe_next_at == T0 + timedelta(seconds=30)


async def test_without_a_clock_the_probe_is_dated_by_the_system_clock() -> None:
    svc = EngineHealthService(
        FakeEngineHealthRepository(), failure_policy=EngineFailurePolicy(threshold=1)
    )
    before = datetime.now(UTC)

    result = await svc.record_failure(uuid4(), EngineId.CLAUDELOOP)

    assert result.probe_next_at is not None
    assert before + timedelta(minutes=5) <= result.probe_next_at
    assert result.probe_next_at <= datetime.now(UTC) + timedelta(minutes=5)


async def test_an_engine_opened_by_failures_half_opens_once_its_probe_time_passes() -> None:
    """End to end through the real selector: three ENGINE failures take the
    engine out of rotation, and once `probe_next_at` is behind the selector's
    clock it is selectable again as a half-open probe -- never out for good."""
    from tests.application.test_engine_selector import FakeRotationCursorRepository
    from vibey.application.engine_selector import EngineSelector
    from vibey.domain.effort import Effort
    from vibey.domain.engine import JobRequirement
    from vibey.domain.errors import NoEligibleEngine
    from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID

    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_make_record(project_id=project_id))
    requirement = JobRequirement(effort=Effort.STANDARD)

    # Failures recorded "now": the probe is five minutes ahead of the
    # selector, which reads the real clock, so the engine is out.
    fresh = EngineHealthService(repo, clock=_Clock(datetime.now(UTC)))
    for _ in range(3):
        opened = await fresh.record_failure(project_id, EngineId.CLAUDELOOP)
    assert opened.circuit == "open"
    selector = EngineSelector(fresh, FakeRotationCursorRepository(), BY_ENGINE_ID)
    with pytest.raises(NoEligibleEngine):
        await selector.select_engine(project_id, requirement)

    # The same trip recorded an hour ago: its probe time has passed.
    await repo.upsert(_make_record(project_id=project_id, consecutive_fail=2))
    stale = EngineHealthService(repo, clock=_Clock(datetime.now(UTC) - timedelta(hours=1)))
    reopened = await stale.record_failure(project_id, EngineId.CLAUDELOOP)
    assert reopened.circuit == "open"

    engine_id, selection = await EngineSelector(
        stale, FakeRotationCursorRepository(), BY_ENGINE_ID
    ).select_engine(project_id, requirement)

    assert engine_id is EngineId.CLAUDELOOP
    # Half-open is selectable at reduced weight: that is the probe.
    (candidate,) = selection.candidates
    assert candidate.health_factor == pytest.approx(0.25)


# --- record_success ---


async def test_record_success_resets_circuit_and_failures() -> None:
    repo = FakeEngineHealthRepository()
    svc = EngineHealthService(repo)
    project_id = uuid4()

    # Set up a failing state first
    await svc.record_capacity_rejection(project_id, EngineId.CLAUDELOOP, CreditsExhausted())

    result = await svc.record_success(project_id, EngineId.CLAUDELOOP)

    assert result.circuit == "closed"
    assert result.capacity_state is None
    assert result.consecutive_fail == 0
    assert result.probe_attempt == 0
    assert result.ewma_failure < 0.1  # decayed


async def test_record_success_decays_ewma() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    existing = _make_record(project_id=project_id, ewma_failure=0.5)
    await repo.upsert(existing)

    svc = EngineHealthService(repo)
    result = await svc.record_success(project_id, EngineId.CLAUDELOOP)

    assert result.ewma_failure == pytest.approx(0.45)


# --- list_for_project ---


async def test_list_for_project_returns_all_records() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()

    await repo.upsert(_make_record(project_id=project_id, engine_id=EngineId.CLAUDELOOP))
    await repo.upsert(_make_record(project_id=project_id, engine_id=EngineId.CODEXLOOP))

    svc = EngineHealthService(repo)
    records = await svc.list_for_project(project_id)

    assert len(records) == 2


async def test_record_preflight_refreshes_auth_but_preserves_conformance() -> None:
    """The worker's startup sweep must never grant or revoke conformance --
    that verdict belongs to `vibey doctor --conformance --record` alone."""
    from vibey.application.dto import PreflightResult

    repo = FakeEngineHealthRepository()
    service = EngineHealthService(repo)
    project_id = uuid4()
    granted = await service.update_from_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
        conformance_ok=True,
    )
    assert granted.conformance_ok is True

    refreshed = await service.record_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.1.0", auth_ok=True),
    )

    assert refreshed.version == "1.1.0"
    assert refreshed.conformance_ok is True
    assert refreshed.conformance_at == granted.conformance_at
    assert refreshed.auth_ok_at is not None


async def test_record_preflight_keeps_prior_auth_timestamp_on_auth_failure() -> None:
    from vibey.application.dto import PreflightResult

    repo = FakeEngineHealthRepository()
    service = EngineHealthService(repo)
    project_id = uuid4()
    first = await service.record_preflight(
        project_id,
        EngineId.AGYLOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
    )
    assert first.auth_ok_at is not None

    second = await service.record_preflight(
        project_id,
        EngineId.AGYLOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=False),
    )

    assert second.auth_ok_at == first.auth_ok_at
    assert second.conformance_ok is False


# --- authentication recovery: the preflight is the probe ---


async def test_a_passing_preflight_half_opens_an_authentication_opened_circuit() -> None:
    """AuthenticationFailed schedules no probe on purpose -- waiting cannot
    fix a credential. The human's re-authentication is the trigger instead,
    and a preflight that sees it puts the engine back in rotation without
    anyone editing engine_health by hand."""
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(
        _make_record(
            project_id=project_id,
            circuit="open",
            capacity_state="AuthenticationFailed",
        )
    )

    svc = EngineHealthService(repo)
    result = await svc.record_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
    )

    assert result.circuit == "half_open"


async def test_a_failing_preflight_reopens_a_half_opened_circuit() -> None:
    """Half-open is a probation, not a pardon, and the probe reads both ways.

    The re-open condition fires on `half_open` for the same reason the
    half-open one fires on `open`: a credential that stops working again has
    to put the engine back out of rotation. Matching only `circuit == "open"`
    would leave a second failed preflight matching nothing, so
    `record_preflight` would preserve `half_open` -- and the old `auth_ok_at`
    with it -- and the selector would keep choosing a credential-invalid
    engine for the rest of the auth TTL. That is the window this circuit
    exists to close.
    """
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(
        _make_record(
            project_id=project_id,
            circuit="half_open",
            capacity_state="AuthenticationFailed",
        )
    )

    svc = EngineHealthService(repo)
    result = await svc.record_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=False),
    )

    assert result.circuit == "open"


async def test_doctor_also_half_opens_an_authentication_opened_circuit() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(
        _make_record(
            project_id=project_id,
            circuit="open",
            capacity_state="AuthenticationFailed",
        )
    )

    svc = EngineHealthService(repo)
    result = await svc.update_from_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
        conformance_ok=True,
    )

    assert result.circuit == "half_open"


async def test_a_failing_preflight_leaves_an_authentication_opened_circuit_open() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(
        _make_record(
            project_id=project_id,
            circuit="open",
            capacity_state="AuthenticationFailed",
        )
    )

    svc = EngineHealthService(repo)
    result = await svc.record_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=False),
    )

    assert result.circuit == "open"


async def test_a_credits_opened_circuit_is_not_reopened_by_working_credentials() -> None:
    """Working credentials say nothing about a credits balance or a rate
    limit window; only those states' own probe times may half-open them."""
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(
        _make_record(
            project_id=project_id,
            circuit="open",
            capacity_state="CreditsExhausted",
            probe_next_at=datetime.now(UTC) + timedelta(minutes=10),
        )
    )

    svc = EngineHealthService(repo)
    result = await svc.record_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
    )

    assert result.circuit == "open"


async def test_a_closed_circuit_is_untouched_by_a_passing_preflight() -> None:
    repo = FakeEngineHealthRepository()
    project_id = uuid4()
    await repo.upsert(_make_record(project_id=project_id, circuit="closed"))

    svc = EngineHealthService(repo)
    result = await svc.record_preflight(
        project_id,
        EngineId.CLAUDELOOP,
        PreflightResult(installed=True, version="1.0.0", auth_ok=True),
    )

    assert result.circuit == "closed"


def test_the_service_satisfies_the_seam_the_selector_takes() -> None:
    """ADR-0016: the class has a declared interface, and it is the real one.

    `EngineSelector.__init__` is typed against `EngineHealthServiceInterface`,
    so if the service ever drops a method off that contract the selector's
    dependency stops being substitutable. mypy --strict catches the signature
    drift; this catches the shape at runtime, which is what a test double has
    to satisfy.
    """
    service = EngineHealthService(FakeEngineHealthRepository())
    assert isinstance(service, EngineHealthServiceInterface)
