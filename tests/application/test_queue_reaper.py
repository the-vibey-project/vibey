# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queue reaper's pass (ADR-0056): each condition with a fake store, a fake broker
and a fake clock, so every branch runs without a database or a broker."""

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from vibey.application.dto import QueueReapReport
from vibey.application.interfaces import (
    BusInspectorPort,
    DeliveryExhaustedGateInterface,
    QueueReaperInterface,
    QueueReapStore,
)
from vibey.application.queue_reaper import (
    DELIVERY_EXHAUSTED_GATE,
    DELIVERY_EXHAUSTED_GATE_KIND,
    QueueReaper,
)
from vibey.domain.config import QueueReapConfig
from vibey.domain.interfaces.queue_reap_interface import BrokerPolicyInterface
from vibey.domain.queue_reap import (
    DeadLetter,
    DeadLetterPeek,
    PolicyOutcome,
    QueueDepth,
    ReapAction,
    ReapCondition,
    ReapVerdict,
)

PROJECT = UUID("6f1c2a4e-0000-4000-8000-000000000000")
T0 = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


def _verdict(
    condition: ReapCondition = ReapCondition.LEASE_EXPIRED,
    action: ReapAction = ReapAction.REQUEUE,
    subject: str = "job-1",
    queue: str = "job:p",
) -> ReapVerdict:
    return ReapVerdict(
        subject=subject,
        queue=queue,
        condition=condition,
        measured=5.0,
        threshold=0.0,
        unit="seconds past deadline",
        action=action,
    )


class Boom(RuntimeError):
    pass


@dataclass
class FakeStore:
    leases: tuple[ReapVerdict, ...] = ()
    ready: tuple[QueueDepth, ...] = ()
    fail: set[str] = field(default_factory=set)
    parked_identities: set[str] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)
    recorded: list[ReapVerdict] = field(default_factory=list)
    parked: list[tuple[DeadLetter, ReapVerdict]] = field(default_factory=list)

    def _enter(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail:
            raise Boom(f"{name} failed")

    async def preview_leases(self) -> tuple[ReapVerdict, ...]:
        self._enter("preview_leases")
        return self.leases

    async def reap_leases(self) -> tuple[ReapVerdict, ...]:
        self._enter("reap_leases")
        return self.leases

    async def ready_depths(self, project_id: UUID) -> tuple[QueueDepth, ...]:
        self._enter("ready_depths")
        return self.ready

    async def park_dead_letter(
        self, project_id: UUID, item: DeadLetter, verdict: ReapVerdict
    ) -> UUID | None:
        self._enter("park_dead_letter")
        if item.identity in self.parked_identities:
            return None
        self.parked_identities.add(item.identity)
        self.parked.append((item, verdict))
        return uuid4()

    async def record(self, project_id: UUID, verdict: ReapVerdict) -> None:
        self._enter("record")
        self.recorded.append(verdict)


@dataclass
class FakeBus:
    queues: tuple[QueueDepth, ...] = ()
    dead: dict[str, DeadLetterPeek] = field(default_factory=dict)
    outcome: PolicyOutcome = PolicyOutcome(policy="vibey-reap", verified=True, detail="ok")
    fail: set[str] = field(default_factory=set)
    calls: list[str] = field(default_factory=list)

    def _enter(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail:
            raise Boom(f"{name} failed")

    async def depths(self) -> tuple[QueueDepth, ...]:
        self._enter("depths")
        return self.queues

    async def peek_dead_letters(self, queue: str, *, limit: int) -> DeadLetterPeek:
        self._enter(f"peek:{queue}:{limit}")
        return self.dead[queue]

    async def apply_policy(self, policy: BrokerPolicyInterface) -> PolicyOutcome:
        self._enter("apply_policy")
        return self.outcome


@dataclass
class StepClock:
    at: datetime = T0

    def now(self) -> datetime:
        return self.at


@dataclass
class RecordingLogger:
    lines: list[tuple[str, dict[str, Any]]] = field(default_factory=list)

    def bind(self, **kwargs: Any) -> "RecordingLogger":
        return self

    def debug(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self.lines.append((event, kwargs))

    def events(self) -> list[str]:
        return [event for event, _ in self.lines]


def _reaper(
    store: FakeStore | None = None,
    bus: FakeBus | None = None,
    *,
    config: QueueReapConfig | None = None,
    clock: StepClock | None = None,
    logger: RecordingLogger | None = None,
) -> tuple[QueueReaper, FakeStore, RecordingLogger]:
    store = store if store is not None else FakeStore()
    logger = logger if logger is not None else RecordingLogger()
    reaper = QueueReaper(
        store=store,
        bus=bus,
        config=config if config is not None else QueueReapConfig(),
        clock=clock if clock is not None else StepClock(),
        logger=logger,
    )
    return reaper, store, logger


def _dead(identity: str, queue: str = "vibey.jobs.dlq") -> DeadLetter:
    return DeadLetter(
        queue=queue, origin_queue="vibey.jobs", reason="rejected", body="{}", message_id=identity
    )


# -- the seams -------------------------------------------------------------------------


def test_the_fakes_and_the_reaper_satisfy_their_ports() -> None:
    reaper, store, _ = _reaper()
    assert isinstance(reaper, QueueReaperInterface)
    assert isinstance(store, QueueReapStore)
    assert isinstance(FakeBus(), BusInspectorPort)
    assert isinstance(DELIVERY_EXHAUSTED_GATE, DeliveryExhaustedGateInterface)


def test_the_exhausted_gate_names_the_job_the_count_and_the_answer() -> None:
    verdict = ReapVerdict(
        subject="j",
        queue="job:p",
        condition=ReapCondition.POISON,
        measured=7.0,
        threshold=7.0,
        unit="attempts",
        action=ReapAction.PARK,
    )
    request = DELIVERY_EXHAUSTED_GATE.request(kind="build.implement", verdict=verdict)
    assert request.kind == DELIVERY_EXHAUSTED_GATE_KIND == "delivery_exhausted"
    assert "'build.implement' (j) was handed out 7 time(s), its limit of 7" in request.prompt
    assert "Answer anything to deliver it once more" in request.prompt


# -- leases: (a), (b), (c) on the job queue --------------------------------------------


async def test_a_pass_reaps_leases_and_reports_them() -> None:
    lease = _verdict()
    reaper, store, logger = _reaper(FakeStore(leases=(lease,)))
    report = await reaper.run(PROJECT)
    assert report.acted == (lease,)
    assert store.calls[:2] == ["reap_leases", "ready_depths"]
    assert report.ok
    assert "queue.reaped" in logger.events()
    assert any("broker: none configured" in note for note in report.notes)


async def test_a_dry_run_previews_leases_and_writes_nothing() -> None:
    lease = _verdict()
    reaper, store, logger = _reaper(FakeStore(leases=(lease,)))
    report = await reaper.run(PROJECT, dry_run=True)
    assert report.dry_run
    assert report.acted == (lease,)
    assert "reap_leases" not in store.calls
    assert "record" not in store.calls
    assert "queue.reap_planned" in logger.events()


async def test_a_pass_without_leases_does_not_touch_them() -> None:
    reaper, store, _ = _reaper()
    await reaper.run(PROJECT, leases=False)
    assert "reap_leases" not in store.calls


async def test_an_unreadable_lease_reap_is_named_and_the_pass_carries_on() -> None:
    reaper, store, logger = _reaper(FakeStore(fail={"reap_leases"}))
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("job-queue leases: reap_leases failed",)
    assert not report.ok
    assert "ready_depths" in store.calls
    assert "queue.reap_unreadable" in logger.events()


# -- (d) on the job queue --------------------------------------------------------------


def _stale(queue: str = "job:p", age: float = 1_000.0) -> QueueDepth:
    return QueueDepth(queue=queue, ready=2, unacked=0, consumers=None, oldest_ready_age_seconds=age)


async def test_stale_ready_work_is_surfaced_and_recorded_once_until_it_clears() -> None:
    store = FakeStore(ready=(_stale(),))
    reaper, _, logger = _reaper(store)
    first = await reaper.run(PROJECT)
    assert [v.condition for v in first.surfaced] == [ReapCondition.STALE_READY]
    assert len(store.recorded) == 1
    assert "queue.stuck" in logger.events()

    await reaper.run(PROJECT)
    assert len(store.recorded) == 1, "a condition still stuck is not recorded again"

    store.ready = ()
    await reaper.run(PROJECT)
    store.ready = (_stale(),)
    await reaper.run(PROJECT)
    assert len(store.recorded) == 2, "a condition that cleared and came back is recorded again"


async def test_a_surfaced_condition_is_not_recorded_in_a_dry_run() -> None:
    reaper, store, _ = _reaper(FakeStore(ready=(_stale(),)))
    report = await reaper.run(PROJECT, dry_run=True)
    assert report.surfaced
    assert store.recorded == []


async def test_an_unreadable_ready_measure_is_named() -> None:
    reaper, _, _ = _reaper(FakeStore(fail={"ready_depths"}))
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("job-queue ready work: ready_depths failed",)


async def test_a_recording_that_fails_is_named_and_retried_on_the_next_pass() -> None:
    store = FakeStore(ready=(_stale(),), fail={"record"})
    reaper, _, _ = _reaper(store)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("recording stale_ready on job:p: record failed",)
    store.fail.clear()
    await reaper.run(PROJECT)
    assert len(store.recorded) == 1


async def test_an_unreadable_source_keeps_what_was_already_surfaced() -> None:
    store = FakeStore(ready=(_stale(),))
    reaper, _, _ = _reaper(store, FakeBus())
    await reaper.run(PROJECT)
    assert len(store.recorded) == 1
    # The job queue cannot be read on this pass: that says nothing about whether the
    # stuck work cleared, so it is not forgotten -- and not recorded again when it is
    # read next time and is still stuck.
    store.fail.add("ready_depths")
    await reaper.run(PROJECT)
    store.fail.clear()
    await reaper.run(PROJECT)
    assert len(store.recorded) == 1


# -- the broker ------------------------------------------------------------------------


async def test_the_broker_policy_is_reconciled_and_its_read_back_reported() -> None:
    bus = FakeBus()
    reaper, _, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    assert bus.calls[0] == "apply_policy"
    assert report.policy == PolicyOutcome(policy="vibey-reap", verified=True, detail="ok")
    assert report.ok


async def test_an_unverified_policy_makes_the_pass_not_ok_and_says_so() -> None:
    bus = FakeBus(outcome=PolicyOutcome(policy="vibey-reap", verified=False, detail="refused"))
    reaper, _, logger = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    assert not report.ok
    assert "queue.reap_policy_unverified" in logger.events()


async def test_a_dry_run_does_not_write_the_policy() -> None:
    bus = FakeBus()
    reaper, _, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT, dry_run=True)
    assert "apply_policy" not in bus.calls
    assert report.policy is None
    assert any("not reconciled in a dry run" in note for note in report.notes)


async def test_an_unreachable_broker_is_named_twice_and_nothing_concluded() -> None:
    bus = FakeBus(fail={"apply_policy", "depths"})
    reaper, _, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    assert report.unreadable == (
        "broker policy 'vibey-reap': apply_policy failed",
        "broker queues: depths failed",
    )
    assert report.surfaced == ()


async def test_a_foreign_queue_is_surfaced_and_never_parked() -> None:
    """Plane's Celery queue on the shared broker: measured, surfaced, left alone."""
    celery = QueueDepth(
        queue="celery", ready=4, unacked=0, consumers=0, oldest_ready_age_seconds=5_000.0
    )
    celery_dead = QueueDepth(
        queue="celery.dlq", ready=2, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )
    bus = FakeBus(queues=(celery, celery_dead))
    reaper, store, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    conditions = sorted((v.queue, v.condition, v.action) for v in report.surfaced)
    assert conditions == [
        ("celery", ReapCondition.STALE_READY, ReapAction.SURFACE),
        ("celery.dlq", ReapCondition.DEAD_LETTERED, ReapAction.SURFACE),
    ]
    assert not [c for c in bus.calls if c.startswith("peek:")]
    assert store.parked == []


async def test_an_owned_dead_letter_queue_is_parked_item_by_item_and_idempotently() -> None:
    dlq = QueueDepth(
        queue="vibey.jobs.dlq", ready=2, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )
    items = (_dead("a"), _dead("b"))
    bus = FakeBus(
        queues=(dlq,), dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 2, items)}
    )
    reaper, store, _ = _reaper(
        store=FakeStore(), bus=bus, config=QueueReapConfig(dead_letter_peek_limit=7)
    )
    first = await reaper.run(PROJECT)
    assert "peek:vibey.jobs.dlq:7" in bus.calls
    assert [v.subject for v in first.acted] == ["id:a", "id:b"]
    assert all(v.action is ReapAction.PARK for v in first.acted)
    assert all("job_id" in v.detail for v in first.acted)
    assert [item.identity for item, _ in store.parked] == ["id:a", "id:b"]

    second = await reaper.run(PROJECT)
    assert second.acted == ()
    assert any("2 dead letter(s) already parked" in note for note in second.notes)
    assert len(store.parked) == 2


async def test_a_dry_run_plans_the_parks_without_making_them() -> None:
    dlq = QueueDepth(
        queue="vibey.jobs.dlq", ready=1, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )
    bus = FakeBus(
        queues=(dlq,),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 1, (_dead("a"),))},
    )
    reaper, store, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT, dry_run=True)
    assert [v.action for v in report.acted] == [ReapAction.PARK]
    assert "park_dead_letter" not in store.calls


async def test_dead_letters_past_the_read_limit_are_surfaced_not_assumed() -> None:
    dlq = QueueDepth(
        queue="vibey.jobs.dlq", ready=5, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )
    bus = FakeBus(
        queues=(dlq,),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 5, (_dead("a"),))},
    )
    reaper, _, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    (unread,) = report.surfaced
    assert unread.condition is ReapCondition.DEAD_LETTERED
    assert unread.measured == 4.0
    assert len(report.acted) == 1


async def test_an_unreadable_dead_letter_queue_and_a_failed_park_are_named() -> None:
    dlq = QueueDepth(
        queue="vibey.jobs.dlq", ready=1, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )
    bus = FakeBus(queues=(dlq,), fail={"peek:vibey.jobs.dlq:100"})
    reaper, _, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("dead letters on vibey.jobs.dlq: peek:vibey.jobs.dlq:100 failed",)

    bus = FakeBus(
        queues=(dlq,),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 1, (_dead("a"),))},
    )
    reaper, _, _ = _reaper(FakeStore(fail={"park_dead_letter"}), bus)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("parking id:a from vibey.jobs.dlq: park_dead_letter failed",)
    assert report.acted == ()


# -- automation ------------------------------------------------------------------------


async def test_run_if_due_runs_at_most_once_per_interval_and_never_reaps_leases() -> None:
    clock = StepClock()
    store = FakeStore(leases=(_verdict(),))
    reaper, _, _ = _reaper(store, clock=clock, config=QueueReapConfig(interval_seconds=60))
    first = await reaper.run_if_due(PROJECT)
    assert isinstance(first, QueueReapReport)
    assert "reap_leases" not in store.calls
    clock.at = T0 + timedelta(seconds=59)
    assert await reaper.run_if_due(PROJECT) is None
    clock.at = T0 + timedelta(seconds=60)
    assert await reaper.run_if_due(PROJECT) is not None


async def test_run_if_due_does_nothing_when_reaping_is_switched_off() -> None:
    reaper, store, _ = _reaper(config=QueueReapConfig(enabled=False))
    assert await reaper.run_if_due(PROJECT) is None
    assert store.calls == []


@pytest.mark.parametrize("dry_run", [True, False])
async def test_joined_keeps_the_later_policy_and_every_finding(dry_run: bool) -> None:
    left = QueueReapReport(
        project_id=PROJECT,
        dry_run=dry_run,
        acted=(_verdict(),),
        policy=PolicyOutcome(policy="a", verified=True),
        notes=("n1",),
    )
    right = QueueReapReport(project_id=PROJECT, dry_run=dry_run, unreadable=("u",))
    joined = left.joined(right)
    assert joined.policy == left.policy
    assert joined.acted == left.acted
    assert joined.notes == ("n1",) and joined.unreadable == ("u",)
    assert not joined.ok
    newer = PolicyOutcome(policy="b", verified=False)
    assert left.joined(QueueReapReport(PROJECT, dry_run, policy=newer)).policy == newer
