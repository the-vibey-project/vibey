# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The queue reaper: one pass over everything a queue guards (ADR-0056).

A pass, in order:

1. **Leases** on the PostgreSQL job queue: every expired lease is judged by
   `QueueReapPolicy` and requeued while attempts remain, or parked with a
   `delivery_exhausted` gate once they are spent -- each in one transaction with its
   `QueueReaped` event (`QueueReapStore.reap_leases`). The worker's idle loop already
   reaps leases through `JobRepository.reap()`, which is the same code, so it asks for a
   pass without them.
2. **Ready work** on the job queue that has waited past `stale_ready_seconds`: surfaced.
3. **The broker**, when one is configured: vibey's policy is reconciled onto the queues
   it owns and read back; every queue is measured; an owned dead-letter queue's messages
   each become a parked job and a `human_gate` row; everything else stuck is surfaced.
   A queue vibey does not own -- Plane's Celery queues on the shared broker -- is only
   ever measured and surfaced, never touched.

A source that cannot be read is named in the report and nothing is concluded from it;
the pass carries on with the rest and is not `ok` (10.f, 12.e). A surfaced condition is
recorded once when it is first seen and again only after it has cleared, so a queue
stuck for an hour is one event, not sixty. A dry run judges everything and writes
nothing, not even the broker policy.
"""

from dataclasses import replace
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
from vibey.domain.interfaces.config_interface import QueueReapConfigInterface
from vibey.domain.interfaces.queue_reap_interface import QueueReapPolicyInterface
from vibey.domain.queue_reap import (
    QUEUE_REAP_POLICY,
    QueueDepth,
    ReapAction,
    ReapThresholds,
    ReapVerdict,
)

type _SurfaceKey = tuple[UUID, str, str, str]

DELIVERY_EXHAUSTED_GATE_KIND: Final = "delivery_exhausted"


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
        self._surfaced: set[_SurfaceKey] = set()
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
        report = QueueReapReport(project_id=project_id, dry_run=dry_run)
        if leases:
            report = report.joined(await self._leases(report))
        report = report.joined(await self._ready(report, thresholds))
        if self._bus is None:
            report = report.joined(
                replace(
                    self._empty(report),
                    notes=(
                        "broker: none configured ([bus] url, username, password); only the "
                        "PostgreSQL job queue was reaped",
                    ),
                )
            )
        else:
            report = report.joined(await self._broker(report, self._bus, thresholds))
        if not dry_run:
            report = report.joined(await self._record_surfaced(report))
        self._log_report(report)
        return report

    @staticmethod
    def _empty(like: QueueReapReport) -> QueueReapReport:
        return QueueReapReport(project_id=like.project_id, dry_run=like.dry_run)

    async def _leases(self, like: QueueReapReport) -> QueueReapReport:
        try:
            if like.dry_run:
                verdicts = await self._store.preview_leases()
            else:
                verdicts = await self._store.reap_leases()
        except Exception as exc:
            return replace(self._empty(like), unreadable=(f"job-queue leases: {exc}",))
        return replace(self._empty(like), acted=verdicts)

    async def _ready(self, like: QueueReapReport, thresholds: ReapThresholds) -> QueueReapReport:
        try:
            depths = await self._store.ready_depths(like.project_id)
        except Exception as exc:
            return replace(self._empty(like), unreadable=(f"job-queue ready work: {exc}",))
        surfaced = tuple(
            verdict
            for depth in depths
            for verdict in self._policy.judge_queue(depth, thresholds=thresholds)
        )
        return replace(self._empty(like), surfaced=surfaced)

    async def _broker(
        self, like: QueueReapReport, bus: BusInspectorPort, thresholds: ReapThresholds
    ) -> QueueReapReport:
        part = self._empty(like)
        policy = self._config.broker_policy()
        if like.dry_run:
            part = replace(
                part, notes=(f"broker policy {policy.name!r}: not reconciled in a dry run",)
            )
        else:
            try:
                part = replace(part, policy=await bus.apply_policy(policy))
            except Exception as exc:
                part = replace(part, unreadable=(f"broker policy {policy.name!r}: {exc}",))
        try:
            measured = await bus.depths()
        except Exception as exc:
            return part.joined(replace(self._empty(like), unreadable=(f"broker queues: {exc}",)))
        for raw in measured:
            depth = replace(
                raw, owned=policy.owns(raw.queue), dead_letter=policy.is_dead_letter(raw.queue)
            )
            for verdict in self._policy.judge_queue(depth, thresholds=thresholds):
                if verdict.action is ReapAction.PARK:
                    part = part.joined(await self._dead_letters(like, bus, depth, thresholds))
                else:
                    part = part.joined(replace(self._empty(like), surfaced=(verdict,)))
        return part

    async def _dead_letters(
        self,
        like: QueueReapReport,
        bus: BusInspectorPort,
        depth: QueueDepth,
        thresholds: ReapThresholds,
    ) -> QueueReapReport:
        try:
            peek = await bus.peek_dead_letters(
                depth.queue, limit=self._config.dead_letter_peek_limit
            )
        except Exception as exc:
            return replace(self._empty(like), unreadable=(f"dead letters on {depth.queue}: {exc}",))
        unread = self._policy.judge_unread(peek)
        acted: list[ReapVerdict] = []
        unreadable: list[str] = []
        already = 0
        for item in peek.items:
            verdict = self._policy.judge_dead_letter(item, depth, thresholds=thresholds)
            if like.dry_run:
                acted.append(verdict)
                continue
            try:
                parked = await self._store.park_dead_letter(like.project_id, item, verdict)
            except Exception as exc:
                unreadable.append(f"parking {item.identity} from {depth.queue}: {exc}")
                continue
            if parked is None:
                already += 1
            else:
                acted.append(replace(verdict, detail={**verdict.detail, "job_id": str(parked)}))
        notes = (
            (
                f"{depth.queue}: {already} dead letter(s) already parked; each stays on the "
                "queue as evidence until a person clears it",
            )
            if already
            else ()
        )
        return replace(
            self._empty(like),
            acted=tuple(acted),
            surfaced=(unread,) if unread is not None else (),
            notes=notes,
            unreadable=tuple(unreadable),
        )

    async def _record_surfaced(self, report: QueueReapReport) -> QueueReapReport:
        seen: set[_SurfaceKey] = set()
        unreadable: list[str] = []
        for verdict in report.surfaced:
            key = (report.project_id, verdict.queue, verdict.condition.value, verdict.subject)
            if key in self._surfaced:
                seen.add(key)
                continue
            try:
                await self._store.record(report.project_id, verdict)
            except Exception as exc:
                unreadable.append(f"recording {verdict.condition.value} on {verdict.queue}: {exc}")
                continue
            seen.add(key)
        # A condition that cleared is forgotten, so its return is recorded again -- but
        # only when every source was read: an unread source says nothing about clearing.
        whole = not report.unreadable and not unreadable
        self._surfaced = seen if whole else self._surfaced | seen
        return replace(self._empty(report), unreadable=tuple(unreadable))

    def _log_report(self, report: QueueReapReport) -> None:
        project = str(report.project_id)
        for verdict in report.acted:
            event = "queue.reap_planned" if report.dry_run else "queue.reaped"
            self._log.warning(event, project_id=project, **verdict.payload())
        for verdict in report.surfaced:
            self._log.warning("queue.stuck", project_id=project, **verdict.payload())
        for source in report.unreadable:
            self._log.warning("queue.reap_unreadable", project_id=project, source=source)
        if report.policy is not None and not report.policy.verified:
            self._log.warning(
                "queue.reap_policy_unverified",
                policy=report.policy.policy,
                detail=report.policy.detail,
            )
