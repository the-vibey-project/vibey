# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from __future__ import annotations

from datetime import timezone

from claudeloop.domain.capacity import WindowExhausted
from claudeloop.domain.waiting import next_probe_instant
from claudeloop.infrastructure.agent.translate import (
    COMPLETION_OUTPUT_SCHEMA,
    TurnAccumulator,
    _to_datetime,
)
from claudeloop.infrastructure.clock import SystemClock
from claudeloop.infrastructure.redact import REDACTED_VALUE, redact


def test_to_datetime_none_stays_none() -> None:
    assert _to_datetime(None) is None


def test_to_datetime_seconds_form_10_digits_is_utc_aware() -> None:
    result = _to_datetime(1786328953)
    assert result is not None
    assert 2020 <= result.year <= 2030
    assert result.tzinfo == timezone.utc


def test_to_datetime_milliseconds_form_13_digits() -> None:
    result = _to_datetime(1786328953799)
    assert result is not None
    assert 2020 <= result.year <= 2030
    assert result.tzinfo == timezone.utc


def test_to_datetime_resets_at_comparable_to_system_clock() -> None:
    """Regression: naive local fromtimestamp vs aware SystemClock.now() crashed
    next_probe_instant with TypeError on every live rate-limit wait."""
    resets_at = _to_datetime(1786328953)
    assert resets_at is not None
    now = SystemClock().now()
    at = next_probe_instant(
        WindowExhausted(rate_limit_type="five_hour", resets_at=resets_at),
        now=now,
        started_waiting_at=now,
        probe_count=0,
    )
    assert at.tzinfo is not None


def test_accumulator_empty_build_is_available_with_no_verdict() -> None:
    accumulator = TurnAccumulator()
    outcome = accumulator.build()
    assert outcome.verdict is None
    assert outcome.output_text == ""
    assert outcome.session_id is None
    assert outcome.cost_usd == 0.0
    assert outcome.raw_events == ()


def test_accumulator_feed_records_raw_events_for_unrecognized_types() -> None:
    accumulator = TurnAccumulator()
    accumulator.feed(object())
    outcome = accumulator.build()
    assert outcome.output_text == ""
    assert len(outcome.raw_events) == 1
    assert outcome.raw_events[0]["type"] == "object"


def test_accumulator_scans_error_details_for_credits() -> None:
    class _FakeResult:
        session_id = "s1"
        api_error_status = 429
        total_cost_usd = 0.0
        result = None
        structured_output = None
        errors = []
        errorDetails = {"error_code": "credits_required", "can_user_purchase_credits": False}

    # ResultMessage isinstance check will fail — feed via _scan path by
    # monkeypatching isn't needed if we call the private scanner.
    acc = TurnAccumulator()
    acc._scan_credit_blob({"error_code": "credits_required", "can_user_purchase_credits": False})
    assert acc._error_code == "credits_required"
    assert acc._can_purchase is False


def test_redact_nested_secrets() -> None:
    payload = {
        "api_key": "sk-secret",
        "nested": {"authorization": "Bearer abc", "ok": "fine"},
        "text": "token sk-ant-abcdefghijklmnopqrstuvwxyz012345",
    }
    scrubbed = redact(payload)
    assert scrubbed["api_key"] == REDACTED_VALUE
    assert scrubbed["nested"]["authorization"] == REDACTED_VALUE
    assert scrubbed["nested"]["ok"] == "fine"
    assert REDACTED_VALUE in scrubbed["text"]


def test_completion_schema_describes_blocked_on_as_terminal_external_only() -> None:
    """Models misuse blocked_on for waitable self-started work; schema text must
    steer them toward remaining_work instead (stops the run as Blocked)."""
    props = COMPLETION_OUTPUT_SCHEMA["properties"]
    assert isinstance(props, dict)
    blocked = props["blocked_on"]
    assert isinstance(blocked, dict)
    description = str(blocked["description"]).lower()
    assert "null" in description
    assert "remaining_work" in description
    assert "background" in description or "waitable" in description
    assert "credential" in description or "human" in description

    remaining = props["remaining_work"]
    assert isinstance(remaining, dict)
    rem_desc = str(remaining["description"]).lower()
    assert "background" in rem_desc or "waitable" in rem_desc


# --- cost modes and token counts ---


def _result_message(**fields: object) -> object:
    from claude_agent_sdk import ResultMessage

    base: dict[str, object] = {
        "subtype": "success",
        "duration_ms": 1,
        "duration_api_ms": 1,
        "is_error": False,
        "num_turns": 1,
        "session_id": "s",
        "total_cost_usd": 0.0008365,
        "usage": {"input_tokens": 157, "output_tokens": 2},
        "result": "OK",
    }
    base.update(fields)
    return ResultMessage(**base)  # type: ignore[arg-type]


def test_reported_cost_mode_keeps_claude_codes_figure_and_the_tokens() -> None:
    acc = TurnAccumulator()
    acc.feed(_result_message())
    outcome = acc.build()
    assert outcome.cost_usd == 0.0008365
    assert (outcome.input_tokens, outcome.output_tokens) == (157, 2)
    assert outcome.signals.local_backend is False
    event = outcome.raw_events[0]
    assert event["total_cost_usd"] == 0.0008365
    assert event["usage"] == {"input_tokens": 157, "output_tokens": 2}
    assert "reported_cost_usd" not in event


def test_zero_cost_mode_records_nothing_spent_but_keeps_the_guess_on_record() -> None:
    """Captured live: Claude Code reported $0.0008365 for one turn of a free
    local qwen2.5-coder:1.5b, priced as if it were its default model."""
    acc = TurnAccumulator(cost_mode="zero", local_backend=True)
    acc.feed(_result_message())
    outcome = acc.build()
    assert outcome.cost_usd == 0.0
    assert outcome.output_tokens == 2
    assert outcome.signals.local_backend is True
    event = outcome.raw_events[0]
    assert event["total_cost_usd"] == 0.0
    assert event["reported_cost_usd"] == 0.0008365


def test_zero_cost_mode_with_no_reported_cost() -> None:
    acc = TurnAccumulator(cost_mode="zero")
    acc.feed(_result_message(total_cost_usd=None))
    outcome = acc.build()
    assert outcome.cost_usd == 0.0
    assert outcome.raw_events[0]["reported_cost_usd"] is None


def test_malformed_usage_leaves_the_counts_alone() -> None:
    acc = TurnAccumulator()
    acc.feed(_result_message(usage={"input_tokens": True, "output_tokens": "7"}))
    acc.feed(_result_message(usage=None))
    outcome = acc.build()
    assert (outcome.input_tokens, outcome.output_tokens) == (0, 0)
