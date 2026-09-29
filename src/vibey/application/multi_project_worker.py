# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""One worker for every project (#1189).

`vibey worker` used to serve one project, so work queued in any other project waited for
a person to start a worker for it. This serves them all without a second claim path: it
asks the queue which projects have claimable work, in the claim's own order, and hands
each to the very `WorkerLoop` a single-project worker would build for it, which claims
through `JobRepository.claim` as it always has. Every per-project rule -- budgets, the
Sabbath, capacity circuits, the priority lane, phase gates, engine selection -- therefore
holds unchanged, because nothing here decides any of them.

A project's loops are built the first time it has work, once, and kept. A project whose
loops cannot be built is refused for the life of the worker and said so; it never stops
the worker serving the others.
"""

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from uuid import UUID

from vibey.application.interfaces import Logger
from vibey.application.interfaces.worker_interface import WorkerLoopInterface
from vibey.application.observability import StandardLibraryLogger
from vibey.application.ports import JobRepository

ProjectLoops = Callable[[UUID], Awaitable[Sequence[WorkerLoopInterface] | None]]
"""Builds a project's loops, one per slot, or None when the project cannot be served."""


class MultiProjectWorker:
    """Declared by `interfaces/worker_interface.py::MultiProjectWorkerInterface`."""

    def __init__(
        self,
        *,
        jobs: JobRepository,
        loops_for: ProjectLoops,
        logger: Logger | None = None,
    ) -> None:
        self._jobs = jobs
        self._loops_for = loops_for
        self._log: Logger = logger if logger is not None else StandardLibraryLogger(__name__)
        self._built: dict[UUID, Sequence[WorkerLoopInterface] | None] = {}
        self._building: dict[UUID, asyncio.Lock] = {}
        self._last_served: UUID | None = None

    @property
    def last_served(self) -> UUID | None:
        return self._last_served

    async def run_once(self, slot: int = 0) -> bool:
        for project_id in await self._jobs.claimable_projects():
            loops = await self._loops(project_id)
            if not loops:
                continue
            if await loops[slot % len(loops)].run_once(project_id):
                self._last_served = project_id
                return True
        return False

    async def _loops(self, project_id: UUID) -> Sequence[WorkerLoopInterface] | None:
        # Parallel drive loops can meet the same new project at once; the lock makes the
        # second wait for the first's build instead of preflighting the engines twice.
        async with self._building.setdefault(project_id, asyncio.Lock()):
            if project_id not in self._built:
                self._built[project_id] = await self._build(project_id)
        return self._built[project_id]

    async def _build(self, project_id: UUID) -> Sequence[WorkerLoopInterface] | None:
        try:
            loops = await self._loops_for(project_id)
        except Exception as exc:  # noqa: BLE001 - one project's setup never stops the rest
            self._log.error("worker.project_refused", project_id=str(project_id), error=str(exc))
            return None
        if not loops:
            self._log.warning("worker.project_refused", project_id=str(project_id))
            return None
        return loops
