# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queue reaper's pass (ADR-0056): each condition with a fake store, a fake broker
and a fake clock, so every branch runs without a database or a broker. The fake store
keeps its sightings the way the ledger does -- shared by every reaper handed the same
store -- so fleet-wide recording is tested here and against PostgreSQL."""

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
    MAX_DEAD_LETTER_READ,
    QueueReaper,
)
from vibey.domain.config import QueueReapConfig
from vibey.domain.errors import LeaseReapIncomplete
from vibey.domain.interfaces.queue_reap_interface import BrokerPolicyInterface
from vibey.domain.job import DELIVERY_EXHAUSTED_GATE_KIND
from vibey.domain.queue_reap import (
    DeadLetter,
    DeadLetterPeek,
    PolicyOutcome,
    QueueDepth,
    ReapAction,
    ReapCondition,
    ReapSource,
    ReapVerdict,
)

PROJECT = UUID("6f1c2a4e-0000-4000-8000-000000000000")
OTHER = UUID("6f1c2a4e-0000-4000-8000-000000000001")
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
        source=ReapSource.JOB_QUEUE,
    )


class Boom(RuntimeError):
    pass


@dataclass
class FakeStore:
    leases: tuple[ReapVerdict, ...] = ()
    ready: tuple[tuple[UUID, QueueDepth], ...] = ()
    fail: set[str] = field(default_factory=set)
    incomplete: LeaseReapIncomplete | None = None
    parked_identities: dict[str, str] = field(default_factory=dict)
    calls: list[str] = field(default_factory=list)
    parked: list[tuple[UUID, DeadLetter, ReapVerdict, bool]] = field(default_factory=list)
    ledger: list[tuple[UUID, ReapVerdict]] = field(default_factory=list)
    """Every sighting recorded, and every clearing, in order: the shared ledger."""
    open_rows: list[tuple[UUID, ReapVerdict]] | None = None
    """When set, what `open_sightings` returns instead of what the ledger says."""

    def _enter(self, name: str) -> None:
        self.calls.append(name)
        if name in self.fail:
            raise Boom(f"{name} failed")

    async def preview_leases(self) -> tuple[ReapVerdict, ...]:
        self._enter("preview_leases")
        return self.leases

    async def reap_leases(self) -> tuple[ReapVerdict, ...]:
        self._enter("reap_leases")
        if self.incomplete is not None:
            raise self.incomplete
        return self.leases

    async def ready_depths(self) -> tuple[tuple[UUID, QueueDepth], ...]:
        self._enter("ready_depths")
        return self.ready

    async def parked_count(self, queue: str) -> int:
        self._enter("parked_count")
        return sum(1 for q in self.parked_identities.values() if q == queue)

    async def park_dead_letter(
        self, project_id: UUID, item: DeadLetter, verdict: ReapVerdict, *, origin_owned: bool
    ) -> UUID | None:
        self._enter("park_dead_letter")
        if item.identity in self.parked_identities:
            return None
        self.parked_identities[item.identity] = item.queue
        self.parked.append((project_id, item, verdict, origin_owned))
        return uuid4()

    def _latest(self, verdict: ReapVerdict) -> ReapAction | None:
        for _, recorded in reversed(self.ledger):
            if recorded.sighting == verdict.sighting:
                return recorded.action
        return None

    async def record_sighting(self, project_id: UUID, verdict: ReapVerdict) -> bool:
        self._enter("record_sighting")
        if self._latest(verdict) is ReapAction.SURFACE:
            return False
        self.ledger.append((project_id, verdict))
        return True

    async def open_sightings(self) -> tuple[tuple[UUID, ReapVerdict], ...]:
        self._enter("open_sightings")
        if self.open_rows is not None:
            return tuple(self.open_rows)
        latest: dict[tuple[str, ...], tuple[UUID, ReapVerdict]] = {}
        for project, verdict in self.ledger:
            latest[verdict.sighting] = (project, verdict)
        return tuple(pair for pair in latest.values() if pair[1].action is ReapAction.SURFACE)

    async def record_cleared(self, project_id: UUID, verdict: ReapVerdict) -> bool:
        self._enter("record_cleared")
        if self._latest(verdict) is not ReapAction.SURFACE:
            return False
        self.ledger.append((project_id, verdict.cleared()))
        return True

    def recorded(self, action: ReapAction = ReapAction.SURFACE) -> list[ReapVerdict]:
        return [v for _, v in self.ledger if v.action is action]


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
        whole = self.dead[queue]
        return DeadLetterPeek(queue=queue, depth=whole.depth, items=whole.items[:limit])

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


def _dead(identity: str, queue: str = "vibey.jobs.dlq", origin: str = "vibey.jobs") -> DeadLetter:
    return DeadLetter(
        queue=queue, origin_queue=origin, reason="rejected", body="{}", message_id=identity
    )


def _dlq(queue: str = "vibey.jobs.dlq", ready: int = 1) -> QueueDepth:
    return QueueDepth(
        queue=queue, ready=ready, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )


def _stale(project: UUID = PROJECT, age: float = 1_000.0) -> tuple[UUID, QueueDepth]:
    return (
        project,
        QueueDepth(
            queue=f"job:{project}",
            ready=2,
            unacked=0,
            consumers=None,
            oldest_ready_age_seconds=age,
            source=ReapSource.JOB_QUEUE,
        ),
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
    reaper, store, logger = _reaper(FakeStore(leases=(lease,), ready=(_stale(),)))
    report = await reaper.run(PROJECT, dry_run=True)
    assert report.dry_run
    assert report.acted == (lease,)
    assert report.surfaced
    assert "reap_leases" not in store.calls
    assert "record_sighting" not in store.calls
    assert "open_sightings" not in store.calls
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


async def test_a_partly_reaped_pass_keeps_what_it_reaped_and_names_the_rest() -> None:
    """#1108 review finding 8: one bad row no longer hides the rows that were reaped."""
    done = _verdict()
    store = FakeStore(incomplete=LeaseReapIncomplete((done, "not a verdict"), ("j2: Boom: x",)))
    reaper, _, _ = _reaper(store)
    report = await reaper.run(PROJECT)
    assert report.acted == (done,)
    assert report.unreadable == ("job-queue lease j2: Boom: x",)


# -- (d) on the job queue, and fleet-wide recording (findings 4 and 5) -----------------


async def test_claimable_unclaimed_work_is_recorded_under_its_own_project() -> None:
    """Finding 5: every project is measured, a project with no worker included, and each
    sighting is filed under the project whose work it is -- not the reaper's."""
    store = FakeStore(ready=(_stale(OTHER),))
    reaper, _, logger = _reaper(store)
    report = await reaper.run(PROJECT)
    (verdict,) = report.surfaced
    assert verdict.condition is ReapCondition.STALE_READY
    assert verdict.unit == "seconds claimable and unclaimed"
    assert verdict.source is ReapSource.JOB_QUEUE
    assert [project for project, _ in store.ledger] == [OTHER]
    assert "queue.stuck" in logger.events()


async def test_p3_one_sighting_is_recorded_once_by_every_pod_and_the_cli() -> None:
    """Finding 4 (P3): two pods and `vibey queue reap` recorded one continuous sighting
    three times, because each process remembered only its own. The ledger remembers."""
    shared = FakeStore(ready=(_stale(),))
    pod_a, _, _ = _reaper(shared)
    pod_b, _, _ = _reaper(shared)
    cli, _, _ = _reaper(shared)
    await pod_a.run(PROJECT)
    await pod_a.run(PROJECT)
    await pod_b.run(PROJECT)
    await cli.run(PROJECT)
    assert len(shared.recorded()) == 1


async def test_a_cleared_sighting_is_closed_once_and_its_return_is_new() -> None:
    shared = FakeStore(ready=(_stale(),))
    pod_a, _, logger = _reaper(shared)
    pod_b, _, _ = _reaper(shared)
    await pod_a.run(PROJECT)
    shared.ready = ()
    first = await pod_a.run(PROJECT)
    second = await pod_b.run(PROJECT)
    assert [v.action for v in first.cleared] == [ReapAction.CLEARED]
    assert second.cleared == (), "the other pod finds it closed already"
    assert len(shared.recorded(ReapAction.CLEARED)) == 1
    assert "queue.unstuck" in logger.events()
    shared.ready = (_stale(),)
    await pod_b.run(PROJECT)
    assert len(shared.recorded()) == 2


async def test_a_source_not_read_whole_clears_nothing() -> None:
    shared = FakeStore(ready=(_stale(),))
    reaper, _, _ = _reaper(shared)
    await reaper.run(PROJECT)
    shared.ready = ()
    shared.fail.add("ready_depths")
    report = await reaper.run(PROJECT)
    assert report.cleared == ()
    assert report.unreadable == ("job-queue claimable work: ready_depths failed",)


async def test_a_sighting_that_cannot_be_recorded_or_cleared_is_named() -> None:
    store = FakeStore(ready=(_stale(),), fail={"record_sighting"})
    reaper, _, _ = _reaper(store)
    report = await reaper.run(PROJECT)
    assert report.unreadable == (f"recording stale_ready on job:{PROJECT}: record_sighting failed",)

    open_one = _verdict(ReapCondition.STALE_READY, ReapAction.SURFACE)
    store = FakeStore(open_rows=[(PROJECT, open_one)], fail={"record_cleared"})
    reaper, _, _ = _reaper(store)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("clearing stale_ready on job:p: record_cleared failed",)

    open_one = _verdict(ReapCondition.STALE_READY, ReapAction.SURFACE)
    store = FakeStore(open_rows=[(PROJECT, open_one)])
    store.ledger.append((PROJECT, open_one.cleared()))
    reaper, _, _ = _reaper(store)
    report = await reaper.run(PROJECT)
    assert report.cleared == ()
    assert report.unreadable == ()

    store = FakeStore(fail={"open_sightings"})
    reaper, _, _ = _reaper(store)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("open sightings: open_sightings failed",)


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


async def test_an_unreachable_broker_is_named_and_no_broker_sighting_clears() -> None:
    celery = QueueDepth(
        queue="celery", ready=4, unacked=0, consumers=0, oldest_ready_age_seconds=5_000.0
    )
    shared = FakeStore()
    bus = FakeBus(queues=(celery,))
    reaper, _, _ = _reaper(shared, bus)
    await reaper.run(PROJECT)
    assert len(shared.recorded()) == 1
    bus.fail = {"apply_policy", "depths"}
    report = await reaper.run(PROJECT)
    assert report.unreadable == (
        "broker policy 'vibey-reap': apply_policy failed",
        "broker queues: depths failed",
    )
    assert report.cleared == ()


async def test_a_foreign_queue_is_surfaced_once_untrusted_and_never_parked() -> None:
    """Plane's Celery queue on the shared broker: measured, surfaced, left alone -- and,
    finding 4, recorded once for the fleet as a broker sighting, not once per project."""
    celery = QueueDepth(
        queue="celery", ready=4, unacked=0, consumers=0, oldest_ready_age_seconds=5_000.0
    )
    celery_dead = QueueDepth(
        queue="celery.dlq", ready=2, unacked=0, consumers=0, oldest_ready_age_seconds=None
    )
    shared = FakeStore()
    bus = FakeBus(queues=(celery, celery_dead))
    first, _, _ = _reaper(shared, bus)
    second, _, _ = _reaper(shared, bus)
    report = await first.run(PROJECT)
    await second.run(OTHER)
    conditions = sorted((v.queue, v.condition, v.action) for v in report.surfaced)
    assert conditions == [
        ("celery", ReapCondition.STALE_READY, ReapAction.SURFACE),
        ("celery.dlq", ReapCondition.DEAD_LETTERED, ReapAction.SURFACE),
    ]
    assert all(v.source is ReapSource.BROKER for v in report.surfaced)
    assert len(shared.recorded()) == 2
    assert {project for project, _ in shared.ledger} == {PROJECT}
    assert not [c for c in bus.calls if c.startswith("peek:")]
    assert shared.parked == []


async def test_unmeasurable_ready_work_on_the_broker_is_noted_not_assumed() -> None:
    """Finding 12: a quorum queue reports no head-message timestamp, so its ready age is
    never measured -- which the pass now says rather than stays silent about."""
    quorum = QueueDepth(
        queue="vibey.jobs.p",
        ready=3,
        unacked=0,
        consumers=0,
        oldest_ready_age_seconds=None,
        kind="quorum",
    )
    reaper, _, _ = _reaper(bus=FakeBus(queues=(quorum,)))
    report = await reaper.run(PROJECT)
    assert report.surfaced == ()
    assert any(
        "vibey.jobs.p: 3 ready with no consumer, age not measurable (a quorum" in note
        for note in report.notes
    )
    untyped = replace_kind(quorum, "")
    report = await _reaper(bus=FakeBus(queues=(untyped,)))[0].run(PROJECT)
    assert any("(a queue whose head message" in note for note in report.notes)


def replace_kind(depth: QueueDepth, kind: str) -> QueueDepth:
    from dataclasses import replace

    return replace(depth, kind=kind)


async def test_an_owned_dead_letter_queue_is_parked_item_by_item_and_idempotently() -> None:
    items = (_dead("a"), _dead("b", origin="celery"))
    bus = FakeBus(
        queues=(_dlq(ready=2),),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 2, items)},
    )
    reaper, store, _ = _reaper(bus=bus, config=QueueReapConfig(dead_letter_peek_limit=7))
    first = await reaper.run(PROJECT)
    assert "peek:vibey.jobs.dlq:7" in bus.calls
    assert [v.subject for v in first.acted] == ["id:a", "id:b"]
    assert all(v.action is ReapAction.PARK for v in first.acted)
    assert all("job_id" in v.detail for v in first.acted)
    assert [(item.identity, owned) for _, item, _, owned in store.parked] == [
        ("id:a", True),
        ("id:b", False),
    ], "a header naming a queue vibey does not own is never offered for replay"

    second = await reaper.run(PROJECT)
    assert second.acted == ()
    assert any("2 dead letter(s) already parked" in note for note in second.notes)
    assert "peek:vibey.jobs.dlq:9" in bus.calls, "the read reaches past the parked two"


async def test_p2_the_read_pages_past_what_is_parked_and_growth_is_recorded_again() -> None:
    """Finding 10 (P2): past the first hundred, nothing was ever parked again -- the read
    always returned the same head -- and the unread remainder's growth was never recorded.
    """
    items = tuple(_dead(f"m{i}") for i in range(150))
    bus = FakeBus(
        queues=(_dlq(ready=150),),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 150, items)},
    )
    reaper, store, _ = _reaper(bus=bus)
    first = await reaper.run(PROJECT)
    assert len(first.acted) == 100
    (unread,) = first.surfaced
    assert (unread.measured, unread.episode) == (50.0, "50")
    second = await reaper.run(PROJECT)
    assert len(second.acted) == 50
    assert len(store.parked) == 150
    assert [v.episode for v in second.cleared] == ["50"]

    grown = items + tuple(_dead(f"m{i}") for i in range(150, 330))
    bus.dead["vibey.jobs.dlq"] = DeadLetterPeek("vibey.jobs.dlq", 330, grown)
    bus.queues = (_dlq(ready=330),)
    third = await reaper.run(PROJECT)
    assert len(third.acted) == 100
    assert [v.episode for v in third.surfaced] == ["80"]
    assert [v.episode for v in store.recorded()] == ["50", "80"]


async def test_the_read_is_capped_however_much_is_parked() -> None:
    store = FakeStore(parked_identities={f"id:{i}": "vibey.jobs.dlq" for i in range(20_000)})
    bus = FakeBus(
        queues=(_dlq(ready=20_001),),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 20_001, ())},
    )
    reaper, _, _ = _reaper(store, bus)
    await reaper.run(PROJECT)
    assert f"peek:vibey.jobs.dlq:{MAX_DEAD_LETTER_READ}" in bus.calls


async def test_a_dry_run_plans_the_parks_without_making_them() -> None:
    bus = FakeBus(
        queues=(_dlq(),),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 1, (_dead("a"),))},
    )
    reaper, store, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT, dry_run=True)
    assert [v.action for v in report.acted] == [ReapAction.PARK]
    assert "park_dead_letter" not in store.calls


async def test_an_unreadable_dead_letter_queue_and_a_failed_park_are_named() -> None:
    bus = FakeBus(queues=(_dlq(),), fail={"peek:vibey.jobs.dlq:100"})
    bus.dead["vibey.jobs.dlq"] = DeadLetterPeek("vibey.jobs.dlq", 1, (_dead("a"),))
    reaper, _, _ = _reaper(bus=bus)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("dead letters on vibey.jobs.dlq: peek:vibey.jobs.dlq:100 failed",)

    reaper, _, _ = _reaper(FakeStore(fail={"parked_count"}), FakeBus(queues=(_dlq(),)))
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("dead letters on vibey.jobs.dlq: parked_count failed",)

    bus = FakeBus(
        queues=(_dlq(),),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 1, (_dead("a"),))},
    )
    reaper, _, _ = _reaper(FakeStore(fail={"park_dead_letter"}), bus)
    report = await reaper.run(PROJECT)
    assert report.unreadable == ("parking id:a from vibey.jobs.dlq: park_dead_letter failed",)
    assert report.acted == ()


async def test_a_dead_letter_queue_that_was_not_read_whole_clears_nothing() -> None:
    items = tuple(_dead(f"m{i}") for i in range(150))
    bus = FakeBus(
        queues=(_dlq(ready=150),),
        dead={"vibey.jobs.dlq": DeadLetterPeek("vibey.jobs.dlq", 150, items)},
    )
    shared = FakeStore()
    reaper, _, _ = _reaper(shared, bus)
    await reaper.run(PROJECT)
    bus.fail = {"peek:vibey.jobs.dlq:200"}
    report = await reaper.run(PROJECT)
    assert report.cleared == ()


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
    cleared = _verdict(ReapCondition.STALE_READY, ReapAction.CLEARED)
    left = QueueReapReport(
        project_id=PROJECT,
        dry_run=dry_run,
        acted=(_verdict(),),
        policy=PolicyOutcome(policy="a", verified=True),
        notes=("n1",),
        cleared=(cleared,),
    )
    right = QueueReapReport(project_id=PROJECT, dry_run=dry_run, unreadable=("u",))
    joined = left.joined(right)
    assert joined.policy == left.policy
    assert joined.acted == left.acted
    assert joined.cleared == (cleared,)
    assert joined.notes == ("n1",) and joined.unreadable == ("u",)
    assert not joined.ok
    newer = PolicyOutcome(policy="b", verified=False)
    assert left.joined(QueueReapReport(PROJECT, dry_run, policy=newer)).policy == newer
