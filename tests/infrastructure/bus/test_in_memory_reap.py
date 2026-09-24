# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The in-memory bus with the RabbitMQ adapter's semantics, and the reaper end to end
over it (ADR-0056). CI has no broker; this is the same flow a broker would see."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from vibey.application.interfaces import BusInspectorPort, BusPort
from vibey.application.observability import StandardLibraryLogger
from vibey.application.queue_reaper import QueueReaper
from vibey.domain.config import QueueReapConfig
from vibey.domain.queue_reap import (
    DeadLetter,
    QueueDepth,
    ReapAction,
    ReapCondition,
    ReapVerdict,
)
from vibey.infrastructure.bus.in_memory import InMemoryBus, InMemoryMessage
from vibey.infrastructure.bus.interfaces import InMemoryBusInterface, InMemoryMessageInterface

PROJECT = UUID("6f1c2a4e-0000-4000-8000-000000000000")
T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


@dataclass
class Clock:
    at: datetime = T0

    def now(self) -> datetime:
        return self.at


@dataclass
class ParkingStore:
    """Just enough of the PostgreSQL store: parks by identity, records what it is told."""

    parked: dict[str, tuple[DeadLetter, ReapVerdict]] = field(default_factory=dict)
    recorded: list[ReapVerdict] = field(default_factory=list)

    async def preview_leases(self) -> tuple[ReapVerdict, ...]:
        return ()

    async def reap_leases(self) -> tuple[ReapVerdict, ...]:
        return ()

    async def ready_depths(self, project_id: UUID) -> tuple[QueueDepth, ...]:
        return ()

    async def park_dead_letter(
        self, project_id: UUID, item: DeadLetter, verdict: ReapVerdict
    ) -> UUID | None:
        if item.identity in self.parked:
            return None
        self.parked[item.identity] = (item, verdict)
        return uuid4()

    async def record(self, project_id: UUID, verdict: ReapVerdict) -> None:
        self.recorded.append(verdict)


def test_the_in_memory_bus_is_a_bus_and_an_inspector() -> None:
    bus = InMemoryBus()
    assert isinstance(bus, BusPort)
    assert isinstance(bus, BusInspectorPort)
    assert isinstance(bus, InMemoryBusInterface)
    message = InMemoryMessage(payload={}, published_at=T0, message_id="m")
    assert isinstance(message, InMemoryMessageInterface)


async def test_depths_measure_what_waits_and_for_how_long() -> None:
    clock = Clock()
    bus = InMemoryBus(clock=clock.now)
    await bus.publish("vibey.jobs", {"n": 1})
    clock.at = T0 + timedelta(seconds=30)
    await bus.publish("vibey.jobs", {"n": 2})
    clock.at = T0 + timedelta(seconds=90)
    depths = {d.queue: d for d in await bus.depths()}
    assert depths["vibey.jobs"] == QueueDepth(
        queue="vibey.jobs", ready=2, unacked=0, consumers=0, oldest_ready_age_seconds=90.0
    )
    assert depths["vibey.jobs.dlq"].oldest_ready_age_seconds is None


async def test_consuming_takes_on_get_so_nothing_is_ever_held() -> None:
    bus = InMemoryBus()
    assert await bus.consume("nowhere") is None
    await bus.publish("q", {"a": 1})
    assert await bus.consume("q") == {"a": 1}
    assert all(d.unacked == 0 for d in await bus.depths())


async def test_a_reject_dead_letters_to_the_queue_declared_for_it() -> None:
    bus = InMemoryBus()
    assert await bus.reject("q") is False
    await bus.publish("q", {"a": 1})
    assert await bus.reject("q", reason="expired") is True
    peek = await bus.peek_dead_letters("q.dlq", limit=10)
    (item,) = peek.items
    assert (item.origin_queue, item.reason, item.payload_object()) == ("q", "expired", {"a": 1})
    assert item.identity.startswith("id:")
    # A peek returns what it read: the dead letter is still there, and a second read
    # sees the same identity.
    again = await bus.peek_dead_letters("q.dlq", limit=10)
    assert again.items[0].identity == item.identity


async def test_a_reject_from_a_queue_without_a_dead_letter_queue_drops_the_message() -> None:
    """A dead-letter queue has no dead-letter queue of its own: rejected, it is gone --
    which is why a reaper never rejects from one."""
    bus = InMemoryBus()
    await bus.publish("q", {"a": 1})
    await bus.reject("q")
    assert await bus.reject("q.dlq") is True
    assert (await bus.peek_dead_letters("q.dlq", limit=10)).depth == 0


async def test_a_bounded_peek_says_it_is_partial_and_an_unknown_queue_is_empty() -> None:
    bus = InMemoryBus()
    for n in range(3):
        await bus.publish("q", {"n": n})
        await bus.reject("q")
    peek = await bus.peek_dead_letters("q.dlq", limit=2)
    assert (peek.depth, len(peek.items), peek.complete) == (3, 2, False)
    empty = await bus.peek_dead_letters("never", limit=2)
    assert (empty.depth, empty.items) == (0, ())
    await bus.declare_queue("plain", dead_letter=False)
    assert "plain.dlq" not in {d.queue for d in await bus.depths()}


async def test_a_policy_is_kept_and_read_back() -> None:
    bus = InMemoryBus()
    policy = QueueReapConfig().broker_policy()
    outcome = await bus.apply_policy(policy)
    assert outcome.verified
    assert bus.policy(policy.name) == policy.body()
    assert bus.policy("other") is None


async def test_the_reaper_over_the_in_memory_bus_end_to_end() -> None:
    """Publish, reject, and let the reaper find it: an owned dead letter is parked once;
    a foreign queue's ready work that ages past the threshold is surfaced and left."""
    clock = Clock()
    bus = InMemoryBus(clock=clock.now)
    store = ParkingStore()
    reaper = QueueReaper(
        store=store,
        bus=bus,
        config=QueueReapConfig(stale_ready_seconds=60),
        clock=clock,
        logger=StandardLibraryLogger(__name__),
    )
    await bus.publish("vibey.jobs.p", {"job_id": "j1"})
    await bus.reject("vibey.jobs.p")
    await bus.publish("celery", {"task": "t"})
    clock.at = T0 + timedelta(seconds=61)

    first = await reaper.run(PROJECT)
    assert first.ok
    assert first.policy is not None and first.policy.verified
    (parked,) = first.acted
    assert parked.condition is ReapCondition.DEAD_LETTERED
    assert parked.action is ReapAction.PARK
    assert parked.detail["origin_queue"] == "vibey.jobs.p"
    (stuck,) = first.surfaced
    assert (stuck.queue, stuck.condition, stuck.action) == (
        "celery",
        ReapCondition.STALE_READY,
        ReapAction.SURFACE,
    )
    assert store.recorded == [stuck]
    # Nothing was taken off the broker: the dead letter and Celery's message are both there.
    depths = {d.queue: d.ready for d in await bus.depths()}
    assert depths["vibey.jobs.p.dlq"] == 1 and depths["celery"] == 1

    second = await reaper.run(PROJECT)
    assert second.acted == ()
    assert len(store.parked) == 1
    assert store.recorded == [stuck]
