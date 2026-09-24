# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Queue reaping's seams (ADR-0056): what reads the broker, what reaps and records against
PostgreSQL, and the one service every entry point reaps through.

Mirrors `vibey/application/queue_reaper.py` (ADR-0016). Interfaces declare; they never
consume.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import HumanGateRequest, JobRecord, QueueReapReport
from vibey.application.interfaces.queue import JobHandler, Outcome
from vibey.domain.interfaces.queue_reap_interface import BrokerPolicyInterface
from vibey.domain.queue_reap import (
    DeadLetter,
    DeadLetterPeek,
    PolicyOutcome,
    QueueDepth,
    ReapVerdict,
)


@runtime_checkable
class BusInspectorPort(Protocol):
    """Reads a broker without taking anything off it, and reconciles vibey's policy onto it.

    Every read is a measurement; none consumes a message. The in-memory bus and the
    RabbitMQ management API implement it with the same semantics.
    """

    async def depths(self) -> tuple[QueueDepth, ...]:
        """Every queue on the vhost, measured once. `owned` and `dead_letter` are left
        False: whether vibey owns a queue is the policy's call, not the broker's."""
        ...

    async def peek_dead_letters(self, queue: str, *, limit: int) -> DeadLetterPeek:
        """Up to `limit` messages off the head of `queue`, each returned to it: read,
        never removed. The peek says how deep the queue was, so a partial read reports
        itself as partial."""
        ...

    async def apply_policy(self, policy: BrokerPolicyInterface) -> PolicyOutcome:
        """Write the policy, then read it back. `verified` is the read-back, never the
        write's status code (12.e)."""
        ...


@runtime_checkable
class QueueReapStore(Protocol):
    """The PostgreSQL side of reaping: the job queue's leases, its ready work, and the
    parked jobs dead letters become. Every write is one transaction with its ledger
    event, so a reap and its record never part."""

    async def preview_leases(self) -> tuple[ReapVerdict, ...]:
        """Every expired lease, judged, with nothing written: a dry run."""
        ...

    async def reap_leases(self) -> tuple[ReapVerdict, ...]:
        """Every expired lease, judged and acted on: requeued while attempts remain,
        parked with a `delivery_exhausted` gate once they are spent. Each verdict returned
        was written and recorded in the same transaction."""
        ...

    async def ready_depths(self, project_id: UUID) -> tuple[QueueDepth, ...]:
        """The project's job queue, for (d): how much claimable work waits, and how long
        the oldest of it has been claimable. Empty when nothing is claimable."""
        ...

    async def park_dead_letter(
        self, project_id: UUID, item: DeadLetter, verdict: ReapVerdict
    ) -> UUID | None:
        """Park one dead letter as a job with a `human_gate` row, and record the verdict,
        in one transaction. The job id, or None when this identity is already parked."""
        ...

    async def record(self, project_id: UUID, verdict: ReapVerdict) -> None:
        """Record a verdict that moved nothing (a surfaced condition)."""
        ...


@runtime_checkable
class QueueReaperInterface(Protocol):
    """Runs one reaper pass over the job queue and the broker."""

    async def run(
        self, project_id: UUID, *, dry_run: bool = False, leases: bool = True
    ) -> QueueReapReport:
        """One pass. Ready work and broker verdicts are judged for, and recorded under,
        `project_id`; a lease verdict is recorded under its own job's project. `leases=False`
        skips the lease reap for a caller that has just run it. A dry run judges
        everything and writes nothing -- not even the broker policy."""
        ...

    async def run_if_due(self, project_id: UUID) -> QueueReapReport | None:
        """A pass without the lease reap, at most once per `[queue.reap] interval_seconds`
        per process; None when it was not due, or reaping is switched off."""
        ...


@runtime_checkable
class DeliveryExhaustedGateInterface(Protocol):
    """The gate a lease reap raises when a job's attempts are spent."""

    def request(self, *, kind: str, verdict: ReapVerdict) -> HumanGateRequest: ...


@runtime_checkable
class BusDeadLetterGateInterface(Protocol):
    """The gate a parked dead letter carries."""

    def request(self, payload: Mapping[str, object], *, note: str = "") -> HumanGateRequest:
        """What died, where and why, and the answers that settle it: `replay` only when
        the body is a whole JSON object, `dismiss` always."""
        ...


@runtime_checkable
class BusDeadLetterHandlerInterface(JobHandler, Protocol):
    """Settles a parked `bus.dead_letter` job by its gate's answer."""

    async def handle(self, job: JobRecord) -> Outcome: ...
