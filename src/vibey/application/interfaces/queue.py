# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The durable job queue and the handler seam a worker drives."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import (
    EnqueueRequest,
    HumanGateRequest,
    JobRecord,
)
from vibey.domain.engine import EngineId
from vibey.domain.job import FailureClass, StoredJobState
from vibey.domain.phase import Phase


@dataclass(frozen=True, slots=True)
class Success:
    result: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Failure:
    failure_class: FailureClass
    detail: str


@dataclass(frozen=True, slots=True)
class Park:
    request: HumanGateRequest


@dataclass(frozen=True, slots=True)
class Defer:
    retry_at: datetime
    detail: str
    capacity: bool = False
    """True only when the deferral is a real engine capacity signal.
    Caught live: verify-repair waits are also Defers, and recording them
    as capacity rejections opened both engines' circuits and stalled the
    whole project. Only a capacity-classed Defer may open a circuit."""


# What a handler is allowed to say happened. Part of the JobHandler seam's
# vocabulary, so it lives beside the Protocol rather than in the worker that
# interprets it -- otherwise the seam imports its own consumer.
Outcome = Success | Failure | Park | Defer


@runtime_checkable
class JobHandler(Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class JobHandlerFactory(Protocol):
    """Builds a handler per claimed job, for kinds whose collaborators are
    job-scoped: BUILD handlers need worktree/integration managers bound to
    `job.cycle` and (later) an engine selected per attempt, so a single
    handler instance constructed at worker start cannot serve them."""

    async def create(self, job: JobRecord) -> JobHandler: ...


@runtime_checkable
class JobReadyNotifier(Protocol):
    async def wait_for_job_ready(self, project_id: UUID, *, timeout: timedelta) -> bool:
        """Blocks until a job-ready notification arrives or timeout elapses.
        Returns True if notified, False on timeout (the poll fallback)."""
        ...


@runtime_checkable
class JobRepository(Protocol):
    async def enqueue(self, request: EnqueueRequest) -> JobRecord:
        """Idempotent: a second enqueue with the same (project_id,
        idempotency_key) returns the existing row rather than creating a
        duplicate."""
        ...

    async def enqueue_batch(self, requests: Sequence[EnqueueRequest]) -> tuple[JobRecord, ...]:
        """All-or-nothing `enqueue`: every request commits in ONE transaction,
        or none does, so a crash part-way through leaves nothing behind.

        Each request is idempotent exactly as `enqueue` is, so replaying a
        batch returns the rows it already made rather than duplicating them.
        Requests are processed in order; a request's `depends_on_keys` may
        name an earlier request of the batch or a job already enqueued, and a
        key that names neither raises LookupError and rolls the batch back.
        Returns one record per request, in request order."""
        ...

    async def list_for_cycle(
        self, project_id: UUID, *, cycle: int, kind: str
    ) -> tuple[JobRecord, ...]:
        """Every job of `kind` in this project's `cycle`, whatever its state,
        oldest first."""
        ...

    async def claim(self, project_id: UUID, *, owner: str, lease: timedelta) -> JobRecord | None:
        """Claims the highest-priority ready job whose dependencies have all
        succeeded, or None if there is nothing claimable right now.

        Only a job in a phase this vibey knows, of a project in a phase this vibey
        knows, is claimable (vibey#287): a phase a newer vibey added is left for a
        worker that knows what it means, never guessed at."""
        ...

    async def heartbeat(self, job_id: UUID, *, owner: str, lease: timedelta) -> bool: ...

    async def ack(self, job_id: UUID, *, owner: str) -> bool: ...

    async def nack(self, job_id: UUID, *, owner: str, error: Mapping[str, object]) -> bool: ...

    async def defer(
        self,
        job_id: UUID,
        *,
        owner: str,
        retry_at: datetime,
        error: Mapping[str, object],
    ) -> bool:
        """Releases a capacity-blocked lease without consuming a failure attempt."""
        ...

    async def park(self, job_id: UUID, *, owner: str) -> bool:
        """Marks the job awaiting_human and releases its lease immediately,
        without counting as a failure attempt."""
        ...

    async def grant_attempts(self, job_id: UUID, *, owner: str, max_attempts: int) -> bool:
        """Durably widens this job's attempt bound to a human's grant.

        ADR-0024: a bounded ladder ends in a park that can grant more. The
        grant has to reach the row, because `nack` decides 'failed' from the
        row's own `max_attempts` -- a grant that lived only in the answered
        gate would be spent by the very next nack. Lease-guarded like every
        other write, and it never narrows: a value at or below the current
        bound is a no-op returning False.
        """
        ...

    async def reap(self) -> int:
        """Reclaims jobs whose lease has expired. Returns the count
        reclaimed."""
        ...

    async def assign_engine(self, job_id: UUID, *, owner: str, engine_id: EngineId) -> bool:
        """Durably records which engine this attempt selected. Guarded by the
        lease so a zombie worker whose lease expired (and whose job was
        reclaimed by someone else) can never overwrite the new owner's
        selection. On a retry, the previous attempt's value is the
        "previous engine" input to forced-rotation exclusion."""
        ...

    async def count_unsettled(
        self, project_id: UUID, *, cycle: int, phase: Phase, exclude: UUID | None = None
    ) -> int:
        """Counts this cycle+phase's jobs not yet in a terminal state
        (succeeded/failed/cancelled). `exclude` lets the caller ask "am I the
        last one?" from inside its own still-leased job."""
        ...

    async def queue_depth(self, project_id: UUID) -> Mapping[StoredJobState, int]:
        """Returns the number of jobs by state for the given project. Every
        `JobState` member is present; a state a newer vibey added is counted under
        its stored name (vibey#287)."""
        ...

    async def get(self, job_id: UUID) -> JobRecord | None: ...
