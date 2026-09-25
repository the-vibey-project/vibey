# Made with ❤️ by [Vibey](https://the-vibey-project.github.io/vibey/), Developed by [Adam Matthew Steinberger](https://vibewithadam.matthewsteinberger.com/) ([@adammatthewsteinberger](https://github.com/adammatthewsteinberger/)).
"""Data transfer objects crossing the application/infrastructure boundary.
Unlike domain/ types these may be mutated by callers and are not required to
be pure -- they are shapes, not behavior."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from uuid import UUID

from vibey.domain.budget import BudgetLedger
from vibey.domain.circuit import StoredCircuitState
from vibey.domain.effort import Effort
from vibey.domain.engine import (
    EngineDescriptor,
    EngineId,
    EngineTier,
    IsolationLevel,
    Loop,
    StoredEngineId,
)
from vibey.domain.interfaces.budget_caps_interface import (
    CapChangeInterface,
    CapHistoryEntryInterface,
)
from vibey.domain.job import FailureClass, StoredJobState
from vibey.domain.phase import Phase, StoredPhase
from vibey.domain.queue_reap import PolicyOutcome, ReapVerdict


@dataclass(frozen=True, slots=True)
class EnqueueRequest:
    project_id: UUID
    cycle: int
    phase: Phase
    kind: str
    idempotency_key: str
    payload: Mapping[str, object] = field(default_factory=dict)
    requirement: Mapping[str, object] = field(default_factory=dict)
    # No `priority`: a bump, through the grant, is the only way to reorder the queue
    # (ADR-0054). A priority on the request would be a second way with no grant.
    work_item_id: str | None = None
    max_attempts: int = 7
    run_after: datetime | None = None
    depends_on: tuple[UUID, ...] = ()
    depends_on_keys: tuple[str, ...] = ()
    """Dependencies named by idempotency key (same project) rather than job id:
    the only way to name a job whose id does not exist yet, i.e. an earlier
    request of the same `JobRepository.enqueue_batch`. Resolved inside the
    enqueue's own transaction; a key that names no job raises LookupError."""


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
    bump_seq: int | None = None
    """The job's place among bumped jobs (ADR-0054), or None in normal order. Last,
    with a default, so a record built before the column existed still builds."""
    bump_named: bool = False
    """True when bumped (or enqueued prioritised) by name and not since un-bumped; false
    for a job pulled into the lane as a named job's dependency (ADR-0054)."""


@dataclass(frozen=True, slots=True)
class QueueEntry:
    """One job as `vibey queue list` shows it: the row, and the dependencies it
    still waits on (not yet succeeded), which the claim will not jump."""

    job: JobRecord
    waiting_on: tuple[UUID, ...] = ()


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
class FeasibilityAssessment:
    """The conductor-facing projection of the family's feasibility verdict.

    ``status`` is one of ``feasible``, ``infeasible`` or ``unknown``.  A first
    repair exists only for a measured shortfall; an unknown coordinate is never
    turned into advice pretending the system measured it.
    """

    status: str
    blocked_at: str | None
    first_repair: str | None
    confidence: float
    required: int
    required_measured: int


@dataclass(frozen=True, slots=True)
class StartupPreflightReport:
    """Everything the worker startup sweep learned before it claims work."""

    ineligible_engines: tuple[EngineId, ...]
    feasibility: FeasibilityAssessment


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


@dataclass(frozen=True, slots=True)
class QueueReapReport:
    """What one reaper pass measured and did (ADR-0056).

    ``acted`` holds the reaps the pass performed and recorded, or -- in a dry run -- the
    reaps it would have performed. ``surfaced`` holds the stuck conditions that move
    nothing. ``unreadable`` names every source the pass could not read: nothing is
    concluded from those, and a pass with any of them is not ``ok`` (10.f, 12.e).
    """

    project_id: UUID
    dry_run: bool
    acted: tuple[ReapVerdict, ...] = ()
    surfaced: tuple[ReapVerdict, ...] = ()
    policy: PolicyOutcome | None = None
    notes: tuple[str, ...] = ()
    unreadable: tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        """Every source was read, and the broker policy -- where one was reconciled -- was
        read back as written."""
        return not self.unreadable and (self.policy is None or self.policy.verified)

    def joined(self, other: "QueueReapReport") -> "QueueReapReport":
        """This part of a pass followed by `other`: every finding of both, in order."""
        return QueueReapReport(
            project_id=self.project_id,
            dry_run=self.dry_run,
            acted=self.acted + other.acted,
            surfaced=self.surfaced + other.surfaced,
            policy=other.policy if other.policy is not None else self.policy,
            notes=self.notes + other.notes,
            unreadable=self.unreadable + other.unreadable,
        )


@dataclass(frozen=True, slots=True)
class ProjectBudget:
    """A project's caps, its current cycle's spend against them, and every change to
    the caps (`vibey budget`).

    `budget` is the brake's own reading, never a second opinion: the caps through
    `LedgerBudgetSource.caps_from_config`, the spend through `LedgerBudgetSource.current`
    -- what the worker checks before every BUILD session. `history` is read back from
    the ledger's `BudgetCapChanged` events, oldest first.
    """

    project_id: UUID
    name: str
    cycle: int
    budget: BudgetLedger
    history: tuple[CapHistoryEntryInterface, ...] = ()

    @property
    def exhausted(self) -> bool:
        """A cap is reached: the next BUILD session parks a `budget_exhausted` gate."""
        return self.budget.any_exhausted


@dataclass(frozen=True, slots=True)
class CapChangeOutcome:
    """What a budget store's write did: the project row as its transaction left it, and
    the changes it made -- none when the request left every cap as it was."""

    project: ProjectRecord
    changes: tuple[CapChangeInterface, ...] = ()


@dataclass(frozen=True, slots=True)
class BudgetChange:
    """What `vibey budget set` or `clear` did, and what holds now.

    `by` is the name the change was recorded under. `parked` holds the project's open
    `budget_exhausted` gates: a changed cap applies to a job parked on one only once the
    gate is answered, so the command says so rather than leaving a person waiting.
    """

    after: ProjectBudget
    by: str
    changes: tuple[CapChangeInterface, ...] = ()
    parked: tuple[HumanGateRecord, ...] = ()


@dataclass(frozen=True, slots=True)
class EngineContext:
    """One engine as vibey's own resolvers see it right now: its descriptor, whether it
    would run, the variable that switches it (a local engine has one), the model it runs
    when vibey chooses that model itself (qwenloop's `VIBEY_OLLAMA_MODEL`), and the argv
    template its `run` is built from (infrastructure/engines/argv.py)."""

    descriptor: EngineDescriptor
    enabled: bool
    run: tuple[str, ...]
    switch: str | None = None
    model: str | None = None
    # Whether the switch is on when nothing sets it: gptossloop's is (ADR-0060).
    on_by_default: bool = False


@dataclass(frozen=True, slots=True)
class EffortRun:
    """One engine at one requested effort: the argv it passes, the effort it really
    achieves, the model when anything in vibey names it, and why when nothing does."""

    effort: Effort
    argv: tuple[str, ...]
    achieved: Effort
    model: str | None
    chosen_by: str | None
    notes: str


@dataclass(frozen=True, slots=True)
class EffortChoice:
    """One engine as a candidate for one effort, in a loop's by-effort view."""

    engine_id: EngineId
    model: str | None
    achieved: Effort


@dataclass(frozen=True, slots=True)
class LoopEngine:
    """One engine as `vibey loops` reports it: its descriptor, how it stands right now,
    every effort it can be asked for, and the argv template of its `run`. A `repealed`
    engine (canon 8.b) stays listed and is never offered for selection."""

    descriptor: EngineDescriptor
    enabled: bool
    switch: str | None
    default_model: str | None
    efforts: tuple[EffortRun, ...]
    run: tuple[str, ...]
    repealed: bool = False
    notes: tuple[str, ...] = ()
    on_by_default: bool = False


@dataclass(frozen=True, slots=True)
class LoopView:
    """One of the two loops (8.c) and every engine its tier holds. `by_effort` offers only
    the engines not repealed."""

    loop: Loop
    tier: EngineTier
    default: bool
    declared_only: bool
    engines: tuple[LoopEngine, ...]
    by_effort: Mapping[Effort, tuple[EffortChoice, ...]]


@dataclass(frozen=True, slots=True)
class EffortLadder:
    """Where each phase starts and how BUILD climbs (domain/effort.py)."""

    phase_base: Mapping[Phase, Effort]
    build_attempts: tuple[Effort, ...]
    exhausted_after: int
    rotates_when_effort_rises: bool


@dataclass(frozen=True, slots=True)
class LoopsReport:
    """Everything `vibey loops` says: the efforts, the default loop and paid engine, the
    ladder, and both loops."""

    efforts: tuple[Effort, ...]
    default_loop: Loop
    paid_default_engine: EngineId
    ladder: EffortLadder
    loops: tuple[LoopView, ...]
