# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue reaping: when queued or held work is stuck, by measurement and never by feel (ADR-0056).

Everything a queue guards can get stuck in one of five ways, and each is judged here
against a declared threshold (12.c), so a reap is a gate a number crossed (12.d):

(a) **A hung handler.** A live holder keeps a piece of work past its deadline: the
    heartbeat that should have pushed the deadline out stopped. ``HUNG_HANDLER``.
(b) **A holder that is gone.** The work is still held, but whoever held it is not there:
    unacknowledged messages on a queue with no consumer. ``HOLDER_GONE``.
    Where the holder's liveness cannot be told apart from a hang -- a PostgreSQL lease,
    which records only when it runs out -- (a) and (b) are one condition,
    ``LEASE_EXPIRED``, and are answered the same way.
(c) **A poison message.** The work has been handed out as many times as its limit
    allows and never settled. Handing it out again is the unbounded ladder ADR-0024
    rules out, so it is dead-lettered, or parked where there is no dead-letter queue.
    ``POISON``.
(d) **Ready work nobody takes.** Work is ready, and has been for longer than the
    declared age, with no consumer to take it. Nothing is moved -- there is nowhere
    better to put it -- but it is surfaced, loudly. ``STALE_READY``.
(e) **Dead letters.** A dead-letter queue holds work. A reaper never deletes one: each
    becomes a parked job and a ``human_gate`` row, the reason recorded. Work on a queue
    vibey does not own is surfaced instead, and never touched. ``DEAD_LETTERED``.

Every verdict carries the object, the condition, the measured value, the threshold and
the action, which is exactly what the ledger records. Nothing here reads a clock: ``now``
is always an argument, so the same inputs always give the same verdict.

The names are ``Reap*``, not ``BusReap*``, on purpose: the PostgreSQL job queue is judged
by the same policy as the broker, so both backends reap identically. The storm's push-lock
reaper is a different reaper over a different lock; if the two converge, this module's
``ReapCondition`` is the vocabulary to converge on.
"""

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Final

from vibey.domain.interfaces.queue_reap_interface import (
    DeadLetterInterface,
    DeadLetterPeekInterface,
    HeldWorkInterface,
    QueueDepthInterface,
    QueueReapPolicyInterface,
    ReapThresholdsInterface,
)


class ReapCondition(StrEnum):
    """What was stuck. One member per measurable condition; see the module docstring."""

    HUNG_HANDLER = "hung_handler"
    HOLDER_GONE = "holder_gone"
    LEASE_EXPIRED = "lease_expired"
    POISON = "poison"
    STALE_READY = "stale_ready"
    DEAD_LETTERED = "dead_lettered"


class ReapAction(StrEnum):
    """What the reaper does about it."""

    REQUEUE = "requeue"
    """Back to ready, the attempt already counted: every job is idempotent under replay."""

    DEAD_LETTER = "dead_letter"
    """Rejected without requeue, so the broker routes it to the queue's dead-letter queue,
    where condition (e) parks it."""

    PARK = "park"
    """A parked job and a ``human_gate`` row: a person decides, and no worker waits."""

    SURFACE = "surface"
    """Reported loudly -- the ledger, the log, ``vibey queue reap`` -- and nothing moved."""


class HolderState(StrEnum):
    """Whether whoever holds a piece of work is still there."""

    LIVE = "live"
    GONE = "gone"
    UNKNOWN = "unknown"
    """A PostgreSQL lease records only when it runs out, never why."""


DEFAULT_LEASE_GRACE_SECONDS: Final = 0
DEFAULT_STALE_READY_SECONDS: Final = 900
DEFAULT_DEAD_LETTER_MIN_DEPTH: Final = 1


@dataclass(frozen=True, slots=True)
class ReapThresholds:
    """The declared thresholds (12.c). The defaults are the ``[queue.reap]`` defaults."""

    lease_grace_seconds: int = DEFAULT_LEASE_GRACE_SECONDS
    """How far past its deadline held work may run before it is reaped. The deadline is
    already the heartbeat's own bound, so the default adds nothing to it."""

    stale_ready_seconds: int = DEFAULT_STALE_READY_SECONDS
    """How long ready work may wait with nobody to take it before it is surfaced."""

    dead_letter_min_depth: int = DEFAULT_DEAD_LETTER_MIN_DEPTH
    """How many dead letters a dead-letter queue must hold before it is acted on. One:
    a single dead letter is already work nobody is doing."""

    def __post_init__(self) -> None:
        if self.lease_grace_seconds < 0:
            raise ValueError("lease_grace_seconds must not be negative")
        if self.stale_ready_seconds < 1:
            raise ValueError("stale_ready_seconds must be at least 1")
        if self.dead_letter_min_depth < 1:
            raise ValueError("dead_letter_min_depth must be at least 1")


@dataclass(frozen=True, slots=True)
class HeldWork:
    """One piece of work somebody holds: a leased job, or an unacknowledged delivery."""

    subject: str
    """What is held: a job id, or a delivery's identity."""

    queue: str
    deadline_at: datetime
    """When the holder's claim runs out unless its heartbeat pushes it on: a lease's
    ``lease_expires_at``, or a delivery's last heartbeat plus its processing deadline."""

    attempts: int
    """How many times it has been handed out, this time included."""

    attempt_limit: int
    """How many hand-outs it may have: a job's ``max_attempts``, a queue's delivery limit."""

    holder: HolderState = HolderState.UNKNOWN
    can_dead_letter: bool = False
    """Whether the queue it came from has a dead-letter queue to reject it into."""


@dataclass(frozen=True, slots=True)
class QueueDepth:
    """One queue, as measured once."""

    queue: str
    ready: int
    unacked: int
    consumers: int | None
    """None when the backend cannot say: PostgreSQL knows no workers, only leases."""

    oldest_ready_age_seconds: float | None
    """How long the oldest ready item has been ready; None when it cannot be measured
    (a message published without a timestamp). Unmeasured is not old (10.f)."""

    dead_letter: bool = False
    owned: bool = False
    """Whether vibey owns the queue. A reaper acts only on what vibey owns; everything
    else on a shared broker -- Plane's Celery queues -- is surfaced and left alone."""


@dataclass(frozen=True, slots=True)
class DeadLetter:
    """One message on a dead-letter queue, read without taking it off."""

    queue: str
    """The dead-letter queue it sits on."""

    origin_queue: str
    """The queue it was dead-lettered from: the first ``x-death`` entry's queue, or the
    dead-letter queue's name without its suffix when the broker recorded none."""

    reason: str
    """Why the broker dead-lettered it: ``rejected``, ``expired``, ``maxlen``,
    ``delivery_limit``; ``unknown`` when it recorded none."""

    body: str
    message_id: str | None = None
    first_death_at: str | None = None
    truncated: bool = False
    """True when the broker handed back only part of the body."""

    @property
    def identity(self) -> str:
        """The message's own id, or a digest of where it died, when, and what it said.

        Stable across reads, so parking is idempotent by identity: a second read of the
        same dead letter finds it parked and does nothing. Two messages with no id, the
        same body and the same first death are one identity -- the one collision this
        admits, and one a publisher avoids by setting ``message_id`` (vibey's does).
        """
        if self.message_id:
            return f"id:{self.message_id}"
        text = f"{self.origin_queue}\n{self.first_death_at or ''}\n{self.body}"
        return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()

    def payload_object(self) -> dict[str, object] | None:
        """The body as a JSON object, or None when it is not one -- or was cut short,
        which is never replayed as though it were whole."""
        if self.truncated:
            return None
        try:
            value = json.loads(self.body)
        except ValueError:
            return None
        return value if isinstance(value, dict) else None


@dataclass(frozen=True, slots=True)
class DeadLetterPeek:
    """A bounded read of one dead-letter queue, and whether it read the whole span."""

    queue: str
    depth: int
    items: tuple[DeadLetter, ...] = ()

    @property
    def complete(self) -> bool:
        """Whether every message on the queue was read. A partial read is reported as
        partial, never as the whole (10.g)."""
        return len(self.items) >= self.depth


@dataclass(frozen=True, slots=True)
class BrokerPolicy:
    """The broker policy vibey reconciles onto the queues it owns, from ``[queue.reap]``.

    ``consumer-timeout`` bounds a hung handler at the broker (a): past it the broker
    closes the channel and every delivery it held is requeued. ``delivery-limit`` bounds a
    poison message (c) on a quorum queue: past it the broker dead-letters it. Classic
    queues ignore ``delivery-limit``; that is RabbitMQ's rule, stated here so nobody reads
    the key as a guarantee it is not.
    """

    name: str
    pattern: str
    consumer_timeout_ms: int
    delivery_limit: int
    priority: int = 0
    dead_letter_pattern: str = r"(\.dlq|\.dead)$"

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a broker policy needs a name")
        patterns = (("pattern", self.pattern), ("dead_letter_pattern", self.dead_letter_pattern))
        for label, pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"{label} is not a regular expression: {exc}") from exc
        if self.consumer_timeout_ms < 1:
            raise ValueError("consumer_timeout_ms must be at least 1")
        if self.delivery_limit < 1:
            raise ValueError("delivery_limit must be at least 1")

    def owns(self, queue: str) -> bool:
        return re.search(self.pattern, queue) is not None

    def is_dead_letter(self, queue: str) -> bool:
        return re.search(self.dead_letter_pattern, queue) is not None

    def definition(self) -> dict[str, object]:
        return {
            "consumer-timeout": self.consumer_timeout_ms,
            "delivery-limit": self.delivery_limit,
        }

    def body(self) -> dict[str, object]:
        """The management API's policy document."""
        return {
            "pattern": self.pattern,
            "definition": self.definition(),
            "priority": self.priority,
            "apply-to": "queues",
        }

    def matches(self, observed: object) -> bool:
        """Whether a policy read back from the broker is this one: the only evidence a
        write landed (12.e)."""
        if not isinstance(observed, dict):
            return False
        return (
            observed.get("pattern") == self.pattern
            and observed.get("definition") == self.definition()
            and observed.get("priority") == self.priority
            and observed.get("apply-to") == "queues"
        )


@dataclass(frozen=True, slots=True)
class PolicyOutcome:
    """What reconciling the broker policy achieved, as read back -- never as written."""

    policy: str
    verified: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ReapVerdict:
    """One measured condition and what is done about it: what the ledger records."""

    subject: str
    queue: str
    condition: ReapCondition
    measured: float
    threshold: float
    unit: str
    action: ReapAction
    detail: dict[str, object] = field(default_factory=dict)

    def payload(self) -> dict[str, object]:
        """The ledger payload: object, condition, measured value, threshold, action."""
        body: dict[str, object] = {
            "object": self.subject,
            "queue": self.queue,
            "condition": self.condition.value,
            "measured": self.measured,
            "threshold": self.threshold,
            "unit": self.unit,
            "action": self.action.value,
        }
        if self.detail:
            body["detail"] = dict(self.detail)
        return body


class QueueReapPolicy:
    """Judges held work, queues and dead letters against the declared thresholds.

    Pure: the measurement and ``now`` come in, a verdict or nothing goes out. The same
    judgement serves the PostgreSQL job queue and the broker, so both reap identically.
    """

    def judge_held(
        self,
        work: HeldWorkInterface,
        *,
        now: datetime,
        thresholds: ReapThresholdsInterface,
    ) -> ReapVerdict | None:
        """(a), (b) and (c) for one piece of held work; None while it is within bounds."""
        overdue = (now - work.deadline_at).total_seconds()
        if overdue <= thresholds.lease_grace_seconds:
            return None
        if work.attempts >= work.attempt_limit:
            return ReapVerdict(
                subject=work.subject,
                queue=work.queue,
                condition=ReapCondition.POISON,
                measured=float(work.attempts),
                threshold=float(work.attempt_limit),
                unit="attempts",
                action=ReapAction.DEAD_LETTER if work.can_dead_letter else ReapAction.PARK,
                detail={"overdue_seconds": overdue, "holder": work.holder.value},
            )
        condition = {
            HolderState.LIVE: ReapCondition.HUNG_HANDLER,
            HolderState.GONE: ReapCondition.HOLDER_GONE,
            HolderState.UNKNOWN: ReapCondition.LEASE_EXPIRED,
        }[work.holder]
        return ReapVerdict(
            subject=work.subject,
            queue=work.queue,
            condition=condition,
            measured=overdue,
            threshold=float(thresholds.lease_grace_seconds),
            unit="seconds past deadline",
            action=ReapAction.REQUEUE,
            detail={"attempts": work.attempts, "attempt_limit": work.attempt_limit},
        )

    def judge_queue(
        self, depth: QueueDepthInterface, *, thresholds: ReapThresholdsInterface
    ) -> tuple[ReapVerdict, ...]:
        """(b), (d) and (e) for one queue measured once."""
        if depth.dead_letter:
            held = depth.ready + depth.unacked
            if held < thresholds.dead_letter_min_depth:
                return ()
            return (
                ReapVerdict(
                    subject=depth.queue,
                    queue=depth.queue,
                    condition=ReapCondition.DEAD_LETTERED,
                    measured=float(held),
                    threshold=float(thresholds.dead_letter_min_depth),
                    unit="messages",
                    action=ReapAction.PARK if depth.owned else ReapAction.SURFACE,
                ),
            )
        verdicts: list[ReapVerdict] = []
        if depth.unacked > 0 and depth.consumers == 0:
            verdicts.append(
                ReapVerdict(
                    subject=depth.queue,
                    queue=depth.queue,
                    condition=ReapCondition.HOLDER_GONE,
                    measured=float(depth.unacked),
                    threshold=0.0,
                    unit="unacknowledged messages with no consumer",
                    action=ReapAction.SURFACE,
                )
            )
        age = depth.oldest_ready_age_seconds
        if (
            depth.ready > 0
            and depth.consumers in (0, None)
            and age is not None
            and age >= thresholds.stale_ready_seconds
        ):
            verdicts.append(
                ReapVerdict(
                    subject=depth.queue,
                    queue=depth.queue,
                    condition=ReapCondition.STALE_READY,
                    measured=age,
                    threshold=float(thresholds.stale_ready_seconds),
                    unit="seconds ready with no consumer",
                    action=ReapAction.SURFACE,
                    detail={"ready": depth.ready},
                )
            )
        return tuple(verdicts)

    def judge_dead_letter(
        self,
        item: DeadLetterInterface,
        depth: QueueDepthInterface,
        *,
        thresholds: ReapThresholdsInterface,
    ) -> ReapVerdict:
        """(e) for one dead letter read off ``depth``'s queue: parked if vibey owns the
        queue, surfaced if it does not. Never deleted either way."""
        return ReapVerdict(
            subject=item.identity,
            queue=item.queue,
            condition=ReapCondition.DEAD_LETTERED,
            measured=float(depth.ready + depth.unacked),
            threshold=float(thresholds.dead_letter_min_depth),
            unit="messages",
            action=ReapAction.PARK if depth.owned else ReapAction.SURFACE,
            detail={"origin_queue": item.origin_queue, "reason": item.reason},
        )

    def judge_unread(self, peek: DeadLetterPeekInterface) -> ReapVerdict | None:
        """(e) for the part of a dead-letter queue a bounded read did not reach.

        A read returns every message it takes to its place, and a reaper never removes
        one, so what lies past the read limit stays past it until a person clears the
        queue. That remainder is measured and surfaced on every pass -- never assumed
        parked, never dropped from the count (10.g). None when the read was whole.
        """
        if peek.complete:
            return None
        return ReapVerdict(
            subject=peek.queue,
            queue=peek.queue,
            condition=ReapCondition.DEAD_LETTERED,
            measured=float(peek.depth - len(peek.items)),
            threshold=0.0,
            unit="dead letters past the read limit, not yet parked",
            action=ReapAction.SURFACE,
            detail={"read": len(peek.items), "depth": peek.depth},
        )


QUEUE_REAP_POLICY: Final[QueueReapPolicyInterface] = QueueReapPolicy()
"""The policy everything shares. Stateless, so one instance serves."""
