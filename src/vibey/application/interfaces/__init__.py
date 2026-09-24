# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Application interfaces -- every seam implemented by infrastructure/ and
never imported from it.

One module per collaborator family, plus the DTOs that are part of a seam's
vocabulary. Nine structurally identical `*Ledger` Protocols collapsed into
`PhaseLedger`, five identical `ProjectTransitioner`s and four `ProjectStore`s
into one each, and two spec readers into `DesignSpecReader`: they were the
same seam re-declared beside every handler that needed it.
"""

from __future__ import annotations

from vibey.application.interfaces.azure import (
    AzureClientPort,
    AzureDiscoveryResult,
    AzureExecutionResult,
    AzureResourceStatus,
    CloudClientPort,
    DeploymentConsentStore,
    DeploymentSpecStore,
)
from vibey.application.interfaces.blob import BlobPort
from vibey.application.interfaces.budget_source_interface import (
    LedgerBudgetSourceInterface,
)
from vibey.application.interfaces.build import (
    BudgetSource,
    BuildProvisioner,
    BuildWorktrees,
    GateResult,
    GateRunner,
    IntegrationBranch,
    IntegrationLock,
    MergeOutcome,
    SkillsContextCompiler,
    SkillsContextResult,
    VerifyWorktrees,
    WorkPlanProducer,
)
from vibey.application.interfaces.bus import BusPort
from vibey.application.interfaces.cache import CachePort
from vibey.application.interfaces.class_contracts import (
    BuildDecomposeHandlerInterface,
    BuildImplementHandlerInterface,
    BuildIntegrateHandlerInterface,
    BuildVerifyHandlerInterface,
    DeployReviewDemoHandlerInterface,
    DeployReviewTriageHandlerInterface,
    DeploySynthesizeHandlerInterface,
    DesignInterviewHandlerInterface,
    DesignResearchHandlerInterface,
    EngineHealthRecordInterface,
    EnqueueRequestInterface,
    JobRecordInterface,
    ProjectRecordInterface,
    ReviewDemoHandlerInterface,
    RotationCursorInterface,
    RotationRecordingHandlerInterface,
    RunOutcomeInterface,
    SelectingEngineProviderInterface,
    SelectionInputsInterface,
    StandardLibraryLoggerInterface,
    VerifyIndependencePolicyInterface,
    VibeySkillsContextCompilerInterface,
)
from vibey.application.interfaces.config_store import ConfigStorePort
from vibey.application.interfaces.design import (
    DesignProvider,
    DesignQuestionProvider,
    DesignSpecReader,
    DesignSpecRepository,
    ResearchProvider,
    SpecSynthesizer,
)
from vibey.application.interfaces.docs import DocsPort
from vibey.application.interfaces.email import EmailPort
from vibey.application.interfaces.engines import (
    EngineAdapter,
    EngineHealthRepository,
    EngineHealthServiceInterface,
    EngineProvider,
    EngineSelectorInterface,
    RotationCursorRepository,
)
from vibey.application.interfaces.files import FilesPort
from vibey.application.interfaces.gates import (
    HumanGateRepository,
)
from vibey.application.interfaces.ledger import (
    BriefProducer,
    BuildLedger,
    DesignLedger,
    HandoffStore,
    LedgerReader,
    LedgerSearch,
    LedgerShardStore,
    LedgerSiteWriter,
    PhaseLedger,
    SpendMeteringLedgerInterface,
)
from vibey.application.interfaces.ledger_publication_interface import (
    InvalidLedgerShardInterface,
    LedgerExporterInterface,
    LedgerShardInterface,
    LedgerSiteBuilderInterface,
    LedgerSitePlanInterface,
    SearchTokenizerInterface,
    ShardHeaderInterface,
    ShardHoldingInterface,
)
from vibey.application.interfaces.messaging import MessagingPort
from vibey.application.interfaces.observability import (
    Logger,
    NotificationSink,
    TelemetryMetrics,
    TelemetrySpan,
    TelemetryTracer,
)
from vibey.application.interfaces.preflight_interface import (
    ConductorPreflightInterface,
    FeasibilityAssessmentInterface,
    PreflightHealthServiceInterface,
    RunFeasibilityEvaluatorInterface,
    StartupPreflightReportInterface,
)
from vibey.application.interfaces.projects import (
    ProjectStore,
    ProjectTransitioner,
)
from vibey.application.interfaces.queue import (
    Defer,
    Failure,
    JobHandler,
    JobHandlerFactory,
    JobReadyNotifier,
    JobRepository,
    Outcome,
    Park,
    Success,
)
from vibey.application.interfaces.queue_priority import (
    CallerIdentity,
    JobPriorityStore,
    PriorityGrantReader,
    QueuePriorityServiceInterface,
)
from vibey.application.interfaces.queue_reap import (
    BusDeadLetterGateInterface,
    BusDeadLetterHandlerInterface,
    BusInspectorPort,
    DeliveryExhaustedGateInterface,
    QueueReaperInterface,
    QueueReapStore,
)
from vibey.application.interfaces.review import (
    AutomatedFinding,
    AutomatedReviewRunner,
    ReviewArtifactWriter,
)
from vibey.application.interfaces.secrets import SecretsPort
from vibey.application.interfaces.siem import SiemPort
from vibey.application.interfaces.sms import SmsPort
from vibey.application.interfaces.system import (
    Clock,
)
from vibey.application.interfaces.tracker import IssueTrackerPort
from vibey.application.interfaces.visual import (
    VisualInventoryProducer,
    VisualInventoryRepository,
)
from vibey.application.interfaces.worker_interface import (
    WorkerLoopInterface,
)

__all__ = [
    "Logger",
    "NotificationSink",
    "TelemetryMetrics",
    "TelemetrySpan",
    "TelemetryTracer",
    "AutomatedFinding",
    "AutomatedReviewRunner",
    "AzureClientPort",
    "CloudClientPort",
    "DeploymentConsentStore",
    "DeploymentSpecStore",
    "AzureDiscoveryResult",
    "AzureExecutionResult",
    "AzureResourceStatus",
    "BuildDecomposeHandlerInterface",
    "BuildImplementHandlerInterface",
    "BuildIntegrateHandlerInterface",
    "BuildVerifyHandlerInterface",
    "BriefProducer",
    "BudgetSource",
    "SkillsContextCompiler",
    "SkillsContextResult",
    "BuildLedger",
    "BuildProvisioner",
    "BuildWorktrees",
    "Clock",
    "ConductorPreflightInterface",
    "Defer",
    "DesignLedger",
    "DesignProvider",
    "DesignQuestionProvider",
    "DesignInterviewHandlerInterface",
    "DesignResearchHandlerInterface",
    "DesignSpecReader",
    "DesignSpecRepository",
    "EngineAdapter",
    "EngineHealthRepository",
    "EngineHealthServiceInterface",
    "EngineHealthRecordInterface",
    "EngineProvider",
    "EngineSelectorInterface",
    "RotationCursorRepository",
    "Failure",
    "FeasibilityAssessmentInterface",
    "GateResult",
    "GateRunner",
    "HandoffStore",
    "HumanGateRepository",
    "IntegrationBranch",
    "IntegrationLock",
    "JobHandler",
    "JobHandlerFactory",
    "JobRecordInterface",
    "CallerIdentity",
    "JobPriorityStore",
    "PriorityGrantReader",
    "JobReadyNotifier",
    "JobRepository",
    "QueuePriorityServiceInterface",
    "BusDeadLetterGateInterface",
    "BusDeadLetterHandlerInterface",
    "BusInspectorPort",
    "DeliveryExhaustedGateInterface",
    "QueueReaperInterface",
    "QueueReapStore",
    "LedgerExporterInterface",
    "InvalidLedgerShardInterface",
    "LedgerBudgetSourceInterface",
    "LedgerReader",
    "LedgerSearch",
    "LedgerShardInterface",
    "LedgerShardStore",
    "LedgerSiteBuilderInterface",
    "LedgerSitePlanInterface",
    "LedgerSiteWriter",
    "MergeOutcome",
    "Outcome",
    "Park",
    "PhaseLedger",
    "ProjectStore",
    "ProjectRecordInterface",
    "ProjectTransitioner",
    "PreflightHealthServiceInterface",
    "ResearchProvider",
    "RunFeasibilityEvaluatorInterface",
    "ReviewArtifactWriter",
    "ReviewDemoHandlerInterface",
    "RotationCursorInterface",
    "RotationRecordingHandlerInterface",
    "RunOutcomeInterface",
    "SearchTokenizerInterface",
    "SelectingEngineProviderInterface",
    "SelectionInputsInterface",
    "ShardHoldingInterface",
    "ShardHeaderInterface",
    "SpecSynthesizer",
    "SpendMeteringLedgerInterface",
    "StandardLibraryLoggerInterface",
    "StartupPreflightReportInterface",
    "Success",
    "VerifyWorktrees",
    "VerifyIndependencePolicyInterface",
    "VibeySkillsContextCompilerInterface",
    "VisualInventoryProducer",
    "VisualInventoryRepository",
    "WorkerLoopInterface",
    "WorkPlanProducer",
    "DeployReviewDemoHandlerInterface",
    "DeployReviewTriageHandlerInterface",
    "DeploySynthesizeHandlerInterface",
    "EnqueueRequestInterface",
    "IssueTrackerPort",
    "DocsPort",
    "SecretsPort",
    "FilesPort",
    "EmailPort",
    "SmsPort",
    "MessagingPort",
    "ConfigStorePort",
    "CachePort",
    "BusPort",
    "BlobPort",
    "SiemPort",
]
