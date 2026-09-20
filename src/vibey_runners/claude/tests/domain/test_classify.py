# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime

import pytest

from claudeloop.domain.capacity import (
    AuthenticationFailed,
    Available,
    BackendMisconfigured,
    CreditsExhausted,
    WindowExhausted,
)
from claudeloop.domain.classify import TurnSignals, backend_misconfiguration, classify

NOW = datetime(2026, 8, 9, tzinfo=UTC)


def test_no_signals_is_available():
    assert classify(TurnSignals()) == Available(utilization=None)


def test_allowed_warning_is_not_a_rejection():
    """The exact false positive documented in the legacy script: allowed_warning
    carries a far-future weekly resetsAt but must never trigger a cooldown."""
    signals = TurnSignals(rate_limit_status="allowed_warning", utilization=0.92)
    result = classify(signals)
    assert isinstance(result, Available)
    assert result.utilization == 0.92


def test_rejected_status_with_reset_time_is_window_exhausted():
    signals = TurnSignals(rate_limit_status="rejected", rate_limit_type="five_hour", resets_at=NOW)
    result = classify(signals)
    assert result == WindowExhausted(rate_limit_type="five_hour", resets_at=NOW)


def test_rejected_status_without_reset_time_falls_back_to_unknown():
    signals = TurnSignals(rate_limit_status="rejected")
    result = classify(signals)
    assert result == WindowExhausted(rate_limit_type="unknown", resets_at=None)


def test_api_error_429_alone_is_rejected():
    """RateLimitEvent is reportedly dropped on some adapter paths — classification
    must not depend on it alone."""
    signals = TurnSignals(api_error_status=429)
    result = classify(signals)
    assert isinstance(result, WindowExhausted)


def test_assistant_error_rate_limit_alone_is_rejected():
    signals = TurnSignals(assistant_error="rate_limit")
    result = classify(signals)
    assert isinstance(result, WindowExhausted)


def test_credits_required_error_code_is_credits_exhausted_not_window():
    """The real transcript case: credits_required has no reset time and must never
    be classified as a waitable window."""
    signals = TurnSignals(
        rate_limit_status="rejected", error_code="credits_required", resets_at=None
    )
    result = classify(signals)
    assert result == CreditsExhausted(can_purchase=True)


def test_out_of_credits_disabled_reason_is_credits_exhausted():
    signals = TurnSignals(rate_limit_status="rejected", disabled_reason="out_of_credits")
    assert classify(signals) == CreditsExhausted(can_purchase=True)


def test_overage_disabled_reason_is_credits_exhausted():
    signals = TurnSignals(rate_limit_status="rejected", overage_disabled_reason="disabled")
    assert classify(signals) == CreditsExhausted(can_purchase=True)


def test_credits_exhausted_even_if_a_reset_time_is_present():
    """Credit signals must outrank a stray reset time — waiting can never fix this."""
    signals = TurnSignals(
        rate_limit_status="rejected", error_code="credits_required", resets_at=NOW
    )
    assert isinstance(classify(signals), CreditsExhausted)


def test_authentication_failed_outranks_everything():
    signals = TurnSignals(
        assistant_error="authentication_failed",
        rate_limit_status="rejected",
        error_code="credits_required",
    )
    result = classify(signals)
    assert result == AuthenticationFailed(detail="authentication_failed")


def test_billing_error_alone_is_credits_exhausted():
    """SDK AssistantMessageError includes billing_error as a sibling of
    rate_limit / authentication_failed. Alone it must not fall through to
    Available."""
    signals = TurnSignals(assistant_error="billing_error")
    assert classify(signals) == CreditsExhausted(can_purchase=True)


def test_billing_error_outranks_window_even_with_resets_at():
    """billing_error + 429 / resets_at must never become waitable WindowExhausted."""
    signals = TurnSignals(
        assistant_error="billing_error",
        api_error_status=429,
        rate_limit_status="rejected",
        resets_at=NOW,
    )
    assert isinstance(classify(signals), CreditsExhausted)


def test_overage_resets_at_used_when_primary_resets_at_absent():
    signals = TurnSignals(
        rate_limit_status="rejected", rate_limit_type="overage", overage_resets_at=NOW
    )
    result = classify(signals)
    assert result == WindowExhausted(rate_limit_type="overage", resets_at=NOW)


def test_spend_limit_result_text_with_thin_rate_limit_is_credits_exhausted():
    """f132e38a attempts 7–10: monthly spend-limit copy + rate_limit/429 and no
    overage_* fields must never become WindowExhausted."""
    signals = TurnSignals(
        assistant_error="rate_limit",
        api_error_status=429,
        result_text=(
            "You've hit your monthly spend limit. Run /usage-credits to manage "
            "your limit and keep using Fable 5 or switch models to continue this chat."
        ),
    )
    assert classify(signals) == CreditsExhausted(can_purchase=True)


def test_spend_limit_text_alone_is_credits_exhausted():
    """Spend-limit copy without a structured rejection still outranks Available."""
    signals = TurnSignals(
        result_text="You've hit your monthly spend limit. Run /usage-credits.",
    )
    assert classify(signals) == CreditsExhausted(can_purchase=True)


def test_ordinary_assistant_text_is_not_spend_limit():
    signals = TurnSignals(result_text="Waiting for the E2E suite to finish.")
    assert classify(signals) == Available(utilization=None)


def test_documenting_spend_limit_is_not_credits_exhausted():
    """Topic mentions must not trip CreditsExhausted — capacity outranks Done,
    so a false positive here aborts otherwise-successful autonomous runs."""
    for text in (
        "Documented the monthly spend limit behavior.",
        "We raised the spend limit in config.",
        "Updated the usage-credits page in the docs.",
        "See /usage-credits in the docs.",
    ):
        assert classify(TurnSignals(result_text=text)) == Available(utilization=None)


def test_session_limit_copy_is_not_spend_limit():
    """Broad 'you've hit your' window copy must stay waitable WindowExhausted."""
    signals = TurnSignals(
        assistant_error="rate_limit",
        api_error_status=429,
        rate_limit_type="five_hour",
        resets_at=NOW,
        result_text="You've hit your session limit. It resets at 4pm.",
    )
    result = classify(signals)
    assert result == WindowExhausted(rate_limit_type="five_hour", resets_at=NOW)


def test_weekly_limit_copy_is_not_spend_limit():
    signals = TurnSignals(
        rate_limit_status="rejected",
        rate_limit_type="seven_day",
        resets_at=NOW,
        result_text="You've hit your weekly limit. Come back later.",
    )
    result = classify(signals)
    assert isinstance(result, WindowExhausted)


# --- backend misconfiguration and local backends ---
#
# Golden payloads: each (assistant_error, api_error_status, result text) triple
# below was captured from the Claude Code CLI bundled with claude-agent-sdk
# 0.2.152, driven through ClaudeSDKClient against Ollama 0.34.2 on 127.0.0.1
# (404 and connection-refused) and against a stub server returning Ollama's own
# 500 / 503 error bodies. The SDK's AssistantMessageError literal does not list
# "model_not_found"; the CLI sends it anyway.

_MODEL_NOT_FOUND = (
    "model_not_found",
    404,
    "There's an issue with the selected model (nope-model:1b). It may not exist or you "
    "may not have access to it.",
)
_REFUSED = (
    "server_error",
    None,
    "API Error: Connection refused \u2014 a firewall or proxy may be blocking it "
    "(ConnectionRefused)",
)
_OOM = (
    "server_error",
    500,
    "API Error: 500 model requires more system memory (18.2 GiB) than is available "
    "(7.1 GiB). This is a server-side issue, usually temporary \u2014 try again in a "
    "moment. If it persists, check your inference gateway (127.0.0.1:11998).",
)
_QUEUE_FULL = (
    "server_error",
    503,
    "API Error: 503 server busy, please try again.  maximum pending requests exceeded. "
    "This is a server-side issue, usually temporary \u2014 try again in a moment. If it "
    "persists, check your inference gateway (127.0.0.1:11997).",
)


def _signals(golden: tuple[str, int | None, str], *, local: bool) -> TurnSignals:
    error, status, text = golden
    return TurnSignals(
        assistant_error=error,
        api_error_status=status,
        result_text=text,
        local_backend=local,
    )


@pytest.mark.parametrize("local", [True, False])
def test_model_not_found_is_misconfigured_on_any_backend(local: bool) -> None:
    """Re-sending a turn to a model that does not exist burned the whole turn
    budget before; it needs a human, local or not."""
    result = classify(_signals(_MODEL_NOT_FOUND, local=local))
    assert isinstance(result, BackendMisconfigured)
    assert result.reason == "model_not_found"
    assert "nope-model:1b" in result.detail


def test_local_backend_down_is_misconfigured_not_available() -> None:
    result = classify(_signals(_REFUSED, local=True))
    assert result == BackendMisconfigured(reason="unreachable", detail=_REFUSED[2])


def test_local_model_that_failed_to_load_is_misconfigured() -> None:
    result = classify(_signals(_OOM, local=True))
    assert isinstance(result, BackendMisconfigured)
    assert result.reason == "model_load_failed"
    assert "system memory" in result.detail


def test_local_context_overflow_is_misconfigured() -> None:
    """Captured live: qwen2.5-coder:14b with context_window = 32768 and no
    max_output_tokens — Claude Code refused the very first turn (14,233 input
    tokens) and would have refused every later one."""
    signals = TurnSignals(
        assistant_error="invalid_request", result_text="Prompt is too long", local_backend=True
    )
    assert classify(signals) == BackendMisconfigured(
        reason="context_too_small", detail="Prompt is too long"
    )


def test_context_overflow_on_anthropic_keeps_its_existing_reading() -> None:
    signals = TurnSignals(assistant_error="invalid_request", result_text="Prompt is too long")
    assert classify(signals) == Available(utilization=None)


def test_local_bare_404_is_a_wrong_endpoint() -> None:
    signals = TurnSignals(
        api_error_status=404, result_text="404 page not found", local_backend=True
    )
    assert classify(signals) == BackendMisconfigured(
        reason="endpoint_not_found", detail="404 page not found"
    )


def test_local_queue_full_is_a_waitable_local_window() -> None:
    assert classify(_signals(_QUEUE_FULL, local=True)) == WindowExhausted(
        rate_limit_type="local", resets_at=None
    )


@pytest.mark.parametrize("golden", [_REFUSED, _OOM, _QUEUE_FULL])
def test_anthropic_keeps_its_existing_reading_of_these_errors(
    golden: tuple[str, int | None, str],
) -> None:
    """Only a local backend reads 500 / 503 / a refused connection this way; on
    Anthropic they stay what they were (transient, not a human's problem)."""
    assert classify(_signals(golden, local=False)) == Available(utilization=None)


def test_a_turn_that_merely_mentions_a_refused_connection_is_not_misconfigured() -> None:
    """The unreachable reading needs a real error signal, never text alone: a
    model debugging a network bug writes exactly these words."""
    signals = TurnSignals(
        result_text="Fixed the ECONNREFUSED / Connection refused bug in the client.",
        local_backend=True,
    )
    assert classify(signals) == Available(utilization=None)


def test_an_error_with_an_http_status_is_not_read_as_unreachable() -> None:
    signals = TurnSignals(
        assistant_error="server_error",
        api_error_status=502,
        result_text="API Error: 502 Connection refused upstream",
        local_backend=True,
    )
    assert backend_misconfiguration(signals) is None


def test_an_unrelated_local_error_is_not_misconfigured() -> None:
    signals = TurnSignals(
        assistant_error="invalid_request",
        result_text="API Error: 400 prompt too long",
        local_backend=True,
    )
    assert backend_misconfiguration(signals) is None
    assert classify(signals) == Available(utilization=None)


def test_authentication_failure_still_outranks_misconfiguration() -> None:
    signals = TurnSignals(
        assistant_error="authentication_failed", api_error_status=404, local_backend=True
    )
    assert isinstance(classify(signals), AuthenticationFailed)


def test_billing_still_outranks_misconfiguration() -> None:
    signals = TurnSignals(assistant_error="billing_error", api_error_status=500, local_backend=True)
    assert isinstance(classify(signals), CreditsExhausted)


def test_misconfiguration_outranks_a_local_rate_limit_signal() -> None:
    signals = TurnSignals(
        assistant_error="model_not_found",
        rate_limit_status="rejected",
        api_error_status=404,
        local_backend=True,
    )
    assert classify(signals) == BackendMisconfigured(reason="model_not_found", detail="")
