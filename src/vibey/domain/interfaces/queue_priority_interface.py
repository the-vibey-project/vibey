# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contracts behind queue priority (ADR-0054).

Mirrors `vibey/domain/queue_priority.py` (ADR-0016). Interfaces declare; they never
consume. The domain types the seams are declared over are imported under
TYPE_CHECKING only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Iterable, Mapping
    from datetime import datetime
    from uuid import UUID

    from vibey.domain.job import StoredJobState
    from vibey.domain.phase import Phase
    from vibey.domain.queue_priority import (
        BumpPlan,
        MovedJob,
        PriorityAction,
        QueuedJob,
        UnbumpPlan,
    )


@runtime_checkable
class QueuedJobInterface(Protocol):
    """The part of a job row that decides its place in the queue."""

    @property
    def id(self) -> UUID: ...

    @property
    def state(self) -> StoredJobState: ...

    @property
    def priority(self) -> int: ...

    @property
    def run_after(self) -> datetime: ...

    @property
    def bump_seq(self) -> int | None:
        """The job's place among bumped jobs, or None when it is not bumped."""
        ...

    @property
    def depends_on(self) -> tuple[UUID, ...]: ...

    @property
    def bumped(self) -> bool: ...

    @property
    def movable(self) -> bool:
        """True while the job can still be claimed, now or after a retry or an answer."""
        ...


@runtime_checkable
class BumpPlanInterface(Protocol):
    @property
    def target(self) -> UUID: ...

    @property
    def moved(self) -> tuple[UUID, ...]:
        """Jobs to give a bump number, dependencies before what needs them."""
        ...

    @property
    def kept(self) -> tuple[UUID, ...]: ...

    @property
    def blocked_by(self) -> tuple[UUID, ...]: ...


@runtime_checkable
class UnbumpPlanInterface(Protocol):
    @property
    def target(self) -> UUID: ...

    @property
    def moved(self) -> tuple[UUID, ...]: ...


@runtime_checkable
class MovedJobInterface(Protocol):
    @property
    def job_id(self) -> UUID: ...

    @property
    def bump_seq(self) -> int | None: ...

    @property
    def previous(self) -> int | None: ...


@runtime_checkable
class PriorityChangeInterface(Protocol):
    """What a bump or an un-bump did."""

    @property
    def action(self) -> PriorityAction: ...

    @property
    def source(self) -> str: ...

    @property
    def target(self) -> UUID: ...

    @property
    def moved(self) -> tuple[MovedJob, ...]: ...

    @property
    def kept(self) -> tuple[UUID, ...]: ...

    @property
    def blocked_by(self) -> tuple[UUID, ...]: ...

    @property
    def changed(self) -> bool:
        """False for a no-op, which is recorded nowhere."""
        ...


@runtime_checkable
class PriorityRefusalInterface(Protocol):
    """A reorder request from a source with no grant, as the ledger records it."""

    @property
    def project_id(self) -> UUID: ...

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> Phase: ...

    @property
    def job_id(self) -> UUID | None: ...

    @property
    def action(self) -> PriorityAction: ...

    @property
    def source(self) -> str: ...

    @property
    def reason(self) -> str: ...


@runtime_checkable
class PriorityGrantInterface(Protocol):
    """Who may move a job ahead: the operator, and the sources declared in config."""

    @property
    def declared(self) -> frozenset[str]:
        """The sources `[queue.priority] sources` declares. Never includes the operator,
        who needs no declaration."""
        ...

    def admits(self, source: str) -> bool:
        """True for the operator and for a declared source, matched exactly."""
        ...

    def refusal(self, source: str) -> str:
        """Why `source` was refused, in words an operator can act on."""
        ...


@runtime_checkable
class ClaimOrderInterface(Protocol):
    """The claim query's ORDER BY, as a sort key over a snapshot of the queue."""

    def key(self, job: QueuedJob) -> tuple[bool, int, int, datetime, UUID]:
        """Bumped before unbumped, then bump order, priority, run_after and id."""
        ...

    def sort(self, jobs: Iterable[QueuedJob]) -> tuple[QueuedJob, ...]:
        """`jobs` in the order the claim would take them, were all claimable."""
        ...


@runtime_checkable
class BumpPlannerInterface(Protocol):
    """Decides what a bump moves: the target and every unfinished dependency."""

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> BumpPlan:
        """`jobs` holds the target and its dependencies, transitively. Raises
        `NotReorderable` for a target that is finished or in an unknown state,
        `DependencyCycle` for a ring, and `LookupError` for a job the snapshot lacks."""
        ...


@runtime_checkable
class UnbumpPlannerInterface(Protocol):
    """Decides what an un-bump moves: the target and every bumped job needing it."""

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> UnbumpPlan:
        """`jobs` holds the target and every job depending on it, transitively.
        Raises `NotReorderable` for a finished or unknown target and `LookupError`
        for a target the snapshot lacks."""
        ...
