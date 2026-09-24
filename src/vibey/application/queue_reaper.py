# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queue reaper: one pass over everything a queue guards (ADR-0056).

A pass, in order:

1. **Leases** on the PostgreSQL job queue: every expired lease is judged by
   `QueueReapPolicy` and requeued while attempts remain, or parked with a
   `delivery_exhausted` gate once they are spent -- each lease in a transaction of its own
   with its `QueueReaped` event (`QueueReapStore.reap_leases`). The worker's idle loop
   already reaps leases through `JobRepository.reap()`, which is the same code, so it asks
   for a pass without them.
2. **Claimable, unclaimed work** on the job queue, in every project -- a project with no
   worker at all included -- that has waited past `stale_ready_seconds`: surfaced.
3. **The broker**, when one is configured: vibey's policies are reconciled onto the queues
   it owns and read back, off the queues themselves; every queue is measured; an owned
   dead-letter queue's messages each become a parked job and a `human_gate` row; everything
   else stuck is surfaced. A queue vibey does not own -- Plane's Celery queues on the shared
   broker -- is only ever measured and surfaced, never touched.

**A sighting is recorded once, fleet-wide** (#1108 review finding 4). The ledger, not the
process, holds it open: before a surfaced condition is recorded, the latest `QueueReaped`
event for the same sighting is read, and if it is still open nothing is written. Every pod
and every `vibey queue reap` sees the same ledger, so two pods and the CLI record one
event, not three. When a pass that read the source whole no longer sees an open sighting,
it records it `cleared`, so the condition's return is a new sighting. A broker sighting
is recorded once for the whole fleet, under the project the pass ran for, and is
`untrusted`: the broker's names are not vibey's words.

A source that cannot be read is named in the report and nothing is concluded from it --
no sighting it would have shown is cleared -- and the pass is not `ok` (10.f, 12.e). A dry
run judges everything and writes nothing, not even the broker policy.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import Final
from uuid import UUID

from vibey.application.dto import HumanGateRequest, QueueReapReport
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.queue_reap import (
    BusInspectorPort,
    DeliveryExhaustedGateInterface,
    QueueReapStore,
)
from vibey.application.interfaces.system import Clock
from vibey.domain.errors import LeaseReapIncomplete
from vibey.domain.interfaces.config_interface import QueueReapConfigInterface
from vibey.domain.interfaces.queue_reap_interface import (
    BrokerPolicyInterface,
    QueueReapPolicyInterface,
)
from vibey.domain.job import DELIVERY_EXHAUSTED_GATE_KIND
from vibey.domain.queue_reap import (
    QUEUE_REAP_POLICY,
    PolicyOutcome,
    QueueDepth,
    ReapAction,
    ReapSource,
    ReapThresholds,
    ReapVerdict,
)

MAX_DEAD_LETTER_READ: Final = 10_000
"""The most dead letters one pass reads off one queue: the ones already parked, which a
read cannot skip because they sit at the head, plus `dead_letter_peek_limit` new ones."""


class DeliveryExhaustedGate:
    """The gate a lease reap raises when a job's attempts are spent (ADR-0044 §8)."""

    def request(self, *, kind: str, verdict: ReapVerdict) -> HumanGateRequest:
        return HumanGateRequest(
            kind=DELIVERY_EXHAUSTED_GATE_KIND,
            prompt=(
                f"job {kind!r} ({verdict.subject}) was handed out {int(verdict.measured)} "
                f"time(s), its limit of {int(verdict.threshold)}, and each time its worker "
                "stopped without settling it: no ack, no nack, and no heartbeat before the "
                "lease ran out. Nothing retries it on its own. Answer anything to deliver it "
                "once more -- one attempt is refunded -- or fix what kills its worker first."
            ),
        )


DELIVERY_EXHAUSTED_GATE: Final[DeliveryExhaustedGateInterface] = DeliveryExhaustedGate()


@dataclass(slots=True)
class _Pass:
    """What one pass has found so far, and which sources it read whole."""

    report: QueueReapReport
    project_of: dict[str, UUID] = field(default_factory=dict)
    """Each job-queue verdict's queue, to the project it is recorded under."""
    job_queue_read: bool = False
    broker_read: bool = False
    unmeasured: set[str] = field(default_factory=set)
    """Broker queues this pass could not judge whole: none of their sightings clear."""

    def add(
        self,
        *,
        acted: tuple[ReapVerdict, ...] = (),
        surfaced: tuple[ReapVerdict, ...] = (),
        cleared: tuple[ReapVerdict, ...] = (),
        policy: PolicyOutcome | None = None,
        notes: tuple[str, ...] = (),
        unreadable: tuple[str, ...] = (),
    ) -> None:
        self.report = self.report.joined(
            QueueReapReport(
                project_id=self.report.project_id,
                dry_run=self.report.dry_run,
                acted=acted,
                surfaced=surfaced,
                cleared=cleared,
                policy=policy,
                notes=notes,
                unreadable=unreadable,
            )
        )


class QueueReaper:
    """Reaps the job queue and the broker by measurement, and records every reap."""

    def __init__(
        self,
        *,
        store: QueueReapStore,
        bus: BusInspectorPort | None,
        config: QueueReapConfigInterface,
        clock: Clock,
        logger: Logger,
        policy: QueueReapPolicyInterface = QUEUE_REAP_POLICY,
    ) -> None:
        self._store = store
        self._bus = bus
        self._config = config
        self._clock = clock
        self._log = logger
        self._policy = policy
        self._last_pass: datetime | None = None

    async def run_if_due(self, project_id: UUID) -> QueueReapReport | None:
        if not self._config.enabled:
            return None
        now = self._clock.now()
        last = self._last_pass
        if last is not None and (now - last).total_seconds() < self._config.interval_seconds:
            return None
        # Claimed before the first await, so the worker's parallel drive loops that share
        # this reaper cannot both find it due.
        self._last_pass = now
        return await self.run(project_id, leases=False)

    async def run(
        self, project_id: UUID, *, dry_run: bool = False, leases: bool = True
    ) -> QueueReapReport:
        thresholds = self._config.thresholds()
        found = _Pass(QueueReapReport(project_id=project_id, dry_run=dry_run))
        if leases:
            await self._leases(found)
        await self._ready(found, thresholds)
        if self._bus is None:
            found.add(
                notes=(
                    "broker: none configured ([bus] url, username, password); only the "
                    "PostgreSQL job queue was reaped",
                )
            )
        else:
            await self._broker(found, self._bus, thresholds)
        if not dry_run:
            await self._record(found)
        self._log_report(found.report)
        return found.report

    async def _leases(self, found: _Pass) -> None:
        try:
            if found.report.dry_run:
                verdicts = await self._store.preview_leases()
            else:
                verdicts = await self._store.reap_leases()
        except LeaseReapIncomplete as exc:
            found.add(
                acted=tuple(v for v in exc.reaped if isinstance(v, ReapVerdict)),
                unreadable=tuple(f"job-queue lease {failure}" for failure in exc.failures),
            )
            return
        except Exception as exc:
            found.add(unreadable=(f"job-queue leases: {exc}",))
            return
        found.add(acted=verdicts)

    async def _ready(self, found: _Pass, thresholds: ReapThresholds) -> None:
        try:
            measured = await self._store.ready_depths()
        except Exception as exc:
            found.add(unreadable=(f"job-queue claimable work: {exc}",))
            return
        found.job_queue_read = True
        for project, depth in measured:
            found.project_of[depth.queue] = project
            found.add(surfaced=self._policy.judge_queue(depth, thresholds=thresholds))

    async def _broker(
        self, found: _Pass, bus: BusInspectorPort, thresholds: ReapThresholds
    ) -> None:
        policy = self._config.broker_policy()
        if found.report.dry_run:
            found.add(notes=(f"broker policy {policy.name!r}: not reconciled in a dry run",))
        else:
            try:
                found.add(policy=await bus.apply_policy(policy))
            except Exception as exc:
                found.add(unreadable=(f"broker policy {policy.name!r}: {exc}",))
        try:
            measured = await bus.depths()
        except Exception as exc:
            found.add(unreadable=(f"broker queues: {exc}",))
            return
        found.broker_read = True
        for raw in measured:
            depth = replace(
                raw, owned=policy.owns(raw.queue), dead_letter=policy.is_dead_letter(raw.queue)
            )
            if (
                not depth.dead_letter
                and depth.ready > 0
                and depth.consumers == 0
                and depth.oldest_ready_age_seconds is None
            ):
                # 10.f: unmeasured is not old, and not silently fine either (finding 12).
                found.add(
                    notes=(
                        f"{depth.queue}: {depth.ready} ready with no consumer, age not "
                        f"measurable (a {depth.kind or 'queue'} whose head message carries "
                        "no timestamp the broker reports; quorum queues report none)",
                    )
                )
            for verdict in self._policy.judge_queue(depth, thresholds=thresholds):
                if verdict.action is ReapAction.PARK:
                    await self._dead_letters(found, bus, depth, thresholds, policy)
                else:
                    found.add(surfaced=(verdict,))

    async def _dead_letters(
        self,
        found: _Pass,
        bus: BusInspectorPort,
        depth: QueueDepth,
        thresholds: ReapThresholds,
        policy: BrokerPolicyInterface,
    ) -> None:
        try:
            parked = await self._store.parked_count(depth.queue)
            # Messages a read returns go back to where they were, so the parked ones stay
            # at the head: the read reaches past them to the next unparked (finding 10).
            limit = min(parked + self._config.dead_letter_peek_limit, MAX_DEAD_LETTER_READ)
            peek = await bus.peek_dead_letters(depth.queue, limit=limit)
        except Exception as exc:
            found.unmeasured.add(depth.queue)
            found.add(unreadable=(f"dead letters on {depth.queue}: {exc}",))
            return
        unread = self._policy.judge_unread(peek)
        if unread is not None:
            found.add(surfaced=(unread,))
        already = 0
        for item in peek.items:
            verdict = self._policy.judge_dead_letter(item, depth, thresholds=thresholds)
            if found.report.dry_run:
                found.add(acted=(verdict,))
                continue
            try:
                job_id = await self._store.park_dead_letter(
                    found.report.project_id,
                    item,
                    verdict,
                    origin_owned=policy.owns(item.origin_queue),
                )
            except Exception as exc:
                found.unmeasured.add(depth.queue)
                found.add(unreadable=(f"parking {item.identity} from {depth.queue}: {exc}",))
                continue
            if job_id is None:
                already += 1
            else:
                found.add(
                    acted=(replace(verdict, detail={**verdict.detail, "job_id": str(job_id)}),)
                )
        if already:
            found.add(
                notes=(
                    f"{depth.queue}: {already} dead letter(s) already parked; each stays on "
                    "the queue as evidence until a person clears it",
                )
            )

    async def _record(self, found: _Pass) -> None:
        """Record each sighting once, fleet-wide, and close the ones that cleared."""
        report = found.report
        seen = {verdict.sighting for verdict in report.surfaced}
        unreadable: list[str] = []
        for verdict in report.surfaced:
            project = (
                found.project_of.get(verdict.queue, report.project_id)
                if verdict.source is ReapSource.JOB_QUEUE
                else report.project_id
            )
            try:
                await self._store.record_sighting(project, verdict)
            except Exception as exc:
                unreadable.append(f"recording {verdict.condition.value} on {verdict.queue}: {exc}")
        cleared: list[ReapVerdict] = []
        try:
            open_sightings = await self._store.open_sightings()
        except Exception as exc:
            unreadable.append(f"open sightings: {exc}")
            open_sightings = ()
        for project, sighting in open_sightings:
            if sighting.sighting in seen or not self._read_whole(found, sighting):
                continue
            try:
                if await self._store.record_cleared(project, sighting):
                    cleared.append(sighting.cleared())
            except Exception as exc:
                unreadable.append(f"clearing {sighting.condition.value} on {sighting.queue}: {exc}")
        found.add(cleared=tuple(cleared), unreadable=tuple(unreadable))

    @staticmethod
    def _read_whole(found: _Pass, sighting: ReapVerdict) -> bool:
        """Whether this pass read the source a sighting came from whole: only then does
        not seeing it mean it cleared."""
        if sighting.source is ReapSource.JOB_QUEUE:
            return found.job_queue_read
        return found.broker_read and sighting.queue not in found.unmeasured

    def _log_report(self, report: QueueReapReport) -> None:
        project = str(report.project_id)
        for verdict in report.acted:
            event = "queue.reap_planned" if report.dry_run else "queue.reaped"
            self._log.warning(event, project_id=project, **verdict.payload())
        for verdict in report.surfaced:
            self._log.warning("queue.stuck", project_id=project, **verdict.payload())
        for verdict in report.cleared:
            self._log.info("queue.unstuck", project_id=project, **verdict.payload())
        for source in report.unreadable:
            self._log.warning("queue.reap_unreadable", project_id=project, source=source)
        if report.policy is not None and not report.policy.verified:
            self._log.warning(
                "queue.reap_policy_unverified",
                policy=report.policy.policy,
                detail=report.policy.detail,
            )
