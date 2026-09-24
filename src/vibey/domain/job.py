# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import hashlib
from dataclasses import dataclass
from datetime import timedelta
from enum import StrEnum
from typing import ClassVar, Final
from uuid import UUID

from vibey.domain.interfaces.stored_value_interface import StoredValueParserInterface
from vibey.domain.stored_value import StoredValueParser, UnrecognizedValue


class JobState(StrEnum):
    READY = "ready"
    LEASED = "leased"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    AWAITING_HUMAN = "awaiting_human"
    AWAITING_CAPACITY = "awaiting_capacity"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class UnrecognizedJobState(UnrecognizedValue):
    """A stored job state this vibey has no `JobState` member for (vibey#287).

    `job_state` is a Postgres enum a newer vibey widens with a migration. The claim
    only ever takes a `ready` row, so an older worker never works such a job; it
    still reads and counts it, under its stored name, when it reports the queue.
    """

    members: ClassVar[frozenset[str]] = frozenset(state.value for state in JobState)


type StoredJobState = JobState | UnrecognizedJobState
"""What a stored job state reads as: a member, or the text of one this vibey does
not know."""

JOB_STATE_PARSER: Final[StoredValueParserInterface[JobState, UnrecognizedJobState]] = (
    StoredValueParser(JobState, UnrecognizedJobState)
)
"""The parser every reader of `job.state` shares. Stateless."""


ATTEMPTS_EXHAUSTED_GATE_KIND: Final = "attempts_exhausted"
"""The worker's gate when a job's handler failed on every attempt (ADR-0024)."""

DELIVERY_EXHAUSTED_GATE_KIND: Final = "delivery_exhausted"
"""The queue reaper's gate when a job's worker died on every attempt (ADR-0056)."""

QUEUE_GATE_KINDS: Final = frozenset({ATTEMPTS_EXHAUSTED_GATE_KIND, DELIVERY_EXHAUSTED_GATE_KIND})
"""The gates the queue raises on a job's behalf, never the job itself.

Answering one buys the job another delivery and answers nothing its handler asked, so a
handler's own gate lookup never returns one (`HumanGateRepository.latest_for_job`). Only the
worker, which raised them, reads them back -- for the attempt grant an answer may carry.
"""


class FailureClass(StrEnum):
    CAPACITY = "capacity"  # opens the circuit
    ENGINE = "engine"  # opens after 3
    WORK = "work"  # the code is wrong -- circuit untouched
    VIBEY = "vibey"  # our bug -- circuit untouched


def backoff(
    attempt: int,
    *,
    base: timedelta = timedelta(seconds=2),
    cap: timedelta = timedelta(minutes=15),
) -> timedelta:
    if attempt < 0:
        attempt = 0
    capped_attempt = min(attempt, 32)
    multiplier: int = 2**capped_attempt
    delay = base * multiplier
    return min(delay, cap)


def idempotency_key(project_id: UUID, cycle: int, kind: str, subject: str) -> str:
    raw = f"{project_id}:{cycle}:{kind}:{subject}".encode()
    return hashlib.sha256(raw).hexdigest()
