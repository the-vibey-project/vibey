# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Data transfer objects crossing the application/infrastructure boundary.
Unlike domain/ types these may be mutated by callers and are not required to
be pure -- they are shapes, not behavior."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID

from vibey.domain.circuit import StoredCircuitState
from vibey.domain.effort import Effort
from vibey.domain.engine import EngineId, IsolationLevel, StoredEngineId
from vibey.domain.job import FailureClass, StoredJobState
from vibey.domain.phase import Phase, StoredPhase


@dataclass(frozen=True, slots=True)
class EnqueueRequest:
    project_id: UUID
    cycle: int
    phase: Phase
    kind: str
    idempotency_key: str
    payload: Mapping[str, object] = field(default_factory=dict)
    requirement: Mapping[str, object] = field(default_factory=dict)
    priority: int = 0
    work_item_id: str | None = None
    max_attempts: int = 7
    run_after: datetime | None = None
    depends_on: tuple[UUID, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectRecord:
    """A project row. `phase` is read forward-compatibly (vibey#287): a phase a
    newer vibey added comes back as an `UnrecognizedPhase`, and a worker that meets
    one declines the project rather than guessing what the phase means."""

    project_id: UUID
    name: str
    repo_path: Path
    phase: StoredPhase
    cycle: int
    max_cycles: int
    config: Mapping[str, object]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class JobRecord:
    """A job row. `phase` and `state` are read forward-compatibly (vibey#287);
    the claim never hands a worker a job whose phase it does not know."""

    id: UUID
    project_id: UUID
    cycle: int
    phase: StoredPhase
    kind: str
    state: StoredJobState
    priority: int
    work_item_id: str | None
    payload: Mapping[str, object]
    requirement: Mapping[str, object]
    idempotency_key: str
    attempts: int
    max_attempts: int
    run_after: datetime
    lease_owner: str | None
    lease_expires_at: datetime | None
    assigned_engine: str | None
    last_error: Mapping[str, object] | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class HumanGateRequest:
    kind: str
    prompt: str
    options: tuple[str, ...] = ()
    default_answer: str | None = None
    timeout_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class HumanGateRecord:
    gate_id: UUID
    project_id: UUID
    job_id: UUID | None
    kind: str
    prompt: str
    options: tuple[str, ...]
    default_answer: str | None
    answer: Mapping[str, object] | None
    raised_at: datetime
    timeout_at: datetime | None
    answered_at: datetime | None
    answered_by: str | None


@dataclass(frozen=True, slots=True)
class RunSpec:
    """What to run: the prompt/task plus the effort and isolation the
    adapter must translate into the engine's own flags."""

    run_id: UUID
    worktree_path: Path
    prompt: str
    effort: Effort
    isolation: IsolationLevel
    session_id: str | None = None  # set to resume a warm session


@dataclass(frozen=True, slots=True)
class RunHandle:
    run_id: UUID
    engine_id: EngineId
    run_dir: Path
    pid: int | None


@dataclass(frozen=True, slots=True)
class PreflightResult:
    installed: bool
    version: str | None
    auth_ok: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class StopSummary:
    run_id: UUID
    complete: bool
    summary: str
    remaining_work: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SnapshotRef:
    path: Path
    schema_version: int
    session_id: str | None


@dataclass(frozen=True, slots=True)
class EngineEvent:
    """One line of a runner's events.jsonl, before translation into a
    vibey LedgerEvent -- the adapter's own vocabulary, not ours."""

    kind: str
    at: datetime
    payload: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class ConformanceCheckResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass(frozen=True, slots=True)
class ConformanceReport:
    engine_id: EngineId
    checks: tuple[ConformanceCheckResult, ...]

    @property
    def ok(self) -> bool:
        return all(c.ok for c in self.checks)


@dataclass(frozen=True, slots=True)
class EngineHealthRecord:
    """One engine's health row. `engine_id` is read forward-compatibly
    (vibey#287): a row a newer vibey wrote for an engine this one does not know
    comes back under its stored id, is shown to the operator, and is never selected
    or written."""

    project_id: UUID
    engine_id: StoredEngineId
    installed: bool
    version: str | None
    conformance_ok: bool
    conformance_at: datetime | None
    auth_ok_at: datetime | None
    circuit: StoredCircuitState
    capacity_state: str | None
    resets_at: datetime | None
    probe_next_at: datetime | None
    probe_attempt: int
    consecutive_fail: int
    ewma_failure: float
    cost_usd_cycle: float
    selected_count: int


@dataclass(frozen=True, slots=True)
class FailureAttribution:
    failure_class: FailureClass
    detail: str


@dataclass(frozen=True, slots=True)
class RotationCursor:
    """SWRR cursor state for one engine in one project. A cursor a newer vibey
    keeps for an engine this one does not know is read under its stored id
    (vibey#287), left out of selection, and never rewritten."""

    project_id: UUID
    engine_id: StoredEngineId
    current: int
    order: int
