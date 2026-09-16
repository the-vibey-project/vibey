# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Shared "run an EngineAdapter, tail its events, record them to the BUILD
ledger" logic used by both build.implement and build.verify -- they differ
in what they ask an engine to do and what a completing verdict means, not
in how a run is driven or persisted."""

from dataclasses import dataclass

from vibey.application.dto import JobRecord, RunHandle
from vibey.application.interfaces import (
    BuildLedger,
)
from vibey.application.ports import EngineAdapter
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.interfaces.correlation_interface import DeliveryCorrelationInterface
from vibey.domain.ledger import EventKind


@dataclass(frozen=True, slots=True)
class RunOutcome:
    complete: bool
    capacity_rejected: bool
    exit_code: int | None = None
    """The engine process's exit code, when the adapter exposes the
    optional ``run_exit_code`` capability -- EXIT_CODE_WIND_DOWN here is
    the graceful-handoff signal. None for adapters without the capability
    or while the process is still running."""


async def run_and_record(
    engine: EngineAdapter,
    ledger: BuildLedger,
    *,
    job: JobRecord,
    handle: RunHandle,
    correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
) -> RunOutcome:
    # One id for the whole delivery, derived from the project; the run's own
    # identity moves to causation_id, which is already on LedgerEvent and was
    # always None. `handle.run_id` rather than a freshly minted uuid4: it is
    # the id the RunSpec was started with, so a ledger row joins to the run
    # directory the engine wrote.
    correlation_id = correlation.for_project(job.project_id).value
    complete = False
    capacity_rejected = False
    async for event in engine.tail(handle):
        await ledger.record(
            project_id=job.project_id,
            cycle=job.cycle,
            job_id=job.id,
            engine_id=engine.descriptor.engine_id,
            correlation_id=correlation_id,
            causation_id=handle.run_id,
            event=event,
        )
        if event.kind == EventKind.VERDICT_RENDERED.value and bool(event.payload.get("complete")):
            complete = True
        if event.kind == EventKind.CAPACITY_REJECTED.value:
            capacity_rejected = True

    # Read the exit code only after the tail drains: the adapter's process
    # reference stays alive until stop() releases it, and a pre-drain read
    # would race the process's own shutdown.
    exit_code: int | None = None
    read_exit_code = getattr(engine, "run_exit_code", None)
    if callable(read_exit_code):
        raw = read_exit_code(handle)
        if isinstance(raw, int):
            exit_code = raw
    return RunOutcome(complete=complete, capacity_rejected=capacity_rejected, exit_code=exit_code)


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "BuildLedger",
]
