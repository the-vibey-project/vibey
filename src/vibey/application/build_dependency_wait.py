# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""An item that builds on another waits for that item to be integrated.

The wait is decided before an engine is chosen. A dependent that only defers must not be
counted as an engine selection (each poll would otherwise add one to the rotation's
bookkeeping, with no session behind it)."""

from datetime import timedelta

from vibey.application.dto import JobRecord
from vibey.application.ports import Clock, JobRepository
from vibey.application.worker import Defer, Outcome
from vibey.domain.job import JobState

#: How often a waiting item looks again. A build takes minutes, so five seconds costs nothing
#: and starts the dependent as soon as what it builds on is integrated.
DEFAULT_DEPENDENCY_WAIT = timedelta(seconds=5)


async def unintegrated_dependencies(jobs: JobRepository, job: JobRecord) -> tuple[str, ...]:
    """The items this one builds on that no succeeded `build.integrate` job covers yet."""
    raw = job.payload.get("depends_on_items")
    if not isinstance(raw, list | tuple) or not raw:
        return ()
    integrated = {
        record.work_item_id
        for record in await jobs.list_for_cycle(
            job.project_id, cycle=job.cycle, kind="build.integrate"
        )
        if record.state == JobState.SUCCEEDED
    }
    return tuple(str(dep) for dep in raw if str(dep) not in integrated)


class DependencyWait:
    """Says whether an implement job must wait, and for what."""

    def __init__(
        self, *, jobs: JobRepository, clock: Clock, wait: timedelta = DEFAULT_DEPENDENCY_WAIT
    ) -> None:
        self._jobs = jobs
        self._clock = clock
        self._wait = wait

    async def deferral(self, job: JobRecord) -> Defer | None:
        """A Defer (not a failure, not an attempt) while a dependency is unintegrated."""
        waiting_for = await unintegrated_dependencies(self._jobs, job)
        if not waiting_for:
            return None
        return Defer(
            retry_at=self._clock.now() + self._wait,
            detail=(
                f"waiting for {', '.join(waiting_for)} to be integrated, so this item "
                "builds on their code"
            ),
        )


class DeferringHandler:
    """A handler that does nothing but defer: the job's turn, without an engine."""

    def __init__(self, deferral: Defer) -> None:
        self._deferral = deferral

    async def handle(self, job: JobRecord) -> Outcome:
        del job
        return self._deferral
