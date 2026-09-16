# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey.application.design import DesignEvent
from vibey.application.dto import ProjectRecord
from vibey.bootstrap import (
    _independence_policy,
    _independent_review_required,
    build_design_worker,
    build_visual_worker,
    qwenloop_enabled,
)
from vibey.domain.engine import EngineId
from vibey.domain.job import JobState
from vibey.domain.phase import Phase
from vibey.infrastructure.engines.claudeloop_design import ClaudeLoopDesignProvider
from vibey.infrastructure.engines.qwenloop_design import QwenloopDesignProvider
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider
from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider


class FakeLedger:
    def __init__(self) -> None:
        self.events: list[DesignEvent] = []
        self.engines: list[EngineId | None] = []

    async def append(self, project_id, cycle, job_id, engine_id, event):  # type: ignore[no-untyped-def]
        self.events.append(event)
        self.engines.append(engine_id)

    async def all_for_project(self, project_id):  # type: ignore[no-untyped-def]
        return tuple(self.events)


class SovereignDesignProvider(ScriptedDesignProvider):
    """A stand-in for the sovereign provider: same answers, different actor."""

    engine_id: EngineId | None = EngineId.QWENLOOP


def test_qwenloop_feature_resolution(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.delenv("VIBEY_FEATURE_QWENLOOP", raising=False)
    assert not qwenloop_enabled({})
    assert qwenloop_enabled({"features": {"qwenloop": True}})

    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "true")
    assert qwenloop_enabled({})

    monkeypatch.setenv("VIBEY_FEATURE_QWENLOOP", "false")
    assert not qwenloop_enabled({"features": {"qwenloop": True}})


async def test_build_design_worker_composes_an_executable_interview(tmp_path: Path) -> None:
    project_id = uuid4()
    job = make_job(project_id)
    job = job.__class__(
        **{
            field: getattr(job, field)
            for field in job.__dataclass_fields__
            if field not in {"phase", "kind"}
        },
        phase=Phase.DESIGN,
        kind="design.interview",
    )
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    resources = SimpleNamespace(
        jobs=jobs,
        gates=gates,
        design_ledger=FakeLedger(),
        design_specs=SimpleNamespace(),
    )
    project = ProjectRecord(
        project_id=project_id,
        name="idea",
        repo_path=tmp_path,
        phase=Phase.DESIGN,
        cycle=1,
        max_cycles=10,
        config={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    worker = build_design_worker(
        resources=resources,  # type: ignore[arg-type]
        project=project,
        provider=ScriptedDesignProvider(),
        owner="test-worker",
    )

    assert await worker.run_once(project_id)
    stored = await jobs.get(job.id)
    assert stored is not None
    assert stored.state is JobState.AWAITING_HUMAN
    assert len(gates.raised) == 1


class FakeVisualInventories:
    def __init__(self) -> None:
        self.value = None
        self.published = False

    async def save(self, project_id, cycle, value):  # type: ignore[no-untyped-def]
        self.value = value

    async def load(self, project_id, cycle):  # type: ignore[no-untyped-def]
        return self.value

    async def publish(self, project_id, cycle, value):  # type: ignore[no-untyped-def]
        self.published = True


async def test_build_visual_worker_composes_an_executable_inventory_job(tmp_path: Path) -> None:
    project_id = uuid4()
    job = make_job(project_id)
    job = job.__class__(
        **{
            field: getattr(job, field)
            for field in job.__dataclass_fields__
            if field not in {"phase", "kind"}
        },
        phase=Phase.VISUAL_DESIGN,
        kind="visual.inventory",
    )
    jobs = FakeJobRepository([job])
    gates = FakeHumanGateRepository()
    inventories = FakeVisualInventories()
    resources = SimpleNamespace(
        jobs=jobs,
        gates=gates,
        design_ledger=FakeLedger(),
        visual_inventories=inventories,
    )
    worker = build_visual_worker(
        resources=resources,  # type: ignore[arg-type]
        provider=ScriptedVisualProvider(),
        owner="test-worker",
    )

    assert await worker.run_once(project_id)
    stored = await jobs.get(job.id)
    assert stored is not None
    assert stored.state is JobState.SUCCEEDED
    assert inventories.value is not None


def _design_job(project_id):  # type: ignore[no-untyped-def]
    job = make_job(project_id)
    return job.__class__(
        **{
            field: getattr(job, field)
            for field in job.__dataclass_fields__
            if field not in {"phase", "kind"}
        },
        phase=Phase.DESIGN,
        kind="design.interview",
    )


def _design_resources(jobs, ledger):  # type: ignore[no-untyped-def]
    return SimpleNamespace(
        jobs=jobs,
        gates=FakeHumanGateRepository(),
        design_ledger=ledger,
        design_specs=SimpleNamespace(),
    )


def _project(project_id, tmp_path):  # type: ignore[no-untyped-def]
    return ProjectRecord(
        project_id=project_id,
        name="idea",
        repo_path=tmp_path,
        phase=Phase.DESIGN,
        cycle=1,
        max_cycles=10,
        config={},
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


async def test_design_ledger_names_the_engine_that_actually_interviewed(tmp_path: Path) -> None:
    """A sovereign run must not be recorded as claudeloop.

    The ledger is append-only, so a wrongly attributed event can never be
    deleted -- only contradicted. Attribution therefore comes from the provider
    that was actually composed, not from a literal in the composition root.
    """
    project_id = uuid4()
    jobs = FakeJobRepository([_design_job(project_id)])
    ledger = FakeLedger()
    worker = build_design_worker(
        resources=_design_resources(jobs, ledger),  # type: ignore[arg-type]
        project=_project(project_id, tmp_path),
        provider=SovereignDesignProvider(),
        owner="test-worker",
    )

    assert await worker.run_once(project_id)
    assert ledger.engines == [EngineId.QWENLOOP]


async def test_a_scripted_design_names_no_engine_rather_than_borrowing_one(
    tmp_path: Path,
) -> None:
    """Nothing ran, so nothing is named: `engine_id` is nullable for this."""
    project_id = uuid4()
    jobs = FakeJobRepository([_design_job(project_id)])
    ledger = FakeLedger()
    worker = build_design_worker(
        resources=_design_resources(jobs, ledger),  # type: ignore[arg-type]
        project=_project(project_id, tmp_path),
        provider=ScriptedDesignProvider(),
        owner="test-worker",
    )

    assert await worker.run_once(project_id)
    assert ledger.engines == [None]


def test_every_design_provider_declares_the_engine_it_speaks_for() -> None:
    """One declaration each, beside the implementation -- the single source the
    composition root reads instead of repeating a literal per wiring site."""
    assert ClaudeLoopDesignProvider.engine_id is EngineId.CLAUDELOOP
    assert QwenloopDesignProvider.engine_id is EngineId.QWENLOOP
    assert ScriptedDesignProvider.engine_id is None


def test_strict_independence_is_opt_in_and_refuses_anything_but_true() -> None:
    """`verify.require_independent_review` decides whether a one-engine pool may
    self-review (ADR-0035). The default has to be False, because the measured
    alternative was BUILD deferring forever; and only the boolean True may turn
    the strict rule on, so a truthy-looking string in a hand-written config
    cannot silently change how a project verifies its own work."""
    assert not _independent_review_required({})
    assert _independent_review_required({"verify": {"require_independent_review": True}})

    # Anything that is not exactly True leaves the default in place.
    assert not _independent_review_required({"verify": {"require_independent_review": False}})
    assert not _independent_review_required({"verify": {"require_independent_review": "true"}})
    assert not _independent_review_required({"verify": {"require_independent_review": 1}})
    assert not _independent_review_required({"verify": {}})
    assert not _independent_review_required({"verify": "require_independent_review"})


class FixedClock:
    def now(self) -> datetime:
        return datetime(2026, 9, 15, tzinfo=UTC)


def test_the_strict_project_gets_no_independence_policy_and_the_default_gets_one() -> None:
    """Both arms of the composition root's choice (ADR-0035).

    `None` is how the composition root says "keep the strict rule": with no
    policy wired, `BuildVerifyHandler` fails a verify the implementer reviews
    itself, which is what a project that would rather stall has asked for.
    """
    pool = frozenset({EngineId.CLAUDELOOP})
    clock = FixedClock()

    strict = _independence_policy({"verify": {"require_independent_review": True}}, pool, clock)
    assert strict is None

    default = _independence_policy({}, pool, clock)
    assert default is not None
    assert default.pool == pool
