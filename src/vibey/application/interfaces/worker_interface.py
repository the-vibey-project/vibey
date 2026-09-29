# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The contract for driving the queue one job at a time (ADR-0016's mirrored seam
for `vibey.application.worker`)."""

from typing import Protocol, runtime_checkable
from uuid import UUID


@runtime_checkable
class WorkerLoopInterface(Protocol):
    """Claims, runs and settles jobs; holds no durable state of its own."""

    async def run_once(self, project_id: UUID) -> bool:
        """Claim and execute at most one job. False if nothing was claimable.

        True once a job was claimed, whether or not its settle landed: a
        settle the queue refused because the lease was lost is logged, never
        raised, so one lost job cannot stop the loop that drives the rest.
        """
        ...


@runtime_checkable
class MultiProjectWorkerInterface(Protocol):
    """Serves every project with claimable work through each project's own loops (#1189)."""

    @property
    def last_served(self) -> UUID | None:
        """The project whose job this worker last ran, or None before the first."""
        ...

    async def run_once(self, slot: int = 0) -> bool:
        """Run at most one job, from the first project in claim order whose own loop
        claims one. `slot` picks which of that project's loops runs it, so parallel drive
        loops never share one. False when no project had anything this worker could claim.
        """
        ...
