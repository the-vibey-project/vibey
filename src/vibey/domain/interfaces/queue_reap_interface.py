# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind queue reaping (ADR-0056).

Mirrors `vibey/domain/queue_reap.py` (ADR-0016). Interfaces declare; they never
consume. The domain types the seams are declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from datetime import datetime

    from vibey.domain.queue_reap import HolderState, ReapVerdict


@runtime_checkable
class ReapThresholdsInterface(Protocol):
    """The declared thresholds a verdict is measured against (12.c)."""

    @property
    def lease_grace_seconds(self) -> int: ...

    @property
    def stale_ready_seconds(self) -> int: ...

    @property
    def dead_letter_min_depth(self) -> int: ...


@runtime_checkable
class HeldWorkInterface(Protocol):
    """One piece of held work: a leased job or an unacknowledged delivery."""

    @property
    def subject(self) -> str: ...

    @property
    def queue(self) -> str: ...

    @property
    def deadline_at(self) -> datetime: ...

    @property
    def attempts(self) -> int: ...

    @property
    def attempt_limit(self) -> int: ...

    @property
    def holder(self) -> HolderState: ...

    @property
    def can_dead_letter(self) -> bool: ...


@runtime_checkable
class QueueDepthInterface(Protocol):
    """One queue, as measured once."""

    @property
    def queue(self) -> str: ...

    @property
    def ready(self) -> int: ...

    @property
    def unacked(self) -> int: ...

    @property
    def consumers(self) -> int | None: ...

    @property
    def oldest_ready_age_seconds(self) -> float | None: ...

    @property
    def dead_letter(self) -> bool: ...

    @property
    def owned(self) -> bool: ...


@runtime_checkable
class DeadLetterInterface(Protocol):
    """One message on a dead-letter queue, read without taking it off."""

    @property
    def queue(self) -> str: ...

    @property
    def origin_queue(self) -> str: ...

    @property
    def reason(self) -> str: ...

    @property
    def body(self) -> str: ...

    @property
    def identity(self) -> str:
        """Stable across reads: parking is idempotent by it."""
        ...

    def payload_object(self) -> dict[str, object] | None: ...


@runtime_checkable
class DeadLetterPeekInterface(Protocol):
    """A bounded read of one dead-letter queue."""

    @property
    def queue(self) -> str: ...

    @property
    def depth(self) -> int: ...

    @property
    def items(self) -> tuple[DeadLetterInterface, ...]: ...

    @property
    def complete(self) -> bool:
        """Whether the read reached every message on the queue."""
        ...


@runtime_checkable
class BrokerPolicyInterface(Protocol):
    """The broker policy vibey reconciles onto the queues it owns."""

    @property
    def name(self) -> str: ...

    def owns(self, queue: str) -> bool: ...

    def is_dead_letter(self, queue: str) -> bool: ...

    def body(self) -> dict[str, object]:
        """The management API's policy document."""
        ...

    def matches(self, observed: object) -> bool:
        """Whether a policy read back from the broker is this one."""
        ...


@runtime_checkable
class QueueReapPolicyInterface(Protocol):
    """Judges held work, queues and dead letters against the declared thresholds."""

    def judge_held(
        self,
        work: HeldWorkInterface,
        *,
        now: datetime,
        thresholds: ReapThresholdsInterface,
    ) -> ReapVerdict | None:
        """(a), (b) and (c); None while the work is within bounds."""
        ...

    def judge_queue(
        self, depth: QueueDepthInterface, *, thresholds: ReapThresholdsInterface
    ) -> tuple[ReapVerdict, ...]:
        """(b), (d) and (e) for one queue."""
        ...

    def judge_dead_letter(
        self,
        item: DeadLetterInterface,
        depth: QueueDepthInterface,
        *,
        thresholds: ReapThresholdsInterface,
    ) -> ReapVerdict:
        """(e) for one dead letter: parked if owned, surfaced if not."""
        ...

    def judge_unread(self, peek: DeadLetterPeekInterface) -> ReapVerdict | None:
        """(e) for the dead letters a bounded read did not reach; None when it was whole."""
        ...
