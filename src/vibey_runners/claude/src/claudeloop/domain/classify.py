# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Pure classification of raw turn signals into a CapacityState.

This is the direct replacement for `extract_limit_signals()` in the legacy script
(legacy/claude_autoresume.py:290-333), except it operates on typed fields the
Agent SDK already parsed, instead of regexing a raw JSON stream. `rate_limit_status
== "allowed_warning"` is deliberately NOT checked as a rejection signal — it falls
through the `rejected` computation below to `Available`, so it can never be
mistaken for a hard limit. Once rejected, credit signals are checked before
falling back to WindowExhausted, so a credits rejection can never be mistaken for
a waitable window even if a stray resets_at rides along with it.

`assistant_error == "billing_error"` (SDK AssistantMessageError) is treated like
credits exhaustion — checked before the Available / window path so a billing
failure cannot be classified as Available or WindowExhausted.

A backend that cannot serve the run as configured is BackendMisconfigured, which
is terminal: a model the backend does not have (Claude Code's
``model_not_found``, on any backend), and on a local backend (``local_backend``)
a 404, a 500 (the model failed to load — typically out of memory), a
conversation Claude Code refuses as longer than the configured window, or a
connection that never got an answer. Each of those used to fall through to
Available and be re-sent turn after turn. A local 503 (Ollama's queue is full)
is the one local error a clock does fix, so it is WindowExhausted with
``rate_limit_type="local"``. Every one of these requires a real error signal —
an ``assistant_error`` or an ``api_error_status`` — never the text alone, so a
turn that merely *talks about* a refused connection stays Available. Golden
payloads for each, captured from the bundled Claude Code CLI against Ollama
0.34.2, are in tests/domain/test_classify.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from claudeloop.domain.capacity import (
    AuthenticationFailed,
    Available,
    BackendMisconfigured,
    CapacityState,
    CreditsExhausted,
    WindowExhausted,
)

_CREDITS_ERROR_CODES = frozenset({"credits_required"})
_CREDITS_DISABLED_REASONS = frozenset({"out_of_credits"})

# Monthly spend / usage-credit limit copy often arrives as a bare rate_limit + 429
# (or only as ResultMessage.result text) with RateLimitEvent dropped — never treat
# that as a waitable window.
#
# Markers must be error-phrasing, not topic mentions: a turn that *documents*
# "monthly spend limit" / "spend limit" / "/usage-credits" must stay Available.
# Bare "you've hit your" also matches session/weekly window copy and must not
# force CreditsExhausted on its own.
_SPEND_LIMIT_ERROR_MARKERS = (
    "hit your monthly",
    "out of extra usage",
    "purchase more credits",
)


# Claude Code's own wording when it never got an HTTP answer at all (observed:
# "API Error: Connection refused — a firewall or proxy may be blocking it
# (ConnectionRefused)"). Matched only alongside an assistant_error and no HTTP
# status, so a model discussing a refused connection is never mistaken for one.
_UNREACHABLE_MARKERS = (
    "connectionrefused",
    "connection refused",
    "econnrefused",
    "unable to connect",
    "enotfound",
    "getaddrinfo",
    "connection error",
)

_CONTEXT_OVERFLOW_MARKER = "prompt is too long"

LOCAL_RATE_LIMIT_TYPE = "local"


def looks_like_spend_limit(text: str | None) -> bool:
    """True when assistant/result copy is a billing spend / usage-credit *error*."""
    if not text:
        return False
    lowered = text.casefold()
    return any(marker in lowered for marker in _SPEND_LIMIT_ERROR_MARKERS)


@dataclass(frozen=True, slots=True)
class TurnSignals:
    """Everything the classifier needs from one turn, gathered from the Agent SDK's
    RateLimitEvent, ResultMessage, and AssistantMessage — deliberately not a single
    source, because RateLimitEvent is reportedly dropped on some adapter paths."""

    rate_limit_status: str | None = None  # "allowed" | "allowed_warning" | "rejected"
    rate_limit_type: str | None = None
    resets_at: datetime | None = None
    utilization: float | None = None
    overage_status: str | None = None
    overage_resets_at: datetime | None = None
    overage_disabled_reason: str | None = None
    api_error_status: int | None = None
    assistant_error: str | None = None
    error_code: str | None = None
    disabled_reason: str | None = None
    can_purchase: bool | None = None
    result_text: str | None = None
    # True when the run talks to a local backend (a profile with base_url). Only
    # then do bare 404 / 500 / 503 statuses and connection failures carry the
    # meanings below; on Anthropic they keep their existing classification.
    local_backend: bool = False


def backend_misconfiguration(signals: TurnSignals) -> BackendMisconfigured | None:
    """The BackendMisconfigured a turn's signals prove, or None.

    A module-level function rather than a method: it is one branch of
    ``classify()`` below, which is itself a module-level pure function called
    throughout the runner, and it is split out only so each rule reads on its own.
    """
    detail = signals.result_text or ""
    if signals.assistant_error == "model_not_found":
        return BackendMisconfigured(reason="model_not_found", detail=detail)
    if not signals.local_backend:
        return None
    if signals.api_error_status == 404:
        return BackendMisconfigured(reason="endpoint_not_found", detail=detail)
    if signals.api_error_status == 500:
        return BackendMisconfigured(reason="model_load_failed", detail=detail)
    # Claude Code's own refusal (no HTTP status) when the conversation does not fit
    # the window it was given — on a local backend that is `context_window` too
    # small for Claude Code's system prompt plus its output reservation, and no
    # later turn fits either. Observed live on qwen2.5-coder:14b with
    # context_window = 32768 and no max_output_tokens.
    if (
        signals.assistant_error == "invalid_request"
        and _CONTEXT_OVERFLOW_MARKER in detail.casefold()
    ):
        return BackendMisconfigured(reason="context_too_small", detail=detail)
    if (
        signals.assistant_error is not None
        and signals.api_error_status is None
        and any(marker in detail.casefold() for marker in _UNREACHABLE_MARKERS)
    ):
        return BackendMisconfigured(reason="unreachable", detail=detail)
    return None


def classify(signals: TurnSignals) -> CapacityState:
    if signals.assistant_error == "authentication_failed":
        return AuthenticationFailed(detail=signals.assistant_error)

    # SDK AssistantMessageError sibling of authentication_failed / rate_limit.
    # Billing failures have no reset clock — never treat as WindowExhausted
    # even when a stray resets_at or 429 rides along.
    if signals.assistant_error == "billing_error":
        return CreditsExhausted(can_purchase=True)

    # Terminal and human-only, like authentication: checked before any rejection
    # so a misconfiguration can never be waited on or retried.
    misconfigured = backend_misconfiguration(signals)
    if misconfigured is not None:
        return misconfigured

    # A local server's queue is full (Ollama OLLAMA_MAX_QUEUE). Waitable: the
    # queue drains on its own. There is no reset instant, so the configured
    # window probe interval decides when to look again.
    if signals.local_backend and signals.api_error_status == 503:
        return WindowExhausted(rate_limit_type=LOCAL_RATE_LIMIT_TYPE, resets_at=None)

    spend_limit = looks_like_spend_limit(signals.result_text)

    rejected = (
        signals.rate_limit_status == "rejected"
        or signals.api_error_status == 429
        or signals.assistant_error == "rate_limit"
        or spend_limit
    )

    if not rejected:
        return Available(utilization=signals.utilization)

    if (
        signals.error_code in _CREDITS_ERROR_CODES
        or signals.disabled_reason in _CREDITS_DISABLED_REASONS
        or signals.overage_disabled_reason is not None
        or spend_limit
    ):
        can_purchase = True if signals.can_purchase is None else signals.can_purchase
        return CreditsExhausted(can_purchase=can_purchase)

    resets_at = signals.resets_at or signals.overage_resets_at
    return WindowExhausted(
        rate_limit_type=signals.rate_limit_type or "unknown",
        resets_at=resets_at,
    )
