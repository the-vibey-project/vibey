# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Composition root: the only module that wires concrete adapters to ports."""

import os
from collections.abc import AsyncIterator, Awaitable, Callable, Mapping
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import asyncpg

from vibey.application.budget_source import LedgerBudgetSource
from vibey.application.build_decompose_handler import BuildDecomposeHandler
from vibey.application.build_implement_handler import BuildImplementHandler
from vibey.application.build_integrate_handler import BuildIntegrateHandler
from vibey.application.build_verify_handler import (
    BuildVerifyHandler,
    VerifyIndependencePolicy,
    VerifyRepairPolicy,
)
from vibey.application.deploy_acceptance_handler import DeployAcceptanceHandler
from vibey.application.deploy_design_bridge import DeployDesignBridgeHandler
from vibey.application.deploy_design_handler import (
    DeployInterviewHandler,
    DeploySynthesizeHandler,
)
from vibey.application.deploy_execute_handler import DeployExecuteHandler
from vibey.application.deploy_review_handler import (
    DeployReviewDemoHandler,
    DeployReviewTriageHandler,
)
from vibey.application.deploy_review_routing import DeployReviewRoutingHandler
from vibey.application.design_handler import DesignInterviewHandler
from vibey.application.design_research_handler import DesignResearchHandler
from vibey.application.design_synthesis_handler import DesignSpecHandler, DesignSynthesizeHandler
from vibey.application.dto import JobRecord, ProjectRecord
from vibey.application.engine_health_service import EngineHealthService
from vibey.application.engine_selection import (
    RotationRecordingHandler,
    SelectingEngineProvider,
    SpendMeteringLedger,
)
from vibey.application.engine_selector import EngineSelector
from vibey.application.interfaces import (
    AzureClientPort,
    BlobPort,
    BusPort,
    CachePort,
    Clock,
    ConductorPreflightInterface,
    ConfigStorePort,
    DesignProvider,
    DocsPort,
    EmailPort,
    EngineAdapter,
    FilesPort,
    IssueTrackerPort,
    JobHandler,
    MessagingPort,
    SecretsPort,
    SiemPort,
    SmsPort,
    VisualInventoryProducer,
    WorkPlanProducer,
)
from vibey.application.job_dispatcher import JobDispatcher
from vibey.application.preflight import ConductorPreflight
from vibey.application.review_collect_handler import ReviewCollectHandler
from vibey.application.review_demo_handler import ReviewDemoHandler
from vibey.application.review_deployment_choice_handler import ReviewDeploymentChoiceHandler
from vibey.application.review_triage_handler import ReviewTriageHandler
from vibey.application.rotation_handoff import RotationHandoffService
from vibey.application.visual_handler import VisualInventoryHandler, VisualPlanHandler
from vibey.application.wind_down import WindDownOrchestrator
from vibey.application.worker import WorkerLoop
from vibey.domain.config import VibeyConfig
from vibey.domain.engine import EngineId
from vibey.domain.errors import VibeyError
from vibey.domain.phase import Phase
from vibey.infrastructure.azure.adapter import InMemoryAzureClientAdapter
from vibey.infrastructure.build.automated_review_runner import SubprocessAutomatedReviewRunner
from vibey.infrastructure.build.gate_runner import SubprocessGateRunner
from vibey.infrastructure.db.advisory_lock import PostgresAdvisoryLock
from vibey.infrastructure.db.build_ledger import PostgresBuildLedger
from vibey.infrastructure.db.design_ledger import PostgresDesignLedger
from vibey.infrastructure.db.design_spec_repository import FileDesignSpecRepository
from vibey.infrastructure.db.engine_health_repository import PostgresEngineHealthRepository
from vibey.infrastructure.db.handoff_repository import PostgresHandoffRepository
from vibey.infrastructure.db.human_gate_repository import PostgresHumanGateRepository
from vibey.infrastructure.db.interfaces import MigratorInterface
from vibey.infrastructure.db.job_repository import PostgresJobRepository
from vibey.infrastructure.db.ledger_repository import PostgresLedgerRepository
from vibey.infrastructure.db.migrator import PostgresMigrator, discover_migrations
from vibey.infrastructure.db.project_repository import PostgresProjectRepository
from vibey.infrastructure.db.review_ledger import PostgresReviewLedger
from vibey.infrastructure.db.rotation_cursor_repository import PostgresRotationCursorRepository
from vibey.infrastructure.db.visual_inventory_repository import FileVisualInventoryRepository
from vibey.infrastructure.deploy.state_repository import FileDeploymentStateRepository
from vibey.infrastructure.docs.bookstack import BookStackDocsAdapter
from vibey.infrastructure.docs.in_memory import InMemoryDocs
from vibey.infrastructure.email.forward_email import ForwardEmailAdapter
from vibey.infrastructure.email.in_memory import InMemoryEmail
from vibey.infrastructure.engines.descriptors import BY_ENGINE_ID, DEFAULT_DESCRIPTORS
from vibey.infrastructure.engines.local_engines import (
    LocalEndpointEnvironment,
    LocalEngineSettings,
)
from vibey.infrastructure.engines.loop_process_adapter import LoopProcessAdapter
from vibey.infrastructure.files.in_memory import InMemoryFiles
from vibey.infrastructure.files.nextcloud import NextcloudFilesAdapter
from vibey.infrastructure.git.integration_branch import IntegrationBranch
from vibey.infrastructure.git.worktree_manager import GitWorktreeManager
from vibey.infrastructure.ledger.full_ledger_writer import write_full_ledger
from vibey.infrastructure.logging import StructlogAppLogger
from vibey.infrastructure.messaging.in_memory import InMemoryMessaging
from vibey.infrastructure.messaging.matrix import MatrixMessagingAdapter
from vibey.infrastructure.notify import NotificationService
from vibey.infrastructure.otel import TelemetryMetrics, TelemetryTracer
from vibey.infrastructure.postgres import POSTGRES_MIN_MAJOR, parse_postgres_server_version
from vibey.infrastructure.preflight_feasibility import VibeyGhFeasibilityAdapter
from vibey.infrastructure.provision.agent_surface import AgentSurfaceProvisioner
from vibey.infrastructure.review_artifact_writer import FileReviewArtifactWriter
from vibey.infrastructure.secrets.in_memory import InMemorySecrets
from vibey.infrastructure.secrets.openbao import OpenBaoSecretsAdapter
from vibey.infrastructure.skills_context import compiler_from_config
from vibey.infrastructure.sms.in_memory import InMemorySms
from vibey.infrastructure.sms.kannel import KannelSmsAdapter
from vibey.infrastructure.tracker.in_memory import InMemoryTracker
from vibey.infrastructure.tracker.plane import PlaneTrackerAdapter


@dataclass(frozen=True, slots=True)
class AppResources:
    projects: PostgresProjectRepository
    jobs: PostgresJobRepository
    gates: PostgresHumanGateRepository
    ledger: PostgresLedgerRepository
    design_ledger: PostgresDesignLedger
    design_specs: FileDesignSpecRepository
    visual_inventories: FileVisualInventoryRepository
    # Phase-specific ledger adapters over the one append-only event log.
    build_ledger: PostgresBuildLedger
    review_ledger: PostgresReviewLedger
    deploy_review_ledger: PostgresReviewLedger
    # Rotation infrastructure (Phase E1)
    engine_health_repo: PostgresEngineHealthRepository
    rotation_cursors: PostgresRotationCursorRepository
    engine_health_service: EngineHealthService
    conductor_preflight: ConductorPreflightInterface
    engine_selector: EngineSelector
    rotation_handoff: RotationHandoffService
    engine_adapters: Mapping[EngineId, EngineAdapter]
    handoffs: PostgresHandoffRepository
    clock: Clock
    notifications: NotificationService
    telemetry_tracer: TelemetryTracer
    telemetry_metrics: TelemetryMetrics
    tracker: IssueTrackerPort
    docs: DocsPort
    secrets: SecretsPort
    files: FilesPort
    email: EmailPort
    sms: SmsPort
    messaging: MessagingPort
    config_store: ConfigStorePort
    cache: CachePort
    bus: BusPort
    blob: BlobPort
    siem: SiemPort
    integration_lock: PostgresAdvisoryLock | None = None


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


def build_design_worker(
    *, resources: AppResources, project: ProjectRecord, provider: DesignProvider, owner: str
) -> WorkerLoop:
    """Compose the DESIGN-only worker around one provider.

    The DESIGN handlers are told who to attribute by asking the provider that
    was actually composed (`DesignProvider.engine_id`) rather than naming an
    engine here. The ledger is append-only, so an event that names the wrong
    actor is a correction no one can make: a sovereign run on qwenloop, or a
    scripted run with no engine at all, must not be recorded as claudeloop.
    """
    clock = SystemClock()
    dispatcher = JobDispatcher(
        {
            "design.interview": DesignInterviewHandler(
                ledger=resources.design_ledger,
                jobs=resources.jobs,
                gates=resources.gates,
                questions=provider,
                clock=clock,
                interviewer=provider.engine_id,
            ),
            "design.research": DesignResearchHandler(
                ledger=resources.design_ledger,
                researcher=provider,
                clock=clock,
                engine_id=provider.engine_id,
            ),
            "design.synthesize": DesignSynthesizeHandler(
                ledger=resources.design_ledger,
                synthesizer=provider,
                specs=resources.design_specs,
            ),
            "design.spec": DesignSpecHandler(specs=resources.design_specs),
        }
    )
    return WorkerLoop(
        jobs=resources.jobs,
        gates=resources.gates,
        handler=dispatcher,
        owner=owner,
        logger=StructlogAppLogger(owner=owner),
        notifications=getattr(resources, "notifications", None),
        notification_config=project.config,
        tracer=getattr(resources, "telemetry_tracer", None),
        metrics=getattr(resources, "telemetry_metrics", None),
        telemetry_enabled=_telemetry_enabled(project.config),
    )


def build_visual_worker(
    *,
    resources: AppResources,
    provider: VisualInventoryProducer,
    owner: str,
    project: ProjectRecord | None = None,
) -> WorkerLoop:
    dispatcher = JobDispatcher(
        {
            "visual.inventory": VisualInventoryHandler(
                ledger=resources.design_ledger,
                producer=provider,
                inventories=resources.visual_inventories,
                jobs=resources.jobs,
            ),
            "visual.plan": VisualPlanHandler(inventories=resources.visual_inventories),
        }
    )
    return WorkerLoop(
        jobs=resources.jobs,
        gates=resources.gates,
        handler=dispatcher,
        owner=owner,
        logger=StructlogAppLogger(owner=owner),
        notifications=getattr(resources, "notifications", None),
        notification_config=project.config if project is not None else None,
        tracer=getattr(resources, "telemetry_tracer", None),
        metrics=getattr(resources, "telemetry_metrics", None),
        telemetry_enabled=_telemetry_enabled(project.config if project is not None else {}),
    )


@dataclass(frozen=True, slots=True)
class _ClosureFactory:
    """JobHandlerFactory over a construction closure. The closures are
    defined inside build_full_worker, the only place allowed to see every
    concrete class -- keeping per-job construction (and per-job engine
    selection) in the composition root."""

    build: Callable[[JobRecord], Awaitable[JobHandler]]

    async def create(self, job: JobRecord) -> JobHandler:
        return await self.build(job)


_KIND_LEASES: Mapping[str, timedelta] = {
    # Engine-driven jobs run for hours; control-plane jobs for minutes.
    # Everything unlisted gets a 2-minute lease (still >> the heartbeat
    # interval of lease/3, so a healthy worker never loses one).
    "build.implement": timedelta(hours=2),
    "build.verify": timedelta(hours=2),
    "build.decompose": timedelta(minutes=15),
    "build.plan": timedelta(minutes=15),
    "build.integrate": timedelta(minutes=15),
}


def lease_for_kind(kind: str) -> timedelta:
    return _KIND_LEASES.get(kind, timedelta(minutes=2))


def _independent_review_required(config: Mapping[str, object]) -> bool:
    """Whether this project refuses a verify the implementer reviews itself.

    Default False: independence is waived when the pool cannot supply a second
    reviewer, because the measured alternative on a one-engine pool was BUILD
    deferring forever with no park and nothing in the ledger. A project that
    would rather stall than accept a self-review sets
    ``verify.require_independent_review = true`` and gets the strict rule back
    (ADR-0018: the choice belongs to the adopter, not to this file; ADR-0035
    records why the permissive reading is the default).
    """
    verify = config.get("verify")
    return isinstance(verify, Mapping) and verify.get("require_independent_review") is True


def _independence_policy(
    config: Mapping[str, object], pool: frozenset[EngineId], clock: Clock
) -> VerifyIndependencePolicy | None:
    """The verify-independence policy this project's config asks for, or None.

    A pool with nobody but the implementer in it verifies its own work and says
    so in the ledger, rather than deferring forever -- unless the project asked
    for the strict rule, in which case no policy is wired and the handler keeps
    failing such a verify (ADR-0035).

    Named rather than inlined at the call site so both arms are reachable from a
    test: the composition root builds its handlers inside closures that only run
    once a real job is dispatched, which would otherwise leave the strict arm
    exercised only by an end-to-end run against a live database.
    """
    if _independent_review_required(config):
        return None
    return VerifyIndependencePolicy(pool=pool, clock=clock)


def qwenloop_enabled(config: Mapping[str, object]) -> bool:
    """Return the resolved qwenloop feature switch for a project.

    The worker and CLI share ``LocalEngineSettings`` for all local engines; this
    compatibility helper keeps the long-standing bootstrap import while delegating
    precedence to that single resolver.
    """
    return LocalEngineSettings(environ=os.environ, config=config).enabled(EngineId.QWENLOOP)


def _telemetry_enabled(config: Mapping[str, object]) -> bool:
    """Resolve the project-level telemetry switch without importing infra config."""
    raw = config.get("telemetry")
    return not isinstance(raw, Mapping) or raw.get("enabled", True) is True


def build_full_worker(
    *,
    resources: AppResources,
    project: ProjectRecord,
    design_provider: DesignProvider,
    visual_provider: VisualInventoryProducer,
    decomposer: WorkPlanProducer,
    owner: str,
    engine_adapters: Mapping[EngineId, EngineAdapter] | None = None,
    allow_list: frozenset[EngineId] | None = None,
    azure_client: AzureClientPort | None = None,
) -> WorkerLoop:
    """The full-phase dispatcher: every job kind vibey enqueues, routed.

    `engine_adapters` overrides resources.engine_adapters -- the faked
    harness injects ScriptedEngines here instead of patching. Engine-driven
    BUILD jobs select their engine per job via the rotation stack
    (SelectingEngineProvider -> EngineSelector SWRR), honoring the
    `allow_list`; selection requires populated engine_health records
    (`vibey doctor --conformance --record` + the worker's startup preflight
    sweep). `azure_client` defaults to the in-memory adapter -- real `az`
    wiring is an explicit later decision, never an accidental default.
    """
    adapters = dict(engine_adapters if engine_adapters is not None else resources.engine_adapters)
    # The one resolver for "which local engines are on" (ADR-0038): the `worker`
    # command asks the same one, so the pool it preflights is the pool this runs.
    # An injected adapter wins (the faked harness passes ScriptedEngines here).
    local = LocalEngineSettings(environ=os.environ, config=project.config)
    for engine_id, local_adapter in local.adapters(LocalEndpointEnvironment(os.environ)).items():
        adapters.setdefault(engine_id, local_adapter)
    azure = azure_client if azure_client is not None else InMemoryAzureClientAdapter()
    clock = resources.clock
    notifications = getattr(resources, "notifications", None)
    telemetry_enabled = _telemetry_enabled(project.config)
    tracer = getattr(resources, "telemetry_tracer", None) if telemetry_enabled else None
    metrics = getattr(resources, "telemetry_metrics", None) if telemetry_enabled else None
    repo_root = Path(project.repo_path)
    deploy_state = FileDeploymentStateRepository(repo_root)
    deploy_design_ledger = PostgresReviewLedger(resources.ledger, phase=Phase.DEPLOY_DESIGN)
    deploy_execute_ledger = PostgresReviewLedger(resources.ledger, phase=Phase.DEPLOY_EXECUTE)
    engine_provider = SelectingEngineProvider(
        selector=resources.engine_selector,
        health=resources.engine_health_service,
        adapters=adapters,
        jobs=resources.jobs,
        clock=clock,
        owner=owner,
        allow_list=allow_list,
        local_engines=local.enabled_engines,
        metrics=metrics,
    )
    # The runaway brake: caps come from the project's own config
    # (max_cycle_dollars / max_cycle_turns, set at `vibey new`). Without
    # either, spend stays uncapped -- opting in is explicit, never a
    # silent default that would surprise existing projects. The parse is
    # LedgerBudgetSource's own, the same one `vibey cost` reports from.
    max_dollars, max_turns = LedgerBudgetSource.caps_from_config(project.config)
    budget_source: LedgerBudgetSource | None = None
    if max_dollars is not None or max_turns is not None:
        budget_source = LedgerBudgetSource(
            resources.ledger, max_dollars=max_dollars, max_turns=max_turns
        )
    wind_down = WindDownOrchestrator(
        ledger=resources.ledger,
        # The pool, like the provider's own selection: a wind-down must hand off to an
        # engine this worker can actually run, never to a stale health row's engine.
        handoff_service=RotationHandoffService(
            resources.engine_selector, allow_list=engine_provider.pool
        ),
        handoffs=resources.handoffs,
        jobs=resources.jobs,
        clock=clock,
        write_ledger=write_full_ledger,
        tracer=tracer,
        metrics=metrics,
    )
    skills_context = compiler_from_config(project.config, repo_path=repo_root)
    # One runner for every gate command -- build.verify's gates and diff,
    # build.integrate's gates, REVIEW's automated checks -- built from the
    # project's `gates` config (per-command timeout, kill grace, Python-env
    # isolation; ADR-0018). Unset keys keep the defaults.
    gate_runner = SubprocessGateRunner.from_config(project.config)

    def _recording(
        handler: JobHandler, adapter: EngineAdapter, meter: SpendMeteringLedger
    ) -> JobHandler:
        return RotationRecordingHandler(
            inner=handler,
            health=resources.engine_health_service,
            project_id=project.project_id,
            engine_id=adapter.descriptor.engine_id,
            meter=meter,
        )

    # One spend meter per job, around the ledger its handler writes through:
    # what the selected engine's session cost is charged to that engine's
    # health record when the job settles (issue #209). The ledger itself sees
    # every event unchanged.
    async def _implement(job: JobRecord) -> JobHandler:
        adapter = await engine_provider.select_for(job)
        meter = SpendMeteringLedger(resources.build_ledger, metrics=metrics)
        handler = BuildImplementHandler(
            worktrees=GitWorktreeManager(repo_root, cycle=job.cycle),
            provisioner=AgentSurfaceProvisioner(),
            engine=adapter,
            ledger=meter,
            jobs=resources.jobs,
            clock=clock,
            wind_down=wind_down,
            human_gates=resources.gates,
            budget_source=budget_source,
            skills_context=skills_context,
            tracer=tracer,
        )
        return _recording(handler, adapter, meter)

    async def _verify(job: JobRecord) -> JobHandler:
        adapter = await engine_provider.select_for(job)
        meter = SpendMeteringLedger(resources.build_ledger, metrics=metrics)
        handler = BuildVerifyHandler(
            worktrees=GitWorktreeManager(repo_root, cycle=job.cycle),
            gates=gate_runner,
            reviewer=adapter,
            ledger=meter,
            jobs=resources.jobs,
            clock=clock,
            repair=VerifyRepairPolicy(
                ledger_reader=resources.ledger, clock=clock, gates=resources.gates
            ),
            independence=_independence_policy(project.config, engine_provider.pool, clock),
            tracer=tracer,
        )
        return _recording(handler, adapter, meter)

    async def _integrate(job: JobRecord) -> JobHandler:
        return BuildIntegrateHandler(
            integration=IntegrationBranch(repo_root, cycle=job.cycle),
            gates=gate_runner,
            ledger=resources.build_ledger,
            jobs=resources.jobs,
            clock=clock,
            projects=resources.projects,
            lock=resources.integration_lock,
            ledger_reader=resources.ledger,
            human_gates=resources.gates,
        )

    handlers: dict[str, JobHandler] = {
        "design.interview": DesignInterviewHandler(
            ledger=resources.design_ledger,
            jobs=resources.jobs,
            gates=resources.gates,
            questions=design_provider,
            clock=clock,
            interviewer=design_provider.engine_id,
        ),
        "design.research": DesignResearchHandler(
            ledger=resources.design_ledger,
            researcher=design_provider,
            clock=clock,
            engine_id=design_provider.engine_id,
        ),
        "design.synthesize": DesignSynthesizeHandler(
            ledger=resources.design_ledger,
            synthesizer=design_provider,
            specs=resources.design_specs,
        ),
        "design.spec": DesignSpecHandler(specs=resources.design_specs),
        "visual.inventory": VisualInventoryHandler(
            ledger=resources.design_ledger,
            producer=visual_provider,
            inventories=resources.visual_inventories,
            jobs=resources.jobs,
        ),
        "visual.plan": VisualPlanHandler(inventories=resources.visual_inventories),
        "build.decompose": BuildDecomposeHandler(
            specs=resources.design_specs,
            decomposer=decomposer,
            jobs=resources.jobs,
        ),
        "review.demo": ReviewDemoHandler(
            specs=resources.design_specs,
            ledger=resources.review_ledger,
            artifacts=FileReviewArtifactWriter(resources.projects),
            jobs=resources.jobs,
            clock=clock,
            # REVIEW's automated checks are the project's own, not vibey's
            # guess: `review.security_commands` / `review.code_review_commands`
            # in the stored config JSON, read the same way the spend caps above
            # are (ADR-0018). Unset keys keep the defaults.
            automated_reviewer=SubprocessAutomatedReviewRunner.from_config(
                project.config,
                projects=resources.projects,
                gates=gate_runner,
            ),
        ),
        "review.collect": ReviewCollectHandler(
            ledger=resources.review_ledger,
            gates=resources.gates,
            jobs=resources.jobs,
            clock=clock,
        ),
        "review.triage": ReviewTriageHandler(
            ledger=resources.review_ledger,
            specs=resources.design_specs,
            jobs=resources.jobs,
            clock=clock,
            projects=resources.projects,
            spec_store=resources.design_specs,
        ),
        "review.deployment_choice": ReviewDeploymentChoiceHandler(
            ledger=resources.review_ledger,
            gates=resources.gates,
            jobs=resources.jobs,
            projects=resources.projects,
            clock=clock,
        ),
        "deploy.design": DeployDesignBridgeHandler(
            jobs=resources.jobs,
            projects=resources.projects,
        ),
        "deploy.interview": DeployInterviewHandler(
            ledger=deploy_design_ledger,
            gates=resources.gates,
            clock=clock,
            jobs=resources.jobs,
        ),
        "deploy.synthesize": DeploySynthesizeHandler(
            ledger=deploy_design_ledger,
            clock=clock,
            jobs=resources.jobs,
            spec_store=deploy_state,
        ),
        "deploy.spec": DeployAcceptanceHandler(
            ledger=deploy_design_ledger,
            gates=resources.gates,
            jobs=resources.jobs,
            projects=resources.projects,
            clock=clock,
            spec_provider=deploy_state.load_spec,
            consent_store=deploy_state,
        ),
        "deploy.execute": DeployExecuteHandler(
            ledger=deploy_execute_ledger,
            jobs=resources.jobs,
            projects=resources.projects,
            azure_client=azure,
            clock=clock,
            spec_provider=deploy_state.load_spec,
            consent_provider=deploy_state.load_consent,
        ),
        "deploy.demo": DeployReviewDemoHandler(
            ledger=resources.deploy_review_ledger,
            human_gates=resources.gates,
            jobs=resources.jobs,
            spec_provider=deploy_state.load_spec,
        ),
        "deploy.triage": DeployReviewTriageHandler(
            ledger=resources.deploy_review_ledger,
            human_gates=resources.gates,
            jobs=resources.jobs,
            spec_provider=deploy_state.load_spec,
        ),
        "deploy.route": DeployReviewRoutingHandler(
            ledger=resources.deploy_review_ledger,
            jobs=resources.jobs,
            projects=resources.projects,
            azure_client=azure,
            spec_provider=deploy_state.load_spec,
            consent_provider=deploy_state.load_consent,
        ),
    }
    # Alias kinds sharing a handler (the handlers themselves guard on both).
    handlers["build.plan"] = handlers["build.decompose"]
    handlers["deploy.accept"] = handlers["deploy.spec"]
    handlers["deploy.graph"] = handlers["deploy.execute"]

    dispatcher = JobDispatcher(
        handlers,
        factories={
            "build.implement": _ClosureFactory(_implement),
            "build.verify": _ClosureFactory(_verify),
            "build.integrate": _ClosureFactory(_integrate),
        },
    )
    return WorkerLoop(
        jobs=resources.jobs,
        gates=resources.gates,
        handler=dispatcher,
        owner=owner,
        lease_for_kind=lease_for_kind,
        logger=StructlogAppLogger(owner=owner),
        notifications=notifications,
        notification_config=project.config,
        tracer=tracer,
        metrics=metrics,
        telemetry_enabled=telemetry_enabled,
    )


class DatabaseNotConfigured(VibeyError):
    """VIBEY_PG_URL is unset and there is no safe default to invent."""

    def __init__(self) -> None:
        super().__init__(
            "VIBEY_PG_URL is not set. vibey will not guess a database.\n"
            "  export VIBEY_PG_URL=postgresql://user@localhost:5432/vibey"
        )


class UnsupportedPostgresVersion(VibeyError):
    """The configured database is below vibey's PostgreSQL compatibility floor."""

    def __init__(self, value: object) -> None:
        self.value = value
        super().__init__(
            f"PostgreSQL server version {value!r} is not supported; "
            f"vibey requires PostgreSQL {POSTGRES_MIN_MAJOR}+"
        )


def database_url() -> str:
    """The DSN, or an error -- never a guess.

    This used to fall back to postgresql://<user>@localhost:5432/vibey. That
    is not the resolution order the architecture describes (an explicit DSN,
    then a Compose service, then a managed cluster under .vibey/pgdata); it
    was an undocumented shortcut that resolved to whatever database happened
    to be named `vibey` on the machine.

    It cost real data integrity. Eight autonomous BUILD jobs ran the test
    suite in their worktrees with VIBEY_PG_URL unset; every test that called
    build_app() without an explicit url took this fallback and wrote to the
    PRODUCTION database, creating 78 projects in eleven minutes. Nothing
    failed, because a silent default cannot fail -- that is the whole
    problem with it. Refusing is the fix: a tool that writes to a database
    should be told which one.
    """
    url = os.environ.get("VIBEY_PG_URL")
    if not url:
        raise DatabaseNotConfigured
    return url


def migrations_dir() -> Path:
    """Resolved relative to this file so it works from a source checkout and
    from the image alike (/app/src/vibey/bootstrap.py -> /app/migrations).
    Derived in one place because two copies of this arithmetic would drift
    silently -- the image's layout depends on it."""
    return Path(__file__).resolve().parents[2] / "migrations"


@asynccontextmanager
async def build_app(
    *, url: str | None = None, config: VibeyConfig | None = None
) -> AsyncIterator[AppResources]:
    # Read before the pool opens, so a bad VIBEY_MIGRATION_LOCK_TIMEOUT_SECONDS
    # fails the start before anything touches the database.
    migrator: MigratorInterface = PostgresMigrator.from_environ(os.environ)
    pool = await asyncpg.create_pool(url or database_url(), min_size=1, max_size=10)
    if pool is None:
        raise RuntimeError("asyncpg did not create a pool")
    try:
        async with pool.acquire() as conn:
            server_version_num = await conn.fetchval("SHOW server_version_num")
            server_version = parse_postgres_server_version(server_version_num)
            if server_version is None or not server_version.supported:
                raise UnsupportedPostgresVersion(server_version_num)
            await migrator.apply(conn, discover_migrations(migrations_dir()))

        telemetry_tracer = TelemetryTracer()
        telemetry_metrics = TelemetryMetrics()
        notifications = NotificationService()
        projects = PostgresProjectRepository(
            pool,
            notifications=notifications,
        )
        ledger = PostgresLedgerRepository(pool)

        # Build rotation infrastructure (Phase E1)
        engine_health_repo = PostgresEngineHealthRepository(pool)
        rotation_cursors = PostgresRotationCursorRepository(pool)
        engine_health_service = EngineHealthService(engine_health_repo)
        conductor_preflight = ConductorPreflight(
            health=engine_health_service,
            feasibility=VibeyGhFeasibilityAdapter(),
        )
        engine_selector = EngineSelector(
            health_service=engine_health_service,
            cursor_repository=rotation_cursors,
            descriptors=BY_ENGINE_ID,
        )
        rotation_handoff = RotationHandoffService(engine_selector)

        # Build engine adapters
        engine_adapters = {
            desc.engine_id: LoopProcessAdapter(descriptor=desc) for desc in DEFAULT_DESCRIPTORS
        }

        resolved_config = config
        if resolved_config is None:
            try:
                from vibey.infrastructure.config_loader import load_config_from_path

                vibey_toml = Path("vibey.toml")
                if vibey_toml.is_file():
                    resolved_config = load_config_from_path(vibey_toml)
            except Exception:  # nosec B110 - a malformed optional vibey.toml must not block startup
                pass

        if (
            resolved_config
            and resolved_config.tracker.url
            and resolved_config.tracker.token
            and resolved_config.tracker.workspace_slug
            and resolved_config.tracker.project_id
        ):
            tracker_port: IssueTrackerPort = PlaneTrackerAdapter(
                url=resolved_config.tracker.url,
                token=resolved_config.tracker.token,
                workspace_slug=resolved_config.tracker.workspace_slug,
                project_id=resolved_config.tracker.project_id,
            )
        else:
            tracker_port = InMemoryTracker()

        if (
            resolved_config
            and resolved_config.docs.url
            and resolved_config.docs.token_id
            and resolved_config.docs.token_secret
        ):
            docs_port: DocsPort = BookStackDocsAdapter(
                url=resolved_config.docs.url,
                token_id=resolved_config.docs.token_id,
                token_secret=resolved_config.docs.token_secret,
                book_id=resolved_config.docs.book_id or 1,
            )
        else:
            docs_port = InMemoryDocs()

        if resolved_config and resolved_config.secrets.url and resolved_config.secrets.token:
            secrets_port: SecretsPort = OpenBaoSecretsAdapter(
                url=resolved_config.secrets.url,
                token=resolved_config.secrets.token,
            )
        else:
            secrets_port = InMemorySecrets()

        if (
            resolved_config
            and resolved_config.files.url
            and resolved_config.files.user
            and resolved_config.files.password
        ):
            files_port: FilesPort = NextcloudFilesAdapter(
                url=resolved_config.files.url,
                user=resolved_config.files.user,
                password=resolved_config.files.password,
            )
        else:
            files_port = InMemoryFiles()

        if resolved_config and resolved_config.email.smtp_host and resolved_config.email.smtp_port:
            email_port: EmailPort = ForwardEmailAdapter(
                smtp_host=resolved_config.email.smtp_host,
                smtp_port=resolved_config.email.smtp_port,
                username=resolved_config.email.username,
                password=resolved_config.email.password,
                from_email=resolved_config.email.from_email,
            )
        else:
            email_port = InMemoryEmail()

        if (
            resolved_config
            and resolved_config.sms.url
            and resolved_config.sms.username
            and resolved_config.sms.password
        ):
            sms_port: SmsPort = KannelSmsAdapter(
                url=resolved_config.sms.url,
                username=resolved_config.sms.username,
                password=resolved_config.sms.password,
                sender=resolved_config.sms.sender or "vibey",
            )
        else:
            sms_port = InMemorySms()

        if resolved_config and resolved_config.messaging.url and resolved_config.messaging.token:
            messaging_port: MessagingPort = MatrixMessagingAdapter(
                url=resolved_config.messaging.url,
                token=resolved_config.messaging.token,
            )
        else:
            messaging_port = InMemoryMessaging()

        if (
            resolved_config
            and resolved_config.config_store.url
            and resolved_config.config_store.token
            and resolved_config.config_store.project_id
        ):
            from vibey.infrastructure.config_store.infisical import InfisicalConfigStoreAdapter

            config_store_port: ConfigStorePort = InfisicalConfigStoreAdapter(
                url=resolved_config.config_store.url,
                token=resolved_config.config_store.token,
                project_id=resolved_config.config_store.project_id,
                environment=resolved_config.config_store.environment,
            )
        else:
            from vibey.infrastructure.config_store.in_memory import InMemoryConfigStore

            config_store_port = InMemoryConfigStore()

        if resolved_config and resolved_config.cache.url:
            from vibey.infrastructure.cache.redis import RedisCacheAdapter

            cache_port: CachePort = RedisCacheAdapter(url=resolved_config.cache.url)
        else:
            from vibey.infrastructure.cache.in_memory import InMemoryCache

            cache_port = InMemoryCache()

        if (
            resolved_config
            and resolved_config.bus.url
            and resolved_config.bus.username
            and resolved_config.bus.password
        ):
            from vibey.infrastructure.bus.rabbitmq import RabbitMqBusAdapter

            bus_port: BusPort = RabbitMqBusAdapter(
                url=resolved_config.bus.url,
                username=resolved_config.bus.username,
                password=resolved_config.bus.password,
            )
        else:
            from vibey.infrastructure.bus.in_memory import InMemoryBus

            bus_port = InMemoryBus()

        if (
            resolved_config
            and resolved_config.blob.url
            and resolved_config.blob.access_key
            and resolved_config.blob.secret_key
        ):
            from vibey.infrastructure.blob.garage import GarageBlobAdapter

            blob_port: BlobPort = GarageBlobAdapter(
                url=resolved_config.blob.url,
                access_key=resolved_config.blob.access_key,
                secret_key=resolved_config.blob.secret_key,
                region=resolved_config.blob.region,
            )
        else:
            from vibey.infrastructure.blob.in_memory import InMemoryBlob

            blob_port = InMemoryBlob()

        if resolved_config and resolved_config.siem.url:
            from vibey.infrastructure.siem.wazuh import WazuhSiemAdapter

            siem_port: SiemPort = WazuhSiemAdapter(
                url=resolved_config.siem.url,
                username=resolved_config.siem.username,
                password=resolved_config.siem.password,
            )
        else:
            from vibey.infrastructure.siem.in_memory import InMemorySiem

            siem_port = InMemorySiem()

        yield AppResources(
            projects=projects,
            jobs=PostgresJobRepository(pool),
            gates=PostgresHumanGateRepository(pool),
            ledger=ledger,
            design_ledger=PostgresDesignLedger(ledger),
            design_specs=FileDesignSpecRepository(projects),
            visual_inventories=FileVisualInventoryRepository(projects),
            build_ledger=PostgresBuildLedger(ledger),
            review_ledger=PostgresReviewLedger(ledger),
            deploy_review_ledger=PostgresReviewLedger(ledger, phase=Phase.DEPLOY_REVIEW),
            engine_health_repo=engine_health_repo,
            rotation_cursors=rotation_cursors,
            engine_health_service=engine_health_service,
            conductor_preflight=conductor_preflight,
            engine_selector=engine_selector,
            rotation_handoff=rotation_handoff,
            engine_adapters=engine_adapters,
            handoffs=PostgresHandoffRepository(pool),
            clock=SystemClock(),
            notifications=notifications,
            telemetry_tracer=telemetry_tracer,
            telemetry_metrics=telemetry_metrics,
            tracker=tracker_port,
            docs=docs_port,
            secrets=secrets_port,
            files=files_port,
            email=email_port,
            sms=sms_port,
            messaging=messaging_port,
            config_store=config_store_port,
            cache=cache_port,
            bus=bus_port,
            blob=blob_port,
            siem=siem_port,
            integration_lock=PostgresAdvisoryLock(pool),
        )
    finally:
        await pool.close()


# Re-exported for the same reason `application/ports.py` re-exports the
# interfaces package: the seam moved, the import path should not break.
__all__ = [
    "DesignProvider",
    "VisualInventoryProducer",
]
