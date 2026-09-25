# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The BUILD handler at ULTRA (ADR-0063): passes at ULTRA with no ladder, "done" as a
checkpoint followed by the next pass under its own key, Stop at the next boundary, the
brake at a cap, and a missing cap parked unless no cap was declared."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from tests.application.fakes import FakeJobRepository
from tests.application.test_build_implement_handler import (
    FakeLedger,
    FakeProvisioner,
    FakeWorktrees,
    FixedClock,
    _job,
)
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.dto import RunSpec
from vibey.application.worker import Failure, Park, Success
from vibey.domain.budget import BudgetLedger
from vibey.domain.effort import Effort
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.ultra import ULTRA_PAYLOAD_KEY, UltraPass
from vibey.infrastructure.engines.descriptors import QWENLOOP
from vibey.infrastructure.engines.scripted import ScriptedEngine


class EventsReader:
    def __init__(self, *kinds: tuple[EventKind, dict[str, object]]) -> None:
        self.events = [
            LedgerEvent(
                event_id=uuid4(),
                project_id=uuid4(),
                cycle=1,
                phase=Phase.BUILD,
                seq=seq,
                kind=kind,
                engine_id=None,
                job_id=None,
                causation_id=None,
                correlation_id=uuid4(),
                provenance=Provenance.TRUSTED,
                produced_at=datetime(2026, 9, 25, tzinfo=UTC),
                payload=payload,
                digest=digest_event(payload),
            )
            for seq, (kind, payload) in enumerate(kinds, start=1)
        ]

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(self.events)


class FixedBudget:
    def __init__(self, ledger: BudgetLedger) -> None:
        self._ledger = ledger

    async def current(self, project_id: object, cycle: int) -> BudgetLedger:
        return self._ledger


class RecordingEngine(ScriptedEngine):
    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.efforts: list[Effort] = []

    async def start(self, spec: RunSpec):  # type: ignore[no-untyped-def]
        self.efforts.append(spec.effort)
        return await super().start(spec)


STARTED = (EventKind.ULTRA_STARTED, {})
STOPPED = (EventKind.ULTRA_STOPPED, {})
NO_CAP = (EventKind.ULTRA_NO_CAP_CHANGED, {"enabled": True})
CAPPED = BudgetLedger(turns_spent=0, dollars_spent=1.0, max_turns=None, max_dollars=10.0)


class FakeCheckpoint:
    def __init__(self) -> None:
        self.commits: list[tuple[Path, str]] = []

    async def commit(self, worktree_path: Path, message: str) -> str | None:
        self.commits.append((worktree_path, message))
        return "c0ffee"


def _handler(
    tmp_path: Path,
    reader: EventsReader | None,
    budget: BudgetLedger | None = CAPPED,
    checkpoint: FakeCheckpoint | None = None,
) -> tuple[BuildImplementHandler, RecordingEngine, FakeLedger, FakeJobRepository]:
    engine = RecordingEngine(descriptor=QWENLOOP, base_dir=tmp_path / "engine")
    ledger = FakeLedger()
    jobs = FakeJobRepository()
    handler = BuildImplementHandler(
        worktrees=FakeWorktrees(tmp_path),
        provisioner=FakeProvisioner(),
        engine=engine,
        ledger=ledger,
        jobs=jobs,
        clock=FixedClock(),
        budget_source=FixedBudget(budget) if budget is not None else None,
        ultra_ledger=reader,
        checkpoint=checkpoint,
    )
    return handler, engine, ledger, jobs


async def test_an_active_run_passes_at_ultra_past_the_ladder_and_enqueues_the_next_pass(
    tmp_path: Path,
) -> None:
    handler, engine, ledger, jobs = _handler(tmp_path, EventsReader(STARTED))
    # Attempt 40 would exhaust any ladder; at ULTRA the ladder is not consulted.
    job = _job(attempts=40, payload={"title": "improve", ULTRA_PAYLOAD_KEY: 2})

    outcome = await handler.handle(job)

    assert isinstance(outcome, Success)
    assert engine.efforts == [Effort.ULTRA]
    passes = [e for e in ledger.recorded if e.kind == EventKind.ULTRA_PASS_COMPLETED.value]
    assert len(passes) == 1 and passes[0].payload["pass"] == 2
    kinds = [job.kind for job in jobs._jobs.values()]
    assert kinds == ["build.verify", "build.implement"]
    verify, following = list(jobs._jobs.values())
    assert following.payload[ULTRA_PAYLOAD_KEY] == 3
    assert following.idempotency_key == UltraPass("item-1", 3).job_key(job.project_id, job.cycle)
    assert passes[0].payload["next_job_key"] == following.idempotency_key
    assert following.payload["title"] == "improve"


async def test_stop_ends_a_queued_pass_without_running_it(tmp_path: Path) -> None:
    handler, engine, _, jobs = _handler(tmp_path, EventsReader(STARTED, STOPPED))
    outcome = await handler.handle(_job(payload={ULTRA_PAYLOAD_KEY: 5}))
    assert outcome == Success({"work_item_id": "item-1", "ultra": "stopped"})
    assert engine.efforts == [] and not jobs._jobs


async def test_the_brake_parks_an_ultra_pass_at_its_cap(tmp_path: Path) -> None:
    spent = BudgetLedger(turns_spent=0, dollars_spent=10.0, max_turns=None, max_dollars=10.0)
    handler, engine, _, _ = _handler(tmp_path, EventsReader(STARTED), spent)
    outcome = await handler.handle(_job())
    assert isinstance(outcome, Park) and outcome.request.kind == "budget_exhausted"
    assert engine.efforts == []


async def test_no_cap_without_the_declaration_parks_for_one(tmp_path: Path) -> None:
    uncapped = replace(CAPPED, max_dollars=None)
    handler, engine, _, _ = _handler(tmp_path, EventsReader(STARTED), uncapped)
    outcome = await handler.handle(_job())
    assert isinstance(outcome, Park) and outcome.request.kind == "ultra_needs_cap"
    assert "vibey budget no-cap" in outcome.request.prompt
    assert engine.efforts == []


async def test_no_budget_source_is_uncapped_so_it_needs_the_declaration(tmp_path: Path) -> None:
    handler, engine, _, _ = _handler(tmp_path, EventsReader(STARTED, NO_CAP), budget=None)
    outcome = await handler.handle(_job())
    assert isinstance(outcome, Success)
    assert engine.efforts == [Effort.ULTRA]


async def test_a_first_pass_after_start_is_pass_one(tmp_path: Path) -> None:
    handler, _, ledger, jobs = _handler(tmp_path, EventsReader(STARTED))
    await handler.handle(_job(payload={"title": "t"}))
    passes = [e for e in ledger.recorded if e.kind == EventKind.ULTRA_PASS_COMPLETED.value]
    assert passes[0].payload["pass"] == 1
    assert list(jobs._jobs.values())[-1].payload[ULTRA_PAYLOAD_KEY] == 2


async def test_without_a_run_the_ladder_decides_as_before(tmp_path: Path) -> None:
    handler, engine, ledger, jobs = _handler(tmp_path, EventsReader())
    outcome = await handler.handle(_job(payload={"title": "t"}))
    assert isinstance(outcome, Success) and "verify_job_id" not in outcome.result
    assert engine.efforts == [Effort.LOW]
    assert [job.kind for job in jobs._jobs.values()] == ["build.verify"]
    assert not any(e.kind == EventKind.ULTRA_PASS_COMPLETED.value for e in ledger.recorded)


async def test_an_ultra_pass_skips_forced_rotation(tmp_path: Path) -> None:
    handler, engine, _, _ = _handler(tmp_path, EventsReader(STARTED))
    job = _job(attempts=3, payload={"previous_engine_id": "qwenloop"})
    assert isinstance(await handler.handle(job), Success)
    assert engine.efforts == [Effort.ULTRA]


async def test_a_failed_pass_enqueues_no_next_pass(tmp_path: Path) -> None:
    engine = RecordingEngine(
        descriptor=QWENLOOP,
        base_dir=tmp_path / "engine",
        script=[{"kind": "SessionSeeded", "at": "2026-01-01T00:00:00+00:00", "payload": {}}],
    )
    jobs = FakeJobRepository()
    handler = BuildImplementHandler(
        worktrees=FakeWorktrees(tmp_path),
        provisioner=FakeProvisioner(),
        engine=engine,
        ledger=FakeLedger(),
        jobs=jobs,
        clock=FixedClock(),
        budget_source=FixedBudget(CAPPED),
        ultra_ledger=EventsReader(STARTED),
    )
    outcome = await handler.handle(_job())
    assert isinstance(outcome, Failure)
    assert not jobs._jobs


async def test_the_next_pass_depends_on_the_checks(tmp_path: Path) -> None:
    handler, _, _, jobs = _handler(tmp_path, EventsReader(STARTED))
    requests: list[object] = []
    original = jobs.enqueue

    async def spy(request):  # type: ignore[no-untyped-def]
        requests.append(request)
        return await original(request)

    jobs.enqueue = spy  # type: ignore[method-assign]
    await handler.handle(_job())
    verify = next(j for j in jobs._jobs.values() if j.kind == "build.verify")
    following = requests[-1]
    assert following.depends_on == (verify.id,)  # type: ignore[attr-defined]


async def test_done_is_a_checkpoint_committed_before_the_next_pass(tmp_path: Path) -> None:
    checkpoint = FakeCheckpoint()
    handler, _, ledger, _ = _handler(tmp_path, EventsReader(STARTED), checkpoint=checkpoint)
    await handler.handle(_job(payload={ULTRA_PAYLOAD_KEY: 4}))
    assert checkpoint.commits == [(tmp_path / "item-1", "chore(ultra): pass 4 of item-1")]
    [done] = [e for e in ledger.recorded if e.kind == EventKind.ULTRA_PASS_COMPLETED.value]
    assert done.payload["commit"] == "c0ffee"
