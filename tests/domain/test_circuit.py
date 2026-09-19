# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as st

from vibey.domain.capacity import (
    AuthenticationFailed,
    Available,
    CapacityState,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.circuit import (
    ENGINE_FAILURE_POLICY,
    ENGINE_FAILURE_PROBE_BASE,
    ENGINE_FAILURE_PROBE_CAP,
    ENGINE_FAILURE_THRESHOLD,
    BackoffProbe,
    DeadlineProbe,
    EngineFailurePolicy,
    schedule_probe,
)
from vibey.domain.interfaces import EngineFailurePolicyInterface

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_available_schedules_no_probe() -> None:
    assert schedule_probe(Available(), now=NOW, attempt=0) is None


def test_authentication_failed_schedules_no_probe() -> None:
    assert schedule_probe(AuthenticationFailed(), now=NOW, attempt=5) is None


def test_window_exhausted_with_deadline_schedules_a_deadline_probe() -> None:
    resets_at = NOW + timedelta(hours=1)
    probe = schedule_probe(WindowExhausted(resets_at=resets_at), now=NOW, attempt=0)

    assert isinstance(probe, DeadlineProbe)
    assert probe.at >= resets_at


def test_window_exhausted_without_deadline_schedules_a_backoff_probe() -> None:
    probe = schedule_probe(WindowExhausted(), now=NOW, attempt=2)

    assert isinstance(probe, BackoffProbe)
    assert probe.next_at > NOW
    assert probe.next_at - NOW <= timedelta(minutes=5)


def test_credits_exhausted_schedules_a_backoff_probe_with_a_floor_and_cap() -> None:
    probe = schedule_probe(CreditsExhausted(), now=NOW, attempt=0)

    assert isinstance(probe, BackoffProbe)
    assert probe.next_at - NOW >= timedelta(minutes=5)
    assert probe.next_at - NOW <= timedelta(minutes=30)


def test_negative_attempt_is_treated_as_zero() -> None:
    probe = schedule_probe(CreditsExhausted(), now=NOW, attempt=-5)
    assert isinstance(probe, BackoffProbe)
    assert probe.next_at - NOW >= timedelta(minutes=5)


def test_credits_exhausted_backoff_never_exceeds_thirty_minutes() -> None:
    probe = schedule_probe(CreditsExhausted(), now=NOW, attempt=1000)

    assert isinstance(probe, BackoffProbe)
    assert probe.next_at - NOW <= timedelta(minutes=30)


_capacity_states = st.one_of(
    st.builds(Available),
    st.builds(
        WindowExhausted,
        resets_at=st.one_of(st.none(), st.datetimes(timezones=st.just(UTC))),
        rate_limit_type=st.one_of(st.none(), st.text(max_size=10)),
    ),
    st.builds(CreditsExhausted, can_purchase=st.booleans()),
    st.builds(AuthenticationFailed, detail=st.text(max_size=20)),
)


@given(
    capacity=_capacity_states,
    now=st.datetimes(timezones=st.just(UTC)),
    attempt=st.integers(0, 100),
)
def test_credits_never_produce_a_deadline(
    capacity: CapacityState, now: datetime, attempt: int
) -> None:
    probe = schedule_probe(capacity, now=now, attempt=attempt)
    if isinstance(capacity, CreditsExhausted):
        assert not isinstance(probe, DeadlineProbe)


@given(
    capacity=_capacity_states,
    now=st.datetimes(timezones=st.just(UTC)),
    attempt=st.integers(0, 100),
)
def test_schedule_probe_never_raises(capacity: CapacityState, now: datetime, attempt: int) -> None:
    schedule_probe(capacity, now=now, attempt=attempt)


# -- EngineFailurePolicy: when ENGINE-class failures open a circuit ---------------


def test_the_default_policy_opens_after_three_as_failure_class_engine_promises() -> None:
    assert ENGINE_FAILURE_THRESHOLD == 3
    assert ENGINE_FAILURE_POLICY.threshold == ENGINE_FAILURE_THRESHOLD
    assert ENGINE_FAILURE_POLICY.probe_base == ENGINE_FAILURE_PROBE_BASE == timedelta(minutes=5)
    assert ENGINE_FAILURE_POLICY.probe_cap == ENGINE_FAILURE_PROBE_CAP == timedelta(minutes=30)
    assert isinstance(ENGINE_FAILURE_POLICY, EngineFailurePolicyInterface)


@pytest.mark.parametrize(("failures", "trips"), [(0, False), (1, False), (2, False), (3, True)])
def test_the_policy_trips_at_the_threshold_and_not_before(failures: int, trips: bool) -> None:
    assert EngineFailurePolicy().trips(failures) is trips


def test_a_tripped_circuit_is_probed_after_the_base_delay_doubling_to_the_cap() -> None:
    policy = EngineFailurePolicy()

    delays = [
        policy.probe_at(now=NOW, consecutive_failures=failures) - NOW for failures in range(3, 9)
    ]

    assert delays == [
        timedelta(minutes=5),
        timedelta(minutes=10),
        timedelta(minutes=20),
        timedelta(minutes=30),
        timedelta(minutes=30),
        timedelta(minutes=30),
    ]


def test_a_probe_asked_for_below_the_threshold_is_the_base_delay_not_a_shorter_one() -> None:
    assert EngineFailurePolicy().probe_at(now=NOW, consecutive_failures=1) == NOW + timedelta(
        minutes=5
    )


def test_every_number_in_the_policy_is_configurable() -> None:
    policy = EngineFailurePolicy(
        threshold=1, probe_base=timedelta(seconds=10), probe_cap=timedelta(seconds=15)
    )

    assert policy.trips(1)
    assert policy.probe_at(now=NOW, consecutive_failures=1) == NOW + timedelta(seconds=10)
    assert policy.probe_at(now=NOW, consecutive_failures=4) == NOW + timedelta(seconds=15)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"threshold": 0}, "at least 1"),
        ({"threshold": True}, "at least 1"),
        ({"probe_base": timedelta(0)}, "positive"),
        ({"probe_base": timedelta(minutes=10), "probe_cap": timedelta(minutes=5)}, "below"),
    ],
)
def test_a_policy_that_could_never_reopen_sensibly_is_refused(
    kwargs: dict[str, object], match: str
) -> None:
    with pytest.raises(ValueError, match=match):
        EngineFailurePolicy(**kwargs)  # type: ignore[arg-type]


@given(st.integers(min_value=0, max_value=10_000))
def test_a_probe_is_always_in_the_future_and_never_past_the_cap(failures: int) -> None:
    delay = EngineFailurePolicy().probe_at(now=NOW, consecutive_failures=failures) - NOW

    assert ENGINE_FAILURE_PROBE_BASE <= delay <= ENGINE_FAILURE_PROBE_CAP
