# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Final

from vibey.domain.capacity import (
    Available,
    CapacityState,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.interfaces.circuit_interface import EngineFailurePolicyInterface


class CircuitState(StrEnum):
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class DeadlineProbe:
    at: datetime


@dataclass(frozen=True, slots=True)
class BackoffProbe:
    next_at: datetime
    attempt: int


ProbeSchedule = DeadlineProbe | BackoffProbe


@dataclass(frozen=True, slots=True)
class Circuit:
    state: CircuitState
    capacity: CapacityState
    probe: ProbeSchedule | None
    consecutive_failures: int = 0
    ewma_failure: float = 0.0


def _jitter(*, seed: bytes, spread: timedelta = timedelta(seconds=30)) -> timedelta:
    """Deterministic pseudo-jitter derived from the seed bytes, so the same
    inputs always produce the same schedule (rotation.py's determinism
    property depends on functions like this staying pure)."""
    digest = hashlib.sha256(seed).digest()
    fraction = int.from_bytes(digest[:4], "big") / 0xFFFFFFFF
    return timedelta(seconds=spread.total_seconds() * fraction)


def _backoff(
    attempt: int,
    *,
    base: timedelta = timedelta(seconds=2),
    floor: timedelta = timedelta(0),
    cap: timedelta,
) -> timedelta:
    if attempt < 0:
        attempt = 0
    # Cap the exponent itself, not just the result: 2**attempt as a plain int
    # can outgrow timedelta's internal range long before the value is
    # clamped to `cap`, so an unbounded attempt count must never reach the
    # multiplication uncapped.
    capped_attempt = min(attempt, 32)
    multiplier: int = 2**capped_attempt
    delay = base * multiplier
    if delay < floor:
        delay = floor
    if delay > cap:
        delay = cap
    return delay


def schedule_probe(capacity: CapacityState, *, now: datetime, attempt: int) -> ProbeSchedule | None:
    """The type system carries the rule: CreditsExhausted can only ever
    produce a BackoffProbe, never a DeadlineProbe -- because there is no
    deadline."""
    match capacity:
        case Available():
            return None
        case WindowExhausted(resets_at=dt) if dt is not None:
            seed = f"window:{dt.isoformat()}:{attempt}".encode()
            return DeadlineProbe(at=dt + _jitter(seed=seed))
        case WindowExhausted():
            delay = _backoff(attempt, cap=timedelta(minutes=5))
            return BackoffProbe(next_at=now + delay, attempt=attempt)
        case CreditsExhausted():
            delay = _backoff(attempt, floor=timedelta(minutes=5), cap=timedelta(minutes=30))
            return BackoffProbe(next_at=now + delay, attempt=attempt)
        case _:
            return None  # AuthenticationFailed or unknown -- waiting cannot fix credentials


ENGINE_FAILURE_THRESHOLD: Final = 3
"""Consecutive ENGINE-class failures that open an engine's circuit -- the
"opens after 3" that ``domain/job.py``'s ``FailureClass.ENGINE`` has always
promised. The count is the engine health record's ``consecutive_fail``, which
capacity rejections also increment and only a success resets."""

ENGINE_FAILURE_PROBE_BASE: Final = timedelta(minutes=5)
"""The probe delay when the threshold is first reached. The same five minutes
the BUILD handlers' capacity backoff and ``CreditsExhausted``'s probe floor
use, so every way an engine leaves rotation comes back on one timescale."""

ENGINE_FAILURE_PROBE_CAP: Final = timedelta(minutes=30)
"""The longest an engine that keeps failing its probes waits between them --
``CreditsExhausted``'s cap, for the same reason."""


@dataclass(frozen=True, slots=True)
class EngineFailurePolicy:
    """When consecutive ENGINE-class failures open a circuit, and when the
    opened circuit is probed again. See ``EngineFailurePolicyInterface``.

    Opening without a probe time would be a one-way door: an OPEN circuit is
    never selected, only a selected run can succeed and close it, and
    ``EngineSelector._circuit_state`` half-opens a circuit only once
    ``resets_at`` or ``probe_next_at`` has passed. So the policy never answers
    "open" without also answering "until when".

    Every number is a field with a default rather than a literal in the
    service that applies it (ADR-0018).
    """

    threshold: int = ENGINE_FAILURE_THRESHOLD
    probe_base: timedelta = ENGINE_FAILURE_PROBE_BASE
    probe_cap: timedelta = ENGINE_FAILURE_PROBE_CAP

    def __post_init__(self) -> None:
        # bool is an int in Python; `threshold=True` would silently mean 1.
        if isinstance(self.threshold, bool) or self.threshold < 1:
            raise ValueError("an engine-failure threshold is a whole number of at least 1")
        if self.probe_base <= timedelta(0):
            raise ValueError("an engine-failure probe delay must be positive")
        if self.probe_cap < self.probe_base:
            raise ValueError("an engine-failure probe cap cannot be below its base delay")

    def trips(self, consecutive_failures: int) -> bool:
        """True once ``consecutive_failures`` has reached the threshold."""
        return consecutive_failures >= self.threshold

    def probe_at(self, *, now: datetime, consecutive_failures: int) -> datetime:
        """``now`` plus a delay that doubles with each failure past the
        threshold, from ``probe_base`` up to ``probe_cap``."""
        attempt = max(consecutive_failures - self.threshold, 0)
        return now + _backoff(attempt, base=self.probe_base, cap=self.probe_cap)


ENGINE_FAILURE_POLICY: Final[EngineFailurePolicyInterface] = EngineFailurePolicy()
"""The published default policy; annotated so ``mypy --strict`` checks the
class against its seam."""
