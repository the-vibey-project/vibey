# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Shared "run an EngineAdapter, tail its events, record them to the BUILD
ledger" logic used by both build.implement and build.verify -- they differ
in what they ask an engine to do and what a completing verdict means, not
in how a run is driven or persisted."""

import contextlib
from dataclasses import dataclass

from vibey.application.dto import HumanGateRequest, JobRecord, RunHandle
from vibey.application.interfaces import (
    BuildLedger,
    TelemetryTracer,
)
from vibey.application.ports import EngineAdapter
from vibey.domain.correlation import DELIVERY_CORRELATION
from vibey.domain.engine import EXIT_CODE_BACKEND_MISCONFIGURED, EngineDescriptor
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
    diagnostic_tail: str = ""
    """Bounded engine output retained for failure attribution."""

    def misconfiguration_gate(
        self, descriptor: EngineDescriptor, work_item_id: str | None
    ) -> HumanGateRequest | None:
        """The human gate for a run that ended on its own backend's configuration.

        Exit 78 (EX_CONFIG) is the runner saying its backend cannot serve this run:
        claudeloop's `BackendMisconfigured` -- an unreachable local server, a model
        that is not pulled or fails to load, a context window too small for one
        request. No retry fixes any of that, and a retry burns an attempt of a
        bounded ladder on the same fault, so the job parks and asks for the fix.
        Answering the gate retries the job; the engine's own `doctor` names the cause.

        Returns None for any other exit, so both BUILD handlers ask the same question
        and cannot disagree about the answer.
        """
        if self.exit_code != EXIT_CODE_BACKEND_MISCONFIGURED:
            return None
        doctor = " ".join((descriptor.binary, "doctor", *descriptor.doctor_args))
        engine = descriptor.engine_id.value
        return HumanGateRequest(
            kind="engine_misconfigured",
            prompt=(
                f"engine {engine} stopped on work item {work_item_id!r} with exit "
                f"{EXIT_CODE_BACKEND_MISCONFIGURED}: its backend is misconfigured (an "
                "unreachable server, a model not pulled or failing to load, or a context "
                f"window too small). Run `{doctor}` to see which, fix it, then answer "
                "anything to retry."
            ),
        )


async def run_and_record(
    engine: EngineAdapter,
    ledger: BuildLedger,
    *,
    job: JobRecord,
    handle: RunHandle,
    correlation: DeliveryCorrelationInterface = DELIVERY_CORRELATION,
    tracer: TelemetryTracer | None = None,
) -> RunOutcome:
    # One id for the whole delivery, derived from the project; the run's own
    # identity moves to causation_id, which is already on LedgerEvent and was
    # always None. `handle.run_id` rather than a freshly minted uuid4: it is
    # the id the RunSpec was started with, so a ledger row joins to the run
    # directory the engine wrote.
    correlation_id = correlation.for_project(job.project_id).value
    complete = False
    capacity_rejected = False
    diagnostics: list[str] = []
    turn_number = 0
    async for event in engine.tail(handle):
        turn_span = (
            tracer.trace_turn(
                engine_id=engine.descriptor.engine_id,
                turn_number=turn_number,
                event_kind=event.kind,
            )
            if tracer is not None and event.kind == EventKind.TURN_COMPLETED.value
            else contextlib.nullcontext()
        )
        with turn_span as span:
            await ledger.record(
                project_id=job.project_id,
                cycle=job.cycle,
                job_id=job.id,
                engine_id=engine.descriptor.engine_id,
                correlation_id=correlation_id,
                causation_id=handle.run_id,
                event=event,
            )
            if span is not None:
                span.set_attribute("event_kind", event.kind)
        if event.kind == EventKind.TURN_COMPLETED.value:
            turn_number += 1
        if event.kind == EventKind.VERDICT_RENDERED.value and bool(event.payload.get("complete")):
            complete = True
        if event.kind == EventKind.CAPACITY_REJECTED.value:
            capacity_rejected = True
        for key in (
            "stderr_tail",
            "stdout",
            "stderr",
            "diagnostic",
            "message",
            "error",
            "detail",
            "output",
        ):
            value = event.payload.get(key)
            if isinstance(value, str) and value.strip():
                diagnostics.append(value.strip())

    # Read the exit code only after the tail drains: the adapter's process
    # reference stays alive until stop() releases it, and a pre-drain read
    # would race the process's own shutdown.
    exit_code: int | None = None
    read_exit_code = getattr(engine, "run_exit_code", None)
    if callable(read_exit_code):
        raw = read_exit_code(handle)
        if isinstance(raw, int):
            exit_code = raw
    read_diagnostics = getattr(engine, "diagnostic_tail", None)
    if callable(read_diagnostics):
        raw_diagnostics = read_diagnostics(handle)
        if isinstance(raw_diagnostics, str) and raw_diagnostics.strip():
            diagnostics.append(raw_diagnostics.strip())
    diagnostic_tail = "\n".join(diagnostics)[-8_000:]
    release_diagnostics = getattr(engine, "release_diagnostics", None)
    if callable(release_diagnostics):
        release_diagnostics(handle)
    return RunOutcome(
        complete=complete,
        capacity_rejected=capacity_rejected,
        exit_code=exit_code,
        diagnostic_tail=diagnostic_tail,
    )


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "BuildLedger",
]
