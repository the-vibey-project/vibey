# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Capacity state — whether the account can currently spend a real turn, and why not
if it can't. This is the typed replacement for regex-scraping stream-json for limit
language."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from claudeloop.domain.backend import BACKEND_MISCONFIGURED_PREFIX


@dataclass(frozen=True, slots=True)
class Available:
    """Capacity exists; a real turn may be spent. `utilization` is informational —
    it reflects an `allowed_warning` signal and must never itself block a turn."""

    utilization: float | None = None


@dataclass(frozen=True, slots=True)
class WindowExhausted:
    """A rate-limit window (five_hour / seven_day / seven_day_opus / seven_day_sonnet /
    overage) has been rejected. `resets_at` is the trusted reset instant when known;
    when None, the caller must fall back to a configured wait interval rather than
    assuming any particular reset time."""

    rate_limit_type: str
    resets_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class CreditsExhausted:
    """No token/time budget will fix this — the account is out of usage credits and
    requires a human to purchase more. There is no reset time by construction: waiting
    for a clock to advance can never resolve this state, only a probe that notices a
    top-up can."""

    can_purchase: bool = True


@dataclass(frozen=True, slots=True)
class AuthenticationFailed:
    """Terminal — credentials are invalid or revoked. Never retryable."""

    detail: str = ""


@dataclass(frozen=True, slots=True)
class BackendMisconfigured:
    """Terminal — the backend, as configured, cannot serve this run, and neither
    waiting nor retrying will change that: it needs a human. Raised for a model
    the backend does not have (any backend), and on a local backend for one that
    is not answering at all, or one that failed to load the model (typically out
    of memory). ``reason`` is a short machine token; ``detail`` is the backend's
    own words."""

    reason: str
    detail: str = ""

    def describe(self) -> str:
        """The run's failure reason. Always starts with BACKEND_MISCONFIGURED_PREFIX
        (domain/backend.py) so the CLI can map it to its own exit status."""
        text = f"{BACKEND_MISCONFIGURED_PREFIX} ({self.reason})"
        detail = " ".join(self.detail.split())
        return f"{text}: {detail}" if detail else text


CapacityState = (
    Available | WindowExhausted | CreditsExhausted | AuthenticationFailed | BackendMisconfigured
)


def is_waitable(state: CapacityState) -> bool:
    """Whether the run loop should ever schedule a wait/probe cycle for this state.
    AuthenticationFailed and BackendMisconfigured must abort outright: neither
    credentials nor a missing model are fixed by a clock."""
    return not isinstance(state, (AuthenticationFailed, BackendMisconfigured))
