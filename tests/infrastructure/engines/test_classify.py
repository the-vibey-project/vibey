# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime

import pytest

from vibey.domain.capacity import (
    AuthenticationFailed,
    Available,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.engine import EngineId
from vibey.domain.job import FailureClass
from vibey.infrastructure.engines.classify import (
    AUTH_FIXTURES,
    AVAILABLE_FIXTURES,
    CREDITS_FIXTURES,
    WINDOW_FIXTURES,
    attribute_failure,
    classify_capacity,
)


@pytest.mark.parametrize("engine_id", list(EngineId))
def test_credits_fixture_classifies_as_credits_exhausted(engine_id: EngineId) -> None:
    result = classify_capacity(engine_id, CREDITS_FIXTURES[engine_id])
    assert isinstance(result, CreditsExhausted)


@pytest.mark.parametrize("engine_id", list(EngineId))
def test_window_fixture_classifies_as_window_exhausted(engine_id: EngineId) -> None:
    result = classify_capacity(engine_id, WINDOW_FIXTURES[engine_id])
    assert isinstance(result, WindowExhausted)


@pytest.mark.parametrize("engine_id", list(EngineId))
def test_auth_fixture_classifies_as_authentication_failed(engine_id: EngineId) -> None:
    result = classify_capacity(engine_id, AUTH_FIXTURES[engine_id])
    assert isinstance(result, AuthenticationFailed)


@pytest.mark.parametrize("engine_id", list(EngineId))
def test_available_fixture_classifies_as_available(engine_id: EngineId) -> None:
    result = classify_capacity(engine_id, AVAILABLE_FIXTURES[engine_id])
    assert isinstance(result, Available)


@pytest.mark.parametrize("engine_id", list(EngineId))
def test_credits_never_carries_a_resets_at(engine_id: EngineId) -> None:
    result = classify_capacity(engine_id, CREDITS_FIXTURES[engine_id])
    assert not hasattr(result, "resets_at")


@pytest.mark.parametrize("engine_id", list(EngineId))
def test_credits_and_window_are_never_confused(engine_id: EngineId) -> None:
    credits_result = classify_capacity(engine_id, CREDITS_FIXTURES[engine_id])
    window_result = classify_capacity(engine_id, WINDOW_FIXTURES[engine_id])

    assert not isinstance(credits_result, WindowExhausted)
    assert not isinstance(window_result, CreditsExhausted)


# --- FailureClass attribution fixture corpus --------------------------------

PYTEST_FAILURE_TAIL = """
======= FAILURES =======
______ test_outbox_relay_retries ______
    assert relay.attempts == 3
AssertionError: assert 1 == 3
FAILED tests/test_relay.py::test_outbox_relay_retries - AssertionError
"""

ENGINE_CRASH_TAIL = """
Traceback (most recent call last):
  File "runner.py", line 42, in main
    raise RuntimeError("runner crashed")
RuntimeError: runner crashed
"""

VIBEY_BUG_TAIL = "VibeyInternalError: unexpected None in handoff.produce"


def test_failing_pytest_never_opens_the_circuit() -> None:
    """The single property called out by the milestone: a project test
    failure must classify WORK, never ENGINE, regardless of exit code."""
    result = attribute_failure(1, PYTEST_FAILURE_TAIL)
    assert result is FailureClass.WORK


def test_failing_pytest_is_work_even_with_a_nonstandard_exit_code() -> None:
    result = attribute_failure(2, PYTEST_FAILURE_TAIL)
    assert result is FailureClass.WORK


def test_work_marker_wins_even_alongside_an_incidental_traceback() -> None:
    mixed_tail = ENGINE_CRASH_TAIL + "\n" + PYTEST_FAILURE_TAIL
    assert attribute_failure(1, mixed_tail) is FailureClass.WORK


def test_engine_crash_classifies_as_engine() -> None:
    assert attribute_failure(1, ENGINE_CRASH_TAIL) is FailureClass.ENGINE


def test_timeout_exit_code_classifies_as_engine() -> None:
    assert attribute_failure(124, "process timed out") is FailureClass.ENGINE


def test_sigkill_exit_code_classifies_as_engine() -> None:
    assert attribute_failure(137, "killed") is FailureClass.ENGINE


def test_vibey_internal_error_classifies_as_vibey() -> None:
    assert attribute_failure(1, VIBEY_BUG_TAIL) is FailureClass.VIBEY


def test_clean_exit_classifies_as_work() -> None:
    assert attribute_failure(0, "") is FailureClass.WORK


def test_unrecognized_nonzero_exit_defaults_to_work() -> None:
    assert attribute_failure(1, "something odd happened") is FailureClass.WORK


# --- Partial branch coverage for per-engine classifiers -----------------------


def test_claudeloop_fallback_available_on_unrecognized_state() -> None:
    result = classify_capacity(EngineId.CLAUDELOOP, {"capacity": {"state": "unknown_state"}})
    assert isinstance(result, Available)


def test_codexloop_fallback_available_on_unrecognized_error_code() -> None:
    result = classify_capacity(EngineId.CODEXLOOP, {"error": {"code": "unknown_code"}})
    assert isinstance(result, Available)


def test_cursorloop_window_without_retry_after_seconds() -> None:
    result = classify_capacity(EngineId.CURSORLOOP, {"status": 429, "type": "rate_limited"})
    assert isinstance(result, WindowExhausted)
    assert result.resets_at is None


def test_parse_dt_returns_none_for_non_string() -> None:
    from vibey.infrastructure.engines.classify import _parse_dt

    assert _parse_dt(None) is None
    assert _parse_dt(12345) is None


def test_parse_duration_from_now_returns_none_for_non_string() -> None:
    from vibey.infrastructure.engines.classify import _parse_duration_from_now

    assert _parse_duration_from_now(None) is None
    assert _parse_duration_from_now(30) is None


def test_parse_duration_from_now_returns_none_for_non_matching_pattern() -> None:
    from vibey.infrastructure.engines.classify import _parse_duration_from_now

    assert _parse_duration_from_now("30m") is None
    assert _parse_duration_from_now("abc") is None


def test_opencode_reads_the_official_provider_error_shape() -> None:
    """Official schema: `{"type":"error","error":{"name":"ProviderAuthError",...}}`.

    The wrapper's provider error name alone must classify; the payload's
    message supplies the detail.
    """
    state = classify_capacity(
        EngineId.OPENCODE,
        {
            "type": "error",
            "error": {
                "name": "ProviderAuthError",
                "data": {"providerID": "google", "message": "API key is missing"},
            },
        },
    )
    assert isinstance(state, AuthenticationFailed)
    assert state.detail == "API key is missing"


@pytest.mark.parametrize(
    ("status_code", "expected"),
    [
        (429, WindowExhausted),
        (402, CreditsExhausted),
        (401, AuthenticationFailed),
    ],
)
def test_opencode_reads_official_api_error_statuses(status_code: int, expected: type) -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {
            "error": {
                "name": "APIError",
                "data": {"statusCode": status_code, "message": "provider response"},
            }
        },
    )
    assert isinstance(state, expected)


def test_opencode_unknown_api_error_status_stays_available() -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {"error": {"name": "APIError", "data": {"statusCode": 500}}},
    )
    assert isinstance(state, Available)


def test_opencode_explicit_wrapper_state_wins_over_the_provider_error() -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {
            "capacity_state": "auth_failed",
            "detail": "wrapper already classified this",
            "resets_at": "2026-01-01T00:05:00+00:00",
            "error": {
                "name": "APIError",
                "data": {"statusCode": 429, "message": "rate limited"},
            },
        },
    )
    assert isinstance(state, AuthenticationFailed)
    assert state.detail == "wrapper already classified this"


def test_opencode_falls_back_to_the_wrapper_detail_when_data_carries_no_message() -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {
            "detail": "wrapper detail",
            "error": {"name": "ProviderAuthError", "data": {}},
        },
    )
    assert isinstance(state, AuthenticationFailed)
    assert state.detail == "wrapper detail"


def test_opencode_ignores_unreadable_error_data_without_wrapper_state() -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {
            "resets_at": "2026-01-01T00:05:00+00:00",
            "error": {"name": "APIError", "data": "not-a-mapping"},
        },
    )
    assert isinstance(state, Available)


def test_opencode_reads_a_camel_case_resets_at_inside_the_error_data() -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {
            "error": {
                "name": "APIError",
                "data": {"statusCode": 429, "resetsAt": "2026-01-01T00:05:00+00:00"},
            },
        },
    )
    assert isinstance(state, WindowExhausted)
    assert state.resets_at == datetime(2026, 1, 1, 0, 5, tzinfo=UTC)


def test_opencode_unknown_provider_error_name_stays_available() -> None:
    state = classify_capacity(
        EngineId.OPENCODE,
        {"error": {"name": "SomethingElse", "data": {"message": "boom"}}},
    )
    assert isinstance(state, Available)


# ── claudeloop's real capacity shape, and its backend misconfiguration ───────


@pytest.mark.parametrize("engine_id", [EngineId.CLAUDELOOP, EngineId.CLAUDELOOP_LOCAL])
@pytest.mark.parametrize(
    "name, expected",
    [
        ("CreditsExhausted", CreditsExhausted),
        ("WindowExhausted", WindowExhausted),
        ("AuthenticationFailed", AuthenticationFailed),
        ("BackendMisconfigured", AuthenticationFailed),
        ("Available", Available),
    ],
)
def test_claudeloop_capacity_is_read_as_the_class_name_it_really_writes(
    engine_id: EngineId, name: str, expected: type
) -> None:
    """claudeloop's runner writes `"capacity": "CreditsExhausted"` -- the class name --
    on `turn.completed`. The classifier only understood a mapping with a `state`, so
    every real payload read as Available, credits exhaustion included."""
    assert isinstance(classify_capacity(engine_id, {"capacity": name}), expected)


def test_a_capacity_name_claudeloop_never_wrote_is_available() -> None:
    assert isinstance(classify_capacity(EngineId.CLAUDELOOP, {"capacity": "Mystery"}), Available)


def test_a_credits_class_name_still_never_carries_a_resets_at() -> None:
    state = classify_capacity(EngineId.CLAUDELOOP_LOCAL, {"capacity": "CreditsExhausted"})
    assert isinstance(state, CreditsExhausted)
    assert not hasattr(state, "resets_at")


def test_a_misconfigured_backend_is_terminal_and_names_its_reason() -> None:
    """Waiting fixes nothing here, so never WindowExhausted; and it is not a credits
    event, so never CreditsExhausted. The same terminal state qwenloop's
    `configuration_error` maps to."""
    state = classify_capacity(
        EngineId.CLAUDELOOP_LOCAL,
        {
            "capacity": {
                "state": "backend_misconfigured",
                "reason": "unreachable",
                "detail": "Connection refused",
            }
        },
    )

    assert state == AuthenticationFailed(
        detail="backend misconfigured: unreachable: Connection refused"
    )


def test_a_misconfigured_backend_without_detail_still_says_what_it_is() -> None:
    state = classify_capacity(
        EngineId.CLAUDELOOP, {"capacity": {"state": "backend_misconfigured", "reason": None}}
    )

    assert state == AuthenticationFailed(detail="backend misconfigured")


def test_exit_78_is_the_engines_configuration_not_the_work() -> None:
    assert attribute_failure(78, "backend misconfigured (unreachable)") is FailureClass.ENGINE


def test_a_failing_test_suite_still_wins_over_exit_78() -> None:
    assert attribute_failure(78, "FAILED tests/test_x.py::test_y") is FailureClass.WORK
