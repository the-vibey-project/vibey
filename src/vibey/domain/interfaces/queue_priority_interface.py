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
        PriorityContext,
        PriorityDecision,
        QueuedJob,
        UnbumpPlan,
    )


@runtime_checkable
class CallerInterface(Protocol):
    """The account a request runs as."""

    @property
    def uid(self) -> int: ...

    @property
    def name(self) -> str:
        """From the password database, never the environment."""
        ...


@runtime_checkable
class PriorityDecisionInterface(Protocol):
    @property
    def admitted(self) -> bool: ...

    @property
    def principal(self) -> str:
        """`operator:NAME`, `source:NAME` or `account:NAME`: who asked."""
        ...

    @property
    def reason(self) -> str:
        """Why it was refused; empty when admitted."""
        ...


@runtime_checkable
class PriorityGrantInterface(Protocol):
    """Who may reorder a project's queue: the account owning its reviewed
    configuration, and the sources that configuration declares, run by that account."""

    @property
    def declared(self) -> frozenset[str]: ...

    @property
    def anchor(self) -> str:
        """The reviewed configuration whose owner is the operator, as a path."""
        ...

    def decide(self, source: str | None, caller: CallerInterface) -> PriorityDecision:
        """No source: admitted only when `caller` owns the anchor. A source: admitted
        only when declared AND `caller` owns the anchor."""
        ...


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
    def bump_origin(self) -> UUID | None:
        """The job whose bump moved this one."""
        ...

    @property
    def phase_known(self) -> bool: ...

    @property
    def bumped(self) -> bool: ...

    @property
    def movable(self) -> bool:
        """True while the job can still be claimed, now or after a retry or an answer."""
        ...

    @property
    def named(self) -> bool:
        """Bumped by name, rather than pulled forward for another job."""
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
    def named(self) -> bool: ...


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
    def requested_by(self) -> str: ...

    @property
    def target(self) -> UUID: ...

    @property
    def moved(self) -> tuple[MovedJob, ...]: ...

    @property
    def kept(self) -> tuple[UUID, ...]: ...

    @property
    def named(self) -> bool: ...

    @property
    def note(self) -> str: ...

    @property
    def changed(self) -> bool:
        """False for a request that moved nothing. It is recorded all the same."""
        ...


@runtime_checkable
class PriorityContextInterface(Protocol):
    @property
    def project_id(self) -> UUID: ...

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> Phase: ...

    @property
    def requested_by(self) -> str: ...


@runtime_checkable
class PriorityRefusalInterface(Protocol):
    """A refused reorder request, as the ledger records it."""

    @property
    def context(self) -> PriorityContext: ...

    @property
    def job_id(self) -> UUID | None: ...

    @property
    def action(self) -> PriorityAction: ...

    @property
    def reason(self) -> str: ...


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

    def plan(
        self, target: UUID, jobs: Mapping[UUID, QueuedJob], *, finished_ok: bool = False
    ) -> BumpPlan:
        """`jobs` holds the target and its unfinished dependencies, transitively, with
        the finished ones they name. Raises `NotReorderable` for a finished or unknown
        target (unless `finished_ok`, which makes a finished target a no-op),
        `DependencyCannotFinish` for a failed, cancelled or unknown dependency,
        `DependencyCycle` for a ring, and `LookupError` for a job the snapshot lacks."""
        ...


@runtime_checkable
class UnbumpPlannerInterface(Protocol):
    """Decides what an un-bump moves: exactly what the target's bump moved."""

    def plan(self, target: UUID, jobs: Mapping[UUID, QueuedJob]) -> UnbumpPlan:
        """`jobs` holds the target and every unfinished job of its project. Raises
        `NotReorderable` for a finished or unknown target, `DependentsStillBumped` while
        a bumped job needs it, and `LookupError` for a target the snapshot lacks."""
        ...
