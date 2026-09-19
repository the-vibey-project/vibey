# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Infrastructure-internal seams.

These are not application ports -- nothing outside infrastructure/ implements
them. They live here so the `every class has an interface in interfaces/`
rule holds at every layer, not just the application boundary.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

from vibey.application.dto import RunSpec
from vibey.infrastructure.interfaces.class_contracts import (
    ClaudeLoopDesignProviderInterface,
    ClaudeLoopWorkPlanProducerInterface,
    ConnectionEventAppenderInterface,
    InvalidMigrationLockTimeoutInterface,
    JsonlShardStoreInterface,
    LocalEngineSwitchInterface,
    LoopProcessAdapterInterface,
    MigrationInsideTransactionInterface,
    MigrationLockTimeoutInterface,
    PostgresBuildLedgerInterface,
    PostgresDesignLedgerInterface,
    PostgresEngineHealthRepositoryInterface,
    PostgresJobRepositoryInterface,
    PostgresLedgerRepositoryInterface,
    PostgresLedgerSearchRepositoryInterface,
    PostgresMigratorInterface,
    PostgresProjectRepositoryInterface,
    PostgresReviewLedgerInterface,
    PostgresRotationCursorRepositoryInterface,
    ScriptedDesignProviderInterface,
    StaticSiteWriterInterface,
    SubprocessAutomatedReviewRunnerInterface,
    SubprocessGateRunnerInterface,
    TierManagerInterface,
    UrllibOllamaTransportInterface,
    VibeyGhFeasibilityAdapterInterface,
    VibeySkillsContextCompilerInterface,
    ZlibCodecInterface,
)
from vibey.infrastructure.interfaces.cluster_preflight_interface import (
    ClusterPreflightInterface,
    EngineAuthCheckInterface,
)
from vibey.infrastructure.interfaces.logging_interface import CorrelationLogContextInterface

if TYPE_CHECKING:  # concrete result types live beside their adapter
    from vibey.infrastructure.engines.claudeloop_process import (
        ClaudeLoopResult,
        CommandResult,
    )


@runtime_checkable
class BoundedClaudeLoop(Protocol):
    async def run(self, spec: RunSpec, *, web_search: bool = False) -> ClaudeLoopResult: ...


@runtime_checkable
class CommandExecutor(Protocol):
    async def execute(self, argv: tuple[str, ...]) -> CommandResult: ...


__all__ = [
    "BoundedClaudeLoop",
    "ClaudeLoopDesignProviderInterface",
    "ClaudeLoopWorkPlanProducerInterface",
    "ClusterPreflightInterface",
    "CommandExecutor",
    "ConnectionEventAppenderInterface",
    "CorrelationLogContextInterface",
    "EngineAuthCheckInterface",
    "InvalidMigrationLockTimeoutInterface",
    "JsonlShardStoreInterface",
    "LocalEngineSwitchInterface",
    "LoopProcessAdapterInterface",
    "MigrationInsideTransactionInterface",
    "MigrationLockTimeoutInterface",
    "PostgresBuildLedgerInterface",
    "PostgresDesignLedgerInterface",
    "PostgresEngineHealthRepositoryInterface",
    "PostgresJobRepositoryInterface",
    "PostgresLedgerRepositoryInterface",
    "PostgresLedgerSearchRepositoryInterface",
    "PostgresMigratorInterface",
    "PostgresProjectRepositoryInterface",
    "PostgresReviewLedgerInterface",
    "PostgresRotationCursorRepositoryInterface",
    "ScriptedDesignProviderInterface",
    "StaticSiteWriterInterface",
    "SubprocessAutomatedReviewRunnerInterface",
    "SubprocessGateRunnerInterface",
    "TierManagerInterface",
    "UrllibOllamaTransportInterface",
    "VibeySkillsContextCompilerInterface",
    "VibeyGhFeasibilityAdapterInterface",
    "ZlibCodecInterface",
]
