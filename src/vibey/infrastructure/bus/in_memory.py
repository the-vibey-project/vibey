# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""In-memory Bus implementation of the service-bus port (ADR-0042).

It also answers the reaper's reads (ADR-0056) with the RabbitMQ adapter's semantics, so
the reaper is tested end to end without a broker -- CI has none (ADR-0056 says so):

- consuming acknowledges on take, so no delivery is ever held: unacked is always 0;
- `reject` dead-letters the head message the way `basic.reject(requeue=false)` does --
  to `<queue>.dlq` when the queue was declared with one, and nowhere when it was not;
- a peek returns every message it reads to its place;
- a policy is kept as written, and read back from what was kept.
"""

from __future__ import annotations

import json
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from vibey.application.interfaces.bus import BusPort
from vibey.application.interfaces.queue_reap import BusInspectorPort
from vibey.domain.interfaces.queue_reap_interface import BrokerPolicyInterface
from vibey.domain.queue_reap import DeadLetter, DeadLetterPeek, PolicyOutcome, QueueDepth


@dataclass(frozen=True, slots=True)
class InMemoryMessage:
    """One message and what a broker would know about it."""

    payload: dict[str, object]
    published_at: datetime
    message_id: str
    died_on: str | None = None
    reason: str | None = None


class InMemoryBus(BusPort, BusInspectorPort):
    """Faked queues for testing and unconfigured local runs."""

    def __init__(self, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._clock = clock
        self._queues: dict[str, deque[InMemoryMessage]] = {}
        self._dead: dict[str, str] = {}
        self._policies: dict[str, dict[str, object]] = {}

    async def declare_queue(self, queue: str, *, dead_letter: bool = True) -> None:
        self._queues.setdefault(queue, deque())
        if dead_letter:
            dlq = f"{queue}.dlq"
            self._queues.setdefault(dlq, deque())
            self._dead[queue] = dlq

    async def publish(self, queue: str, payload: dict[str, object]) -> None:
        await self.declare_queue(queue)
        self._queues[queue].append(
            InMemoryMessage(
                payload=dict(payload), published_at=self._clock(), message_id=uuid.uuid4().hex
            )
        )

    async def consume(self, queue: str) -> dict[str, object] | None:
        pending = self._queues.get(queue)
        if not pending:
            return None
        return pending.popleft().payload

    async def reject(self, queue: str, *, reason: str = "rejected") -> bool:
        """Dead-letter the head of `queue`: to its dead-letter queue, or -- declared
        without one -- nowhere, as a broker drops it. False when the queue is empty."""
        pending = self._queues.get(queue)
        if not pending:
            return False
        message = pending.popleft()
        dlq = self._dead.get(queue)
        if dlq is not None:
            self._queues[dlq].append(
                InMemoryMessage(
                    payload=message.payload,
                    published_at=message.published_at,
                    message_id=message.message_id,
                    died_on=queue,
                    reason=reason,
                )
            )
        return True

    async def depths(self) -> tuple[QueueDepth, ...]:
        now = self._clock()
        return tuple(
            QueueDepth(
                queue=name,
                ready=len(messages),
                unacked=0,
                consumers=0,
                oldest_ready_age_seconds=(
                    (now - messages[0].published_at).total_seconds() if messages else None
                ),
            )
            for name, messages in sorted(self._queues.items())
        )

    async def peek_dead_letters(self, queue: str, *, limit: int) -> DeadLetterPeek:
        messages = list(self._queues.get(queue, ()))
        items = tuple(
            DeadLetter(
                queue=queue,
                origin_queue=message.died_on or queue.removesuffix(".dlq"),
                reason=message.reason or "unknown",
                body=json.dumps(message.payload),
                message_id=message.message_id,
                first_death_at=message.published_at.isoformat(),
            )
            for message in messages[:limit]
        )
        return DeadLetterPeek(queue=queue, depth=len(messages), items=items)

    async def apply_policy(self, policy: BrokerPolicyInterface) -> PolicyOutcome:
        self._policies[policy.name] = policy.body()
        observed = self._policies.get(policy.name)
        return PolicyOutcome(
            policy=policy.name,
            verified=policy.matches(observed),
            detail="kept in memory and read back",
        )

    def policy(self, name: str) -> dict[str, object] | None:
        """The policy document kept under `name`, as a broker would report it."""
        return self._policies.get(name)
