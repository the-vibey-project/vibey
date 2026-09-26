# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""The brake reads a project's caps when it checks, not when the worker starts.

`vibey worker` builds its BUILD handlers once. With the caps copied in at that moment, a
cap `vibey budget set` wrote while the worker ran would bind nothing until a restart,
and a project created uncapped had no brake at all -- so the command's promise that
"the next BUILD session will park a budget_exhausted gate" would be false. Here the
handler is built once and the project's stored config changes under it, as it does
when a person runs `vibey budget`.
"""

import dataclasses
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from tests.application.fakes import FakeJobRepository, make_job
from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.dto import EngineEvent, JobRecord, ProjectRecord
from vibey.application.interfaces import ProjectLookup
from vibey.application.project_budget import BUDGET_GATE_KIND
from vibey.application.worker import Park, Success
from vibey.domain.ledger import EventKind, LedgerEvent, Provenance, digest_event
from vibey.domain.phase import Phase
from vibey.domain.provision import ProvisionSpec
from vibey.infrastructure.engines.descriptors import CLAUDELOOP
from vibey.infrastructure.engines.scripted import ScriptedEngine

NOW = datetime(2026, 9, 24, 12, 0, tzinfo=UTC)


class _Projects:
    """One project whose stored config a test rewrites, as `vibey budget` does."""

    def __init__(self, project: ProjectRecord | None) -> None:
        self.project = project
        self.reads = 0

    async def get(self, project_id: UUID) -> ProjectRecord | None:
        self.reads += 1
        return self.project if self.project and self.project.project_id == project_id else None

    def configure(self, config: dict[str, object]) -> None:
        assert self.project is not None
        self.project = dataclasses.replace(self.project, config=config)


class _Ledger:
    def __init__(self, events: list[LedgerEvent]) -> None:
        self.events = events

    async def all_for_project(self, project_id: UUID) -> tuple[LedgerEvent, ...]:
        return tuple(self.events)


def _project(project_id: UUID, config: dict[str, object]) -> ProjectRecord:
    return ProjectRecord(
        project_id=project_id,
        name="live-caps",
        repo_path=Path("/tmp/live-caps"),
        phase=Phase.BUILD,
        cycle=1,
        max_cycles=3,
        config=config,
        created_at=NOW,
        updated_at=NOW,
    )


def _spend(project_id: UUID, dollars: float) -> LedgerEvent:
    payload: dict[str, object] = {"cost_usd": dollars}
    return LedgerEvent(
        event_id=uuid4(),
        project_id=project_id,
        cycle=1,
        phase=Phase.BUILD,
        seq=1,
        kind=EventKind.TURN_COMPLETED,
        engine_id=None,
        job_id=None,
        causation_id=None,
        correlation_id=project_id,
        provenance=Provenance.AGENT,
        produced_at=NOW,
        payload=payload,
        digest=digest_event(payload),
    )


def test_a_project_lookup_is_the_narrow_seam_the_brake_reads_through() -> None:
    assert isinstance(_Projects(None), ProjectLookup)


async def test_the_caps_are_read_from_the_stored_config_at_every_check() -> None:
    project_id = uuid4()
    projects = _Projects(_project(project_id, {}))
    source = LedgerBudgetSource(_Ledger([_spend(project_id, 12.5)]), projects=projects)

    uncapped = await source.current(project_id, 1)
    projects.configure({"max_cycle_dollars": 10, "max_cycle_turns": 50})
    capped = await source.current(project_id, 1)
    projects.configure({"max_cycle_turns": 50})
    cleared = await source.current(project_id, 1)

    assert (uncapped.max_dollars, uncapped.max_turns, uncapped.any_exhausted) == (None, None, False)
    assert (capped.max_dollars, capped.max_turns, capped.any_exhausted) == (10.0, 50, True)
    assert (cleared.max_dollars, cleared.any_exhausted) == (None, False)
    assert capped.dollars_spent == 12.5
    assert projects.reads == 3


async def test_a_project_that_is_gone_falls_back_to_the_caps_the_source_was_built_with() -> None:
    project_id = uuid4()
    source = LedgerBudgetSource(_Ledger([]), max_dollars=4.0, max_turns=9, projects=_Projects(None))

    budget = await source.current(project_id, 1)

    assert (budget.max_dollars, budget.max_turns) == (4.0, 9)


# -- through the handler, whose park-and-grant path is unchanged ---------------------------


class _Worktrees:
    def __init__(self, root: Path) -> None:
        self.root = root

    async def create(self, item_id: str, *, base_ref: str = "HEAD") -> Path:
        path = self.root / item_id
        path.mkdir(parents=True, exist_ok=True)
        return path


class _Provisioner:
    async def provision(self, worktree_path: Path, spec: ProvisionSpec) -> tuple[Path, ...]:
        return ()


class _BuildLedger:
    async def record(  # type: ignore[no-untyped-def]
        self, *, project_id, cycle, job_id, engine_id, correlation_id, event, causation_id=None
    ) -> None:
        assert isinstance(event, EngineEvent)


class _Clock:
    def now(self) -> datetime:
        return NOW


def _job(project_id: UUID) -> JobRecord:
    job = make_job(project_id, attempts=1)
    return dataclasses.replace(job, work_item_id="item-1", payload={"title": "t"})


async def test_a_worker_built_uncapped_parks_the_next_session_once_a_cap_is_set(
    tmp_path: Path,
) -> None:
    """The handler is built once, as `vibey worker` builds it; the cap arrives later."""
    project_id = uuid4()
    projects = _Projects(_project(project_id, {}))
    handler = BuildImplementHandler(
        worktrees=_Worktrees(tmp_path),
        provisioner=_Provisioner(),
        engine=ScriptedEngine(descriptor=CLAUDELOOP, base_dir=tmp_path / "engine"),
        ledger=_BuildLedger(),
        jobs=FakeJobRepository(),
        clock=_Clock(),
        budget_source=LedgerBudgetSource(_Ledger([_spend(project_id, 3.21)]), projects=projects),
    )

    assert isinstance(await handler.handle(_job(project_id)), Success)

    projects.configure({"max_cycle_dollars": 2.0})
    parked = await handler.handle(_job(project_id))

    assert isinstance(parked, Park)
    assert parked.request.kind == BUDGET_GATE_KIND
    assert "$3.21 spent of $2.00 cap" in parked.request.prompt

    projects.configure({})
    assert isinstance(await handler.handle(_job(project_id)), Success)
