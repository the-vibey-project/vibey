# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import ClassVar, Final

from vibey.domain.capacity import (
    Available,
    CapacityState,
    CreditsExhausted,
    WindowExhausted,
)
from vibey.domain.interfaces.circuit_interface import EngineFailurePolicyInterface
from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.stored_value import StoredValueParser, UnrecognizedValue


class CircuitState(StrEnum):
    CLOSED = "closed"
    HALF_OPEN = "half_open"
    OPEN = "open"


@dataclass(frozen=True, slots=True)
class UnrecognizedCircuitState(UnrecognizedValue):
    """A stored circuit state this vibey has no `CircuitState` member for
    (vibey#287). `circuit_state` is a Postgres enum a newer vibey widens with a
    migration. An older selector cannot tell whether such a circuit admits a run,
    so it does not select the engine; it never crashes on the row."""

    members: ClassVar[frozenset[str]] = frozenset(state.value for state in CircuitState)


type StoredCircuitState = CircuitState | UnrecognizedCircuitState


CIRCUIT_STATE_PARSER: Final[StoredValueParserInterface[CircuitState, UnrecognizedCircuitState]] = (
    StoredValueParser(CircuitState, UnrecognizedCircuitState)
)
"""The parser every reader of `engine_health.circuit` shares. Stateless."""


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
"""Consecutive ENGINE-class failures that open an engine's circuit."""

ENGINE_FAILURE_PROBE_BASE: Final = timedelta(minutes=5)
"""Probe delay when the failure threshold is first reached."""

ENGINE_FAILURE_PROBE_CAP: Final = timedelta(minutes=30)
"""Maximum delay between probes of an engine that keeps failing."""


@dataclass(frozen=True, slots=True)
class EngineFailurePolicy:
    """When ENGINE-class failures open a circuit and when it is probed again.

    Declared by ``EngineFailurePolicyInterface``. Opening without a probe time
    would be a one-way door because an open engine cannot be selected to prove
    it has recovered.
    """

    threshold: int = ENGINE_FAILURE_THRESHOLD
    probe_base: timedelta = ENGINE_FAILURE_PROBE_BASE
    probe_cap: timedelta = ENGINE_FAILURE_PROBE_CAP

    def __post_init__(self) -> None:
        if isinstance(self.threshold, bool) or self.threshold < 1:
            raise ValueError("an engine-failure threshold is a whole number of at least 1")
        if self.probe_base <= timedelta(0):
            raise ValueError("an engine-failure probe delay must be positive")
        if self.probe_cap < self.probe_base:
            raise ValueError("an engine-failure probe cap cannot be below its base delay")

    def trips(self, consecutive_failures: int) -> bool:
        """Whether the consecutive-failure count has reached the threshold."""
        return consecutive_failures >= self.threshold

    def probe_at(self, *, now: datetime, consecutive_failures: int) -> datetime:
        """Return the next probe time, exponentially backed off and capped."""
        attempt = max(consecutive_failures - self.threshold, 0)
        return now + _backoff(attempt, base=self.probe_base, cap=self.probe_cap)


ENGINE_FAILURE_POLICY: Final[EngineFailurePolicyInterface] = EngineFailurePolicy()
"""The shared default, annotated so static typing verifies its interface."""
