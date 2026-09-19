# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Contracts for application classes that are more specific than a shared port.

The application ports remain the dependency-inversion seams.  These named
contracts mirror the concrete classes that carry application state or add
policy to a shared port, so a refactor cannot silently change that narrower
surface while still satisfying a broad ``JobHandler`` or ``Logger`` protocol.
Interfaces declare; they never consume infrastructure implementations.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import UUID

from vibey.application.dto import JobRecord
from vibey.application.interfaces.build import SkillsContextCompiler, SkillsContextResult
from vibey.application.interfaces.engines import EngineAdapter, EngineProvider
from vibey.application.interfaces.observability import Logger
from vibey.application.interfaces.queue import JobHandler, Outcome
from vibey.domain.circuit import StoredCircuitState
from vibey.domain.engine import EngineId, JobRequirement, StoredEngineId
from vibey.domain.phase import Phase, StoredPhase


@runtime_checkable
class EnqueueRequestInterface(Protocol):
    @property
    def project_id(self) -> UUID: ...

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> Phase: ...

    @property
    def kind(self) -> str: ...

    @property
    def idempotency_key(self) -> str: ...

    @property
    def payload(self) -> Mapping[str, object]: ...

    @property
    def requirement(self) -> Mapping[str, object]: ...

    @property
    def priority(self) -> int: ...

    @property
    def work_item_id(self) -> str | None: ...

    @property
    def max_attempts(self) -> int: ...

    @property
    def run_after(self) -> datetime | None: ...

    @property
    def depends_on(self) -> tuple[UUID, ...]: ...

    @property
    def depends_on_keys(self) -> tuple[str, ...]: ...


@runtime_checkable
class ProjectRecordInterface(Protocol):
    @property
    def project_id(self) -> UUID: ...

    @property
    def name(self) -> str: ...

    @property
    def repo_path(self) -> Path: ...

    @property
    def phase(self) -> StoredPhase: ...

    @property
    def cycle(self) -> int: ...

    @property
    def max_cycles(self) -> int: ...

    @property
    def config(self) -> Mapping[str, object]: ...

    @property
    def created_at(self) -> datetime: ...

    @property
    def updated_at(self) -> datetime: ...


@runtime_checkable
class JobRecordInterface(Protocol):
    @property
    def id(self) -> UUID: ...

    @property
    def project_id(self) -> UUID: ...

    @property
    def cycle(self) -> int: ...

    @property
    def phase(self) -> StoredPhase: ...

    @property
    def kind(self) -> str: ...

    @property
    def state(self) -> object: ...

    @property
    def priority(self) -> int: ...

    @property
    def work_item_id(self) -> str | None: ...

    @property
    def payload(self) -> Mapping[str, object]: ...

    @property
    def requirement(self) -> Mapping[str, object]: ...

    @property
    def idempotency_key(self) -> str: ...

    @property
    def attempts(self) -> int: ...

    @property
    def max_attempts(self) -> int: ...

    @property
    def run_after(self) -> datetime: ...

    @property
    def lease_owner(self) -> str | None: ...

    @property
    def lease_expires_at(self) -> datetime | None: ...

    @property
    def assigned_engine(self) -> str | None: ...

    @property
    def last_error(self) -> Mapping[str, object] | None: ...

    @property
    def created_at(self) -> datetime: ...

    @property
    def updated_at(self) -> datetime: ...


@runtime_checkable
class EngineHealthRecordInterface(Protocol):
    @property
    def project_id(self) -> UUID: ...

    @property
    def engine_id(self) -> StoredEngineId: ...

    @property
    def installed(self) -> bool: ...

    @property
    def version(self) -> str | None: ...

    @property
    def conformance_ok(self) -> bool: ...

    @property
    def conformance_at(self) -> datetime | None: ...

    @property
    def auth_ok_at(self) -> datetime | None: ...

    @property
    def circuit(self) -> StoredCircuitState: ...

    @property
    def capacity_state(self) -> str | None: ...

    @property
    def resets_at(self) -> datetime | None: ...

    @property
    def probe_next_at(self) -> datetime | None: ...

    @property
    def probe_attempt(self) -> int: ...

    @property
    def consecutive_fail(self) -> int: ...

    @property
    def ewma_failure(self) -> float: ...

    @property
    def cost_usd_cycle(self) -> float: ...

    @property
    def selected_count(self) -> int: ...


@runtime_checkable
class RotationCursorInterface(Protocol):
    @property
    def project_id(self) -> UUID: ...

    @property
    def engine_id(self) -> StoredEngineId: ...

    @property
    def current(self) -> int: ...

    @property
    def order(self) -> int: ...


@runtime_checkable
class SelectionInputsInterface(Protocol):
    @property
    def requirement(self) -> JobRequirement: ...

    @property
    def affinity(self) -> EngineId | None: ...

    @property
    def independence_waived(self) -> bool: ...


@runtime_checkable
class SelectingEngineProviderInterface(EngineProvider, Protocol):
    @property
    def pool(self) -> frozenset[EngineId]: ...

    async def select_for(self, job: JobRecord) -> EngineAdapter: ...


@runtime_checkable
class RotationRecordingHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class BuildDecomposeHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class BuildImplementHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class BuildIntegrateHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class BuildVerifyHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class DeploySynthesizeHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class DeployReviewDemoHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class DeployReviewTriageHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class DesignInterviewHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class DesignResearchHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class ReviewDemoHandlerInterface(JobHandler, Protocol):
    async def handle(self, job: JobRecord) -> Outcome: ...


@runtime_checkable
class StandardLibraryLoggerInterface(Logger, Protocol):
    def bind(self, **kwargs: object) -> Logger: ...

    def debug(self, event: str, **kwargs: object) -> None: ...

    def info(self, event: str, **kwargs: object) -> None: ...

    def warning(self, event: str, **kwargs: object) -> None: ...

    def error(self, event: str, **kwargs: object) -> None: ...


@runtime_checkable
class VibeySkillsContextCompilerInterface(SkillsContextCompiler, Protocol):
    async def compile(self, *, job: object, worktree_path: Path) -> SkillsContextResult: ...


@runtime_checkable
class VerifyIndependencePolicyInterface(Protocol):
    @property
    def pool(self) -> frozenset[EngineId]: ...

    @property
    def clock(self) -> object: ...


@runtime_checkable
class RunOutcomeInterface(Protocol):
    @property
    def complete(self) -> bool: ...

    @property
    def capacity_rejected(self) -> bool: ...

    @property
    def exit_code(self) -> int | None: ...

    @property
    def diagnostic_tail(self) -> str: ...

    def misconfiguration_gate(self, descriptor: object, work_item_id: str | None) -> object:
        """Return the repair gate for backend exit 78, or ``None``."""
        ...
