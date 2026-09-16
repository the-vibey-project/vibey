# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
import ast
import logging
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import structlog

from tests.application.fakes import FakeHumanGateRepository, FakeJobRepository, make_job
from vibey import bootstrap
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
from vibey.domain.verbosity import LogPlan
from vibey.infrastructure.engines.claudeloop_design import ClaudeLoopDesignProvider
from vibey.infrastructure.engines.qwenloop_design import QwenloopDesignProvider
from vibey.infrastructure.engines.scripted_design import ScriptedDesignProvider
from vibey.infrastructure.engines.scripted_visual import ScriptedVisualProvider
from vibey.infrastructure.logging import StructlogAppLogger, configure_logging


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


def test_every_composed_worker_is_given_the_structured_logger() -> None:
    """Structural, not textual. Counting `return WorkerLoop(` against
    `logger=StructlogAppLogger(` balances two unrelated totals: drop the keyword from one
    constructor, add a `StructlogAppLogger(...)` anywhere else in the module, and the counts
    still match while the worker is back on the flattening default. So walk the AST and tie
    each construction to its own argument."""
    tree = ast.parse(Path(bootstrap.__file__).read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "WorkerLoop"
    ]
    assert calls, "bootstrap must still construct WorkerLoop"
    for call in calls:
        logger = next((kw for kw in call.keywords if kw.arg == "logger"), None)
        assert logger is not None, (
            f"WorkerLoop at bootstrap.py:{call.lineno} is constructed without a logger, "
            "so it falls back to the flattening default"
        )
        assert isinstance(logger.value, ast.Call), f"line {call.lineno}: logger= is not a call"
        assert isinstance(logger.value.func, ast.Name), f"line {call.lineno}: unexpected logger"
        assert logger.value.func.id == "StructlogAppLogger", (
            f"WorkerLoop at bootstrap.py:{call.lineno} is given "
            f"{logger.value.func.id}, which is not the redaction-aware logger"
        )


def test_a_key_only_secret_is_redacted_through_the_configured_sink(tmp_path: Path) -> None:
    """The property the structural test cannot see: a field sensitive only because of its
    NAME survives as a field all the way to the sink, and is redacted there.

    `hunter2` matches no vendor-shaped pattern, so it is redacted by key or not at all --
    which is exactly what flattening it into the message would lose."""
    root = logging.getLogger()
    root.handlers.clear()
    structlog.reset_defaults()
    log_file = tmp_path / "vibey.log"
    configure_logging(
        LogPlan(level="INFO", include_third_party=False, include_payloads=False),
        log_file=log_file,
        human_console=False,
    )
    try:
        # the logger the composition root hands every worker
        StructlogAppLogger(owner="worker-1").warning("job.deferred", password="hunter2")
        logging.getLogger().handlers[-1].flush()
        written = log_file.read_text(encoding="utf-8")
    finally:
        root.handlers.clear()
        structlog.reset_defaults()

    assert "hunter2" not in written, "a key-only secret reached the sink unredacted"
    assert "[REDACTED]" in written
    assert "job.deferred" in written


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
