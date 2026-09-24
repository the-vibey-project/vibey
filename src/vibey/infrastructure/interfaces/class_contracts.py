# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Named contracts for concrete infrastructure adapters.

The application ports describe the cross-layer surface.  These narrower
contracts also preserve adapter-specific construction and helper capabilities
without making application code depend on a concrete implementation.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol, runtime_checkable

from vibey.application.interfaces import (
    BuildLedger,
    CallerIdentity,
    DesignProvider,
    EngineAdapter,
    EngineHealthRepository,
    JobPriorityStore,
    JobRepository,
    LedgerSearch,
    LedgerShardStore,
    LedgerSiteWriter,
    PhaseLedger,
    PriorityGrantReader,
    ProjectStore,
    RotationCursorRepository,
    RunFeasibilityEvaluatorInterface,
    SkillsContextCompiler,
    WorkPlanProducer,
)
from vibey.domain.interfaces.config_interface import QueueConfigInterface
from vibey.infrastructure.build.interfaces import (
    ConfigurableAutomatedReviewRunnerInterface,
    ConfigurableGateRunnerInterface,
)
from vibey.infrastructure.db.interfaces import EventAppenderInterface, MigratorInterface
from vibey.infrastructure.engines.interfaces import OllamaTransportInterface
from vibey.infrastructure.ledger.interfaces import CompressionCodecInterface


@runtime_checkable
class SubprocessAutomatedReviewRunnerInterface(
    ConfigurableAutomatedReviewRunnerInterface, Protocol
): ...


@runtime_checkable
class SubprocessGateRunnerInterface(ConfigurableGateRunnerInterface, Protocol):
    """The configurable subprocess gate adapter."""


@runtime_checkable
class PostgresBuildLedgerInterface(BuildLedger, Protocol):
    """The Postgres implementation of the BUILD ledger port."""


@runtime_checkable
class PostgresDesignLedgerInterface(Protocol):
    async def append(self, *args: object, **kwargs: object) -> None: ...

    async def all_for_project(self, project_id: object) -> tuple[object, ...]: ...


@runtime_checkable
class PostgresEngineHealthRepositoryInterface(EngineHealthRepository, Protocol):
    """The Postgres implementation of the engine-health repository port."""


@runtime_checkable
class PostgresJobRepositoryInterface(JobRepository, Protocol):
    """The Postgres implementation of the durable job repository port."""


@runtime_checkable
class PostgresJobPriorityStoreInterface(JobPriorityStore, Protocol):
    """The Postgres implementation of the queue-priority store (ADR-0054)."""


@runtime_checkable
class ProjectPriorityGrantReaderInterface(PriorityGrantReader, Protocol):
    """Reads a project's grant from `<repo_path>/vibey.toml`, and nowhere else."""


@runtime_checkable
class ProcessCallerInterface(CallerIdentity, Protocol):
    """The account this process runs as: uid from the OS, name from pwd."""


@runtime_checkable
class QueueConfigLoaderInterface(Protocol):
    """Reads `[queue]` from a vibey.toml, and only `[queue]`."""

    def load(self, path: Path) -> QueueConfigInterface:
        """The declared queue policy. A missing file declares nothing -- the operator
        alone may reorder -- and a malformed one raises rather than being read as
        empty, so a broken declaration is never mistaken for none."""
        ...


@runtime_checkable
class ConnectionEventAppenderInterface(EventAppenderInterface, Protocol):
    """Appends a draft on a caller-owned connection."""


@runtime_checkable
class PostgresLedgerRepositoryInterface(Protocol):
    async def append(self, draft: object) -> object: ...

    async def range(
        self, project_id: object, *, from_seq: int, to_seq: int
    ) -> tuple[object, ...]: ...

    async def all_for_project(self, project_id: object) -> tuple[object, ...]: ...

    async def latest_seq(self, project_id: object) -> int: ...


@runtime_checkable
class PostgresLedgerSearchRepositoryInterface(LedgerSearch, Protocol):
    """The Postgres implementation of the searchable-ledger port."""


@runtime_checkable
class MigrationLockTimeoutInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class InvalidMigrationLockTimeoutInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class MigrationInsideTransactionInterface(Protocol):
    @property
    def args(self) -> tuple[object, ...]: ...


@runtime_checkable
class PostgresMigratorInterface(MigratorInterface, Protocol):
    @property
    def lock_timeout_seconds(self) -> float: ...


@runtime_checkable
class PostgresProjectRepositoryInterface(ProjectStore, Protocol):
    async def create(self, *args: object, **kwargs: object) -> object: ...

    async def get_latest(self) -> object: ...


@runtime_checkable
class PostgresReviewLedgerInterface(PhaseLedger, Protocol):
    """The phase-ledger adapter used by review and deployment stages."""


@runtime_checkable
class PostgresRotationCursorRepositoryInterface(RotationCursorRepository, Protocol):
    """The Postgres implementation of the rotation cursor port."""


@runtime_checkable
class ClaudeLoopWorkPlanProducerInterface(WorkPlanProducer, Protocol):
    """The paid Claude-loop decomposition provider."""


@runtime_checkable
class ClaudeLoopDesignProviderInterface(DesignProvider, Protocol):
    """The paid Claude-loop design provider."""


@runtime_checkable
class LocalEngineSwitchInterface(Protocol):
    @property
    def engine_id(self) -> object: ...

    @property
    def feature_key(self) -> str: ...

    def env_var(self) -> str: ...


@runtime_checkable
class LoopProcessAdapterInterface(EngineAdapter, Protocol):
    def help_text(self) -> str | None: ...

    def run_exit_code(self, handle: object) -> int | None: ...

    def diagnostic_tail(self, handle: object) -> str: ...

    def release_diagnostics(self, handle: object) -> None: ...


@runtime_checkable
class UrllibOllamaTransportInterface(OllamaTransportInterface, Protocol):
    """The stdlib HTTP transport used by the local chat client."""


@runtime_checkable
class ScriptedDesignProviderInterface(DesignProvider, Protocol):
    """The deterministic provider used by demos and tests."""


@runtime_checkable
class JsonlShardStoreInterface(LedgerShardStore, Protocol):
    def path(self, forge_class: str) -> Path: ...


@runtime_checkable
class StaticSiteWriterInterface(LedgerSiteWriter, Protocol):
    """Writes the planned static ledger site."""


@runtime_checkable
class VibeySkillsContextCompilerInterface(SkillsContextCompiler, Protocol):
    """Compiles repository skills into an application context packet."""


@runtime_checkable
class VibeyGhFeasibilityAdapterInterface(RunFeasibilityEvaluatorInterface, Protocol):
    """Adapts vibey-gh's three-valued feasibility engine to the conductor."""


@runtime_checkable
class TierManagerInterface(Protocol):
    def reconcile_tiers(self, project_id: object, config: object) -> tuple[int, int]: ...

    def get_event(self, project_id: object, seq: int) -> object: ...

    def get_range(self, project_id: object, from_seq: int, to_seq: int) -> tuple[object, ...]: ...


@runtime_checkable
class ZlibCodecInterface(CompressionCodecInterface, Protocol):
    """The zlib implementation of the lossless compression port."""
