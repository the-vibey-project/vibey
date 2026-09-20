# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""run_and_record's optional exit-code channel."""

from collections.abc import AsyncIterator
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from tests.application.fakes import make_job
from vibey.application.build_engine_run import run_and_record
from vibey.application.dto import EngineEvent, RunHandle
from vibey.infrastructure.engines.descriptors import CLAUDELOOP


class _NoExitCodeEngine:
    """An adapter without the optional run_exit_code capability."""

    descriptor = CLAUDELOOP

    async def tail(self, handle: RunHandle) -> AsyncIterator[EngineEvent]:
        return
        yield  # pragma: no cover


class _NullLedger:
    async def record(self, **kwargs: object) -> None:
        raise AssertionError("no events to record")


class _RecordingLedger:
    async def record(self, **kwargs: object) -> None:
        del kwargs


class _DiagnosticEngine(_NoExitCodeEngine):
    def run_exit_code(self, handle: RunHandle) -> int | None:
        return 137

    def diagnostic_tail(self, handle: RunHandle) -> str:
        return "AssertionError: FAILED while checking the work item"


class _EventDiagnosticEngine(_NoExitCodeEngine):
    def __init__(self) -> None:
        self.released = False

    async def tail(self, handle: RunHandle) -> AsyncIterator[EngineEvent]:
        yield EngineEvent(
            kind="diagnostic",
            at=datetime.now(UTC),
            payload={"message": " ", "detail": "FAILED in the work item"},
        )

    def run_exit_code(self, handle: RunHandle) -> object:
        return "not-an-exit-code"

    def diagnostic_tail(self, handle: RunHandle) -> str:
        return "   "

    def release_diagnostics(self, handle: RunHandle) -> None:
        self.released = True


def _handle() -> RunHandle:
    return RunHandle(
        run_id=uuid4(),
        engine_id=CLAUDELOOP.engine_id,
        run_dir=Path("/tmp/unused"),
        pid=None,
    )


async def test_adapter_without_the_capability_reports_no_exit_code() -> None:
    job = replace(make_job(uuid4()), kind="build.implement")

    outcome = await run_and_record(
        _NoExitCodeEngine(),  # type: ignore[arg-type]
        _NullLedger(),
        job=job,
        handle=_handle(),
    )

    assert outcome.exit_code is None
    assert not outcome.complete
    assert not outcome.capacity_rejected


async def test_exit_code_outcome_keeps_diagnostics_for_failure_attribution() -> None:
    job = replace(make_job(uuid4()), kind="build.implement")

    outcome = await run_and_record(
        _DiagnosticEngine(),  # type: ignore[arg-type]
        _NullLedger(),
        job=job,
        handle=_handle(),
    )

    assert outcome.exit_code == 137
    assert "AssertionError: FAILED" in outcome.diagnostic_tail


async def test_event_and_optional_diagnostics_are_retained_and_released() -> None:
    job = replace(make_job(uuid4()), kind="build.implement")
    engine = _EventDiagnosticEngine()

    outcome = await run_and_record(
        engine,  # type: ignore[arg-type]
        _RecordingLedger(),
        job=job,
        handle=_handle(),
    )

    assert outcome.exit_code is None
    assert outcome.diagnostic_tail == "FAILED in the work item"
    assert engine.released
