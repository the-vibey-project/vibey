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
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import ClassVar, Final

from vibey.domain.interfaces.queue_reap_interface import (
    DeadLetterInterface,
    DeadLetterPeekInterface,
    HeldWorkInterface,
    QueueAttachmentInterface,
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
    """Reported loudly -- the ledger, the log, ``vibey queue reap`` -- and nothing moved.
    Recorded once per sighting, fleet-wide: the ledger holds the sighting open until a pass
    that read the source whole no longer sees it."""

    CLEARED = "cleared"
    """A surfaced sighting that a later whole read no longer found: it closes the sighting,
    so its return is a new one (#1108 review finding 4)."""


class ReapSource(StrEnum):
    """Where a verdict was measured -- and so who wrote the names in it."""

    JOB_QUEUE = "job_queue"
    """vibey's own PostgreSQL job queue: vibey's rows, vibey's words (`trusted`)."""

    BROKER = "broker"
    """A queue on the broker. Anyone with the broker's credentials names its queues and
    writes its messages' headers, so what a broker verdict names is `untrusted` (SD-01 §4)."""


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

    source: ReapSource = ReapSource.JOB_QUEUE


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

    source: ReapSource = ReapSource.BROKER
    kind: str = ""
    """The broker's queue type (`classic`, `quorum`, `stream`), where it reports one. A
    quorum queue reports no head-message timestamp, so its ready age is never measured
    (#1108 review finding 12)."""


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
    """The broker policies vibey reconciles onto the queues it owns, from ``[queue.reap]``.

    ``consumer-timeout`` bounds a hung handler at the broker (a): past it the broker
    closes the channel and every delivery it held is requeued. ``delivery-limit`` bounds a
    poison message (c) on a quorum queue: past it the broker dead-letters it.

    **Two policies, one per queue type** (#1108 review finding 2). Observed on the pinned
    image (RabbitMQ 4.3.6): a policy whose definition holds ``delivery-limit`` does not
    attach to a classic queue at all -- it did not merely ignore the key, it left the queue
    with no policy, so its ``consumer-timeout`` never applied either. So quorum queues get
    ``name`` (both keys, ``apply-to: quorum_queues``) and classic queues get
    ``<name>-classic`` (``consumer-timeout`` only, ``apply-to: classic_queues``).
    """

    name: str
    pattern: str
    consumer_timeout_ms: int
    delivery_limit: int
    priority: int = 0
    dead_letter_pattern: str = r"(\.dlq|\.dead)$"

    FOREIGN_CANARIES: ClassVar[tuple[str, ...]] = (
        "celery",
        "celery.pidbox",
        "celeryev.canary",
        "amq.gen-canary",
    )
    """Names on a shared broker that are certainly not vibey's: Plane's Celery queues and
    the broker's own server-named queues. A pattern that owns one would put a policy on it,
    and park its dead letters, so it is refused (#1108 review)."""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("a broker policy needs a name")
        patterns = (("pattern", self.pattern), ("dead_letter_pattern", self.dead_letter_pattern))
        for label, pattern in patterns:
            try:
                compiled = re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"{label} is not a regular expression: {exc}") from exc
            if compiled.search("") is not None:
                raise ValueError(
                    f"{label} {pattern!r} matches every queue name; name the queues it means"
                )
        foreign = [name for name in self.FOREIGN_CANARIES if self.owns(name)]
        if foreign:
            raise ValueError(
                f"pattern {self.pattern!r} would own {foreign[0]!r}, a queue vibey does not own"
            )
        if self.consumer_timeout_ms < 1:
            raise ValueError("consumer_timeout_ms must be at least 1")
        if self.delivery_limit < 1:
            raise ValueError("delivery_limit must be at least 1")
        if self.priority < 0:
            raise ValueError("priority must not be negative")

    def owns(self, queue: str) -> bool:
        return re.search(self.pattern, queue) is not None

    def is_dead_letter(self, queue: str) -> bool:
        return re.search(self.dead_letter_pattern, queue) is not None

    def documents(self) -> tuple["PolicyDocument", ...]:
        """The policies, quorum first: what the broker is told, and read back against."""
        return (
            PolicyDocument(
                name=self.name,
                pattern=self.pattern,
                apply_to="quorum_queues",
                definition={
                    "consumer-timeout": self.consumer_timeout_ms,
                    "delivery-limit": self.delivery_limit,
                },
                priority=self.priority,
            ),
            PolicyDocument(
                name=f"{self.name}-classic",
                pattern=self.pattern,
                apply_to="classic_queues",
                definition={"consumer-timeout": self.consumer_timeout_ms},
                priority=self.priority,
            ),
        )

    def expected_for(self, kind: str) -> "PolicyDocument | None":
        """The policy a queue of this type should carry; None for a type no policy of
        vibey's applies to (a stream)."""
        quorum, classic = self.documents()
        return {"quorum": quorum, "classic": classic}.get(kind)

    def attachment_gaps(self, queues: Iterable[QueueAttachmentInterface]) -> tuple[str, ...]:
        """Every owned queue the broker says does NOT carry vibey's policy, and why: the
        only evidence a policy is in force is the queue reporting it (12.e). A queue the
        broker gives no type for is a gap -- its policy cannot be judged -- never a pass."""
        gaps: list[str] = []
        for queue in queues:
            if not self.owns(queue.queue):
                continue
            if queue.kind == "stream":
                continue
            expected = self.expected_for(queue.kind)
            if expected is None:
                gaps.append(f"{queue.queue}: queue type {queue.kind or 'unknown'!r} not judged")
                continue
            if queue.policy != expected.name:
                gaps.append(
                    f"{queue.queue} ({queue.kind}): carries {queue.policy or 'no policy'!r}, "
                    f"not {expected.name!r}"
                )
                continue
            missing = {
                key: value
                for key, value in expected.definition.items()
                if queue.effective.get(key) != value
            }
            if missing:
                gaps.append(f"{queue.queue} ({queue.kind}): effective policy lacks {missing}")
        return tuple(gaps)


@dataclass(frozen=True, slots=True)
class PolicyDocument:
    """One broker policy, as the management API takes and reports it."""

    name: str
    pattern: str
    apply_to: str
    definition: dict[str, object]
    priority: int = 0

    def body(self) -> dict[str, object]:
        """The management API's policy document."""
        return {
            "pattern": self.pattern,
            "definition": dict(self.definition),
            "priority": self.priority,
            "apply-to": self.apply_to,
        }

    def matches(self, observed: object) -> bool:
        """Whether a policy read back from the broker is this one (12.e)."""
        if not isinstance(observed, dict):
            return False
        return (
            observed.get("pattern") == self.pattern
            and observed.get("definition") == self.definition
            and observed.get("priority") == self.priority
            and observed.get("apply-to") == self.apply_to
        )


@dataclass(frozen=True, slots=True)
class QueueAttachment:
    """What the broker reports a queue carries: its type, the policy applied to it, and
    the effective definition -- the policy in force, not the one written."""

    queue: str
    kind: str
    policy: str | None
    effective: dict[str, object] = field(default_factory=dict)


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
    source: ReapSource = ReapSource.BROKER
    episode: str = ""
    """What makes a sighting of the same condition on the same object a new one: the size
    of an unread dead-letter remainder, so its growth is recorded again (finding 10)."""

    @property
    def sighting(self) -> tuple[str, str, str, str, str]:
        """The key a sighting is recorded under, once, whichever process sees it."""
        return (self.source.value, self.queue, self.condition.value, self.subject, self.episode)

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
            "source": self.source.value,
            "episode": self.episode,
        }
        if self.detail:
            body["detail"] = dict(self.detail)
        return body

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> "ReapVerdict":
        """The verdict a `QueueReaped` event recorded. Raises ValueError on a payload no
        vibey wrote; an event written before `source` and `episode` existed reads as a
        broker sighting with no episode."""
        try:
            detail = payload.get("detail", {})
            return cls(
                subject=str(payload["object"]),
                queue=str(payload["queue"]),
                condition=ReapCondition(str(payload["condition"])),
                measured=float(str(payload["measured"])),
                threshold=float(str(payload["threshold"])),
                unit=str(payload["unit"]),
                action=ReapAction(str(payload["action"])),
                detail=dict(detail) if isinstance(detail, Mapping) else {},
                source=ReapSource(str(payload.get("source", ReapSource.BROKER.value))),
                episode=str(payload.get("episode", "")),
            )
        except (KeyError, ValueError) as exc:
            raise ValueError(f"not a QueueReaped payload: {exc}") from exc

    def cleared(self) -> "ReapVerdict":
        """The record that closes this sighting: same key, nothing measured now."""
        return ReapVerdict(
            subject=self.subject,
            queue=self.queue,
            condition=self.condition,
            measured=0.0,
            threshold=self.threshold,
            unit=self.unit,
            action=ReapAction.CLEARED,
            source=self.source,
            episode=self.episode,
        )


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
                source=work.source,
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
            source=work.source,
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
                    source=depth.source,
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
                    source=depth.source,
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
                    unit=(
                        "seconds claimable and unclaimed"
                        if depth.source is ReapSource.JOB_QUEUE
                        else "seconds ready with no consumer"
                    ),
                    action=ReapAction.SURFACE,
                    detail={"ready": depth.ready},
                    source=depth.source,
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
            source=ReapSource.BROKER,
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
        remaining = peek.depth - len(peek.items)
        return ReapVerdict(
            subject=peek.queue,
            queue=peek.queue,
            condition=ReapCondition.DEAD_LETTERED,
            measured=float(remaining),
            threshold=0.0,
            unit="dead letters past the read limit, not yet parked",
            action=ReapAction.SURFACE,
            detail={"read": len(peek.items), "depth": peek.depth},
            source=ReapSource.BROKER,
            episode=str(remaining),
        )


QUEUE_REAP_POLICY: Final[QueueReapPolicyInterface] = QueueReapPolicy()
"""The policy everything shares. Stateless, so one instance serves."""
