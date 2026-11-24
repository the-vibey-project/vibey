---
description: "The pure core of vibey, type by type: the phase machine, the effort ladder, engines and their tiers, rotation, the ledger and the no-loss gate, as they are in src/vibey/domain/ today."
---

# The domain model: vibey's pure core, type by type

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** `src/vibey/domain/` holds every rule vibey must get right
> (which phase is legal, which engine runs next, whether a handoff lost anything) as pure
> functions over frozen values, with no I/O and a 100% branch-coverage gate. This page walks
> the core modules member by member. Before you copy a signature from it, open the module: the
> code is the source, and this page says where it summarises.

> **How current this page is.** Sections 2–22 were checked member by member against
> `src/vibey/domain/` on `develop` at `d91a3791e` (vibey-engine 0.4.0) on 2026-11-24. The
> retired engine ids are gone from §4, `Effort.ULTRA` is in §3, the tier and loop model is in
> §4 and §7, `EventKind` lists all 56 members in §8, `errors.py` lists all 44 classes in §21,
> and the config defaults in §15 are the code's. The page covers the core modules in depth;
> the 50-odd modules added since 2026-09 are listed with one line each in §23, with the
> decision record that explains each. `domain/` has 82 modules plus the `acp/` and
> `interfaces/` packages. Earlier corrections kept: the import rule follows
> [ADR-0017](../architecture/decisions/0017-dogfood-the-family-first.md); the security
> primitives are plain classes; `check_clear_conditions` implements three of its four
> conditions; rotation's smoothness property, the probe backoff floors, the retry-ladder
> bound, the command deny-list and gate rule R7 are stated as the code behaves. Every layer,
> not only this one, carries a 100% branch coverage gate
> ([ADR-0023](../architecture/decisions/0023-four-layers-four-floors.md)). This page lives
> under `docs/plans/`, which the published site leaves out on purpose; it is kept current
> because the agent instruction files point here.

## The idea, in one conversation

> Daniel had a printout of `phase.py` on the bench, three lines underlined in pencil.
>
> **Daniel:** Professor, why does the domain have no database in it? Surely the phase of a
> project lives in the database.
>
> **Professor Feynman:** It does. But think of a referee's rule book. The book does not hold
> the ball. It says: if these things are true, the goal stands. You can read the book on a
> train, with no stadium anywhere near.
>
> **Daniel:** So the domain is the rule book, and the database is the stadium.
>
> **Professor Feynman:** Yes. `evaluate_transition` takes the state and the evidence and
> answers "allowed" or "denied, for these reasons". Nothing else. Because it touches nothing,
> we can throw thousands of made-up cases at it and check it never lies.
>
> **Daniel:** What happens when a newer vibey writes a phase the older one has never heard of?
>
> **Professor Feynman:** Good question, and the rule book has an answer: an unknown word is
> kept, shown, and never acted on. That is `UnrecognizedPhase`, and every stored enum has a
> twin like it. The picture stops working here: a referee can improvise, and our rule book
> may not. If it is not written in the book, the answer is no.

## See it on your machine

1. Ask the domain which engines exist and what each effort level becomes.

   ```bash
   vibey loops --json
   ```

   You should see a JSON document with a `loops` list of two entries, `sovereignloop` and
   `paidloop`, and inside them the five engine ids of `EngineId` with their effort
   projections from `TRIVIAL` to `ULTRA`.

2. From a checkout, ask the enums themselves.

   ```bash
   uv run python -c "from vibey.domain.effort import Effort; from vibey.domain.engine import EngineId; print([e.name for e in Effort]); print([e.value for e in EngineId])"
   ```

   You should see:

   ```text
   ['TRIVIAL', 'LOW', 'STANDARD', 'HIGH', 'MAX', 'ULTRA']
   ['claudeloop', 'codexloop', 'gptossloop', 'qwenloop', 'claudeloop-local']
   ```

3. Ask for a retired engine, and read the refusal.

   ```bash
   uv run python -c "from vibey.domain.engine import EngineId; EngineId('cursorloop')"
   ```

   The last line you should see is:

   ```text
   ValueError: 'cursorloop' is not a valid EngineId -- cursorloop was retired by ADR-0078 (#1376) and deleted with its runner; claudeloop and codexloop are the paid engines
   ```

## Daniel's teach-back

> **Daniel:** The domain is vibey's rule book. It holds the phase machine, the effort ladder,
> the engines and their tiers, rotation, the ledger's shape and the no-loss gate, all as pure
> functions over frozen values. It never touches a database, a clock or the network, and a test
> walks its imports to prove it. A value it does not recognise is kept and never acted on.
>
> **Professor Feynman:** Right. One small fix: "never a clock" means the domain never *reads*
> one. Times arrive as arguments, which is why the tests can choose them.

> Everything in `src/vibey/domain/`. **Stdlib, itself, and any family package
> that is itself dependency-free** (`vibey-gh`, `vibey-skills` and
> `vibey-runners-common` all declare `dependencies = []`); `vibey_bootstrap` is
> forbidden by name because it carries the Azure SDK and OpenTelemetry
> ([ADR-0017](../architecture/decisions/0017-dogfood-the-family-first.md)). No I/O, no async,
> no clock, no network — the import rule is enforced by `import-linter`, the rest
> by `tests/domain/test_domain_purity.py`, which walks the AST. Every value type
> here is a frozen, slotted dataclass and every function is pure, with one
> carve-out: the three security primitives in §19 are plain classes, and
> `PromptShield.frame_untrusted_input` mints a random nonce with
> `secrets.token_hex` unless the caller passes `nonce=`. This layer carries a 100%
> branch coverage floor because it is the layer where being wrong is silent.

---

## 1. Why the domain is this large

A thin domain would push the six-phase machine, the rotation algorithm, and the
no-loss gate into `application/`, where they would be tested against fakes rather
than against their own properties. The three things vibey must get right —
*which engine next*, *did the handoff lose anything*, *is this transition legal* —
are all pure functions of state. They belong here, where Hypothesis can attack
them without a database.

---

## 2. `phase.py`

```python
class Phase(StrEnum):
    INTAKE = "intake"; DESIGN = "design"; VISUAL_DESIGN = "visual_design"
    BUILD = "build"; REVIEW = "review"
    DEPLOY_DESIGN = "deploy_design"      # Phase ④
    DEPLOY_EXECUTE = "deploy_execute"    # Phase ⑤
    DEPLOY_REVIEW = "deploy_review"      # Phase ⑥
    DEPLOY = "deploy"                    # legacy single-phase bridge
    DONE = "done"; ABANDONED = "abandoned"


TERMINAL: frozenset[Phase] = frozenset({Phase.DONE, Phase.ABANDONED})
INTERACTIVE: frozenset[Phase] = frozenset({
    Phase.DESIGN, Phase.VISUAL_DESIGN, Phase.REVIEW,
    Phase.DEPLOY_DESIGN, Phase.DEPLOY_REVIEW,
})


class CompletionMode(StrEnum):
    LOCAL = "local"; DEPLOYED = "deployed"


class VisualDecision(StrEnum):
    OPTED_IN = "opted_in"; DECLINED = "declined"; ACCEPTED = "accepted"
    WAIVED = "waived"


class DeploymentDecision(StrEnum):
    OPTED_IN = "opted_in"; DECLINED = "declined"
```

`Phase.DEPLOY` is a legacy single-phase bridge kept alongside the ④–⑥
deployment stage set (`DEPLOY_DESIGN` / `DEPLOY_EXECUTE` / `DEPLOY_REVIEW`);
both `DONE` and `REVIEW` still have edges into it. The legal edges of the
machine live in a private `_EDGES: dict[Phase, frozenset[Phase]]` table,
checked independently of guard evaluation.

**Forward compatibility (vibey#287).** A phase is read from the database through
`PHASE_PARSER` into a `StoredPhase = Phase | UnrecognizedPhase`. An
`UnrecognizedPhase` is the text of a phase a newer vibey wrote during a rolling upgrade:
it is kept and shown, and never acted on. Every stored enum in `domain/` follows the same
pattern through `domain/stored_value.py` (`StoredValueParser`, `UnrecognizedValue`): engine
ids, event kinds, provenance, job states and circuit states each have an `Unrecognized…`
twin.

```python
@dataclass(frozen=True, slots=True)
class PhaseState:
    phase: StoredPhase              # Phase | UnrecognizedPhase
    cycle: int
    max_cycles: int
    entered_at: datetime

    def __post_init__(self) -> None:
        if self.cycle < 1:
            raise InvalidPhaseError("cycle must be >= 1")
        if self.max_cycles < 1:
            raise InvalidPhaseError("max_cycles must be >= 1")


@dataclass(frozen=True, slots=True)
class TransitionEvidence:
    """Everything a guard needs. Assembled by application/, evaluated here."""
    acceptance_criteria: int = 0
    open_blocking_questions: int = 0
    # DESIGN jobs of this cycle not yet succeeded, failed or cancelled: research,
    # synthesis and the spec must have run before the design can be accepted.
    unsettled_design_jobs: int = 0
    unmapped_criteria: tuple[str, ...] = ()
    work_items_total: int = 0
    work_items_settled: int = 0
    integration_green: bool = False
    criteria_with_passing_tests: int = 0
    build_savepoint_exists: bool = False
    open_findings: tuple[FindingRef, ...] = ()
    user_verdict: UserVerdict | None = None
    budget_exhausted: bool = False
    blocked_on_ambiguity: int = 0
    visual_decision: VisualDecision | None = None
    visual_inventory_complete: bool = False
    deployment_decision: DeploymentDecision | None = None
    completion_mode: CompletionMode | None = None
    deployment_spec_accepted: bool = False
    deployment_consent_recorded: bool = False
    deployment_verified: bool = False
    deployment_requires_user_input: bool = False
    deployment_demo_accepted: bool = False
    deployment_attempts: int = 0
    max_deployment_attempts: int = 5


@dataclass(frozen=True, slots=True)
class TransitionRequest:
    to: Phase
    reason: str
    evidence: TransitionEvidence


Allowed = Literal["allowed"]
ALLOWED: Allowed = "allowed"

@dataclass(frozen=True, slots=True)
class Denied:
    violations: tuple[str, ...]

TransitionOutcome = Allowed | Denied


def evaluate_transition(state: PhaseState, request: TransitionRequest) -> TransitionOutcome:
    """Checked in order: (0) a stored phase this vibey does not recognise
    (`UnrecognizedPhase`) is always denied, (1) the edge must exist in `_EDGES`,
    (2) `cycle` must not exceed `max_cycles` unless routing to `ABANDONED`,
    (3) any per-edge guard registered in `_GUARDS` must report no violations."""


def next_phase_after_design(*, visual_decision: VisualDecision, spec_is_buildable: bool) -> Phase:
    """Raises InvalidPhaseError on a non-buildable spec; otherwise VISUAL_DESIGN
    on opt-in, else BUILD directly."""


def next_phase_after_review(findings: Sequence[FindingRef], *, strict_loopback: bool) -> Phase:
    """The routing decision from ADR-0010. No findings -> DONE. strict_loopback
    or any NEEDS_CLARIFICATION finding -> DESIGN. Otherwise -> BUILD."""


def next_phase_after_deploy_review(
    findings: Sequence[FindingRef] = (),
    *,
    demo_accepted: bool = False,
    target_changed: bool = False,
    retry_unambiguous: bool = False,
    code_defect: bool = False,
) -> Phase:
    """The routing decision from ADR-0013 for Phase ⑥. Priority order:
    demo accepted (or nothing outstanding) -> DONE; a code defect -> DESIGN;
    a changed deployment target -> DEPLOY_DESIGN; an unambiguous retry ->
    DEPLOY_EXECUTE; otherwise -> DONE."""
```

Every guard function (`_guard_design_to_build`, `_guard_build_to_review`, …) is
registered in a private `_GUARDS: dict[tuple[Phase, Phase], Callable]` table
keyed by the edge it guards, so `evaluate_transition` never has to know which
guard applies — it just looks the edge up.

### Invariants

- `DONE` and `ABANDONED` have no outgoing edges except `DONE`'s bridge into
  `DEPLOY` / `DEPLOY_DESIGN`.
- No transition is legal when `cycle > max_cycles` except `→ ABANDONED`.
- Every non-terminal phase, `INTAKE` included, has an unguarded edge to
  `ABANDONED`, so `vibey abandon` can end a project wherever it stalled -- a
  dispatch that never reached `DESIGN` included. `DONE` has none: it is a
  different ending.
- `DESIGN → BUILD` and `DESIGN → VISUAL_DESIGN` share a common guard
  (`_guard_design_common`): at least one acceptance criterion, no open blocking
  question, no DESIGN job of this cycle still unsettled, no unmapped criterion, and
  a user verdict of `ACCEPT`.
- No transition out of an `UnrecognizedPhase` is legal.
- `DESIGN → BUILD` additionally requires an explicit visual-design **decline**;
  opting in must route through `VISUAL_DESIGN` first. `DESIGN → VISUAL_DESIGN`
  additionally requires an explicit opt-in.
- `VISUAL_DESIGN → BUILD` requires the visual plan accepted-or-waived *and* a
  complete screen/state inventory.
- `BUILD → REVIEW` requires every work item settled, the integration branch
  green, every acceptance criterion covered by a passing test, and a build
  savepoint at the integration head.
- `BUILD → DESIGN` requires at least one work item blocked on ambiguity.
- `REVIEW → DONE` requires no open findings and a user verdict of `ACCEPT`.
- `REVIEW → DEPLOY_DESIGN`, `DONE → DEPLOY` and `DONE → DEPLOY_DESIGN` require
  an explicit deployment opt-in.
- `DEPLOY_DESIGN → DEPLOY_EXECUTE` requires both an accepted deployment spec
  and recorded consent.
- `DEPLOY_EXECUTE → DEPLOY_REVIEW` requires the deployment to be verified or
  classified as needing user input.
- `DEPLOY_REVIEW → DONE` requires the deployment demo to be accepted.
- `DEPLOY_DESIGN` and `DEPLOY_EXECUTE` each have an unguarded self-edge
  (revise or retry within the phase); every other unlisted edge is unguarded
  and decided by the handler that requests it.
- `evaluate_transition` is total: every `(state, request)` pair returns
  without raising.

---

## 3. `effort.py`

```python
class Effort(IntEnum):
    TRIVIAL = 0; LOW = 1; STANDARD = 2; HIGH = 3; MAX = 4
    # Effort without a ceiling (ADR-0063): chosen, never escalated into. No ladder,
    # triage rule or phase base reaches it; an engine runs it with no turn limit.
    ULTRA = 5


PHASE_BASE_EFFORT: Mapping[Phase, Effort] = {
    Phase.DESIGN: Effort.HIGH,     # the user's requirement
    Phase.VISUAL_DESIGN: Effort.HIGH,
    Phase.BUILD:  Effort.LOW,      # the user's requirement
    Phase.REVIEW: Effort.HIGH,     # the user's requirement
    Phase.DEPLOY_DESIGN: Effort.HIGH,
    Phase.DEPLOY_EXECUTE: Effort.LOW,
    Phase.DEPLOY_REVIEW: Effort.HIGH,
    Phase.DEPLOY: Effort.LOW,
}

# attempt -> effort, for Phase 2's per-item escalation ladder (1-based attempts)
BUILD_LADDER: tuple[Effort, ...] = (
    Effort.LOW, Effort.LOW,
    Effort.STANDARD, Effort.STANDARD,
    Effort.HIGH, Effort.HIGH,
)
BUILD_LADDER_EXHAUSTED = len(BUILD_LADDER)   # attempt 7 → human gate


def effort_for_attempt(base: Effort, attempt: int) -> Effort:
    """Phase 2 escalation. Never lowers below base; saturates at HIGH.
    Raises EscalationExhausted past attempt 6, and ValueError for
    attempt <= 0 (attempts are 1-based)."""


def forces_rotation(previous: Effort, current: Effort) -> bool:
    return current > previous


def triage_required_effort(findings: Sequence[FindingRef]) -> Effort:
    """Required execution effort for a set of triaged review findings: any
    CRITICAL -> MAX, else any HIGH -> HIGH, else any MEDIUM -> STANDARD,
    else LOW."""
```

---

## 4. `engine.py`

```python
EXIT_CODE_WIND_DOWN = 75
"""The *loop runners' shared "graceful wind-down" exit code: the engine ran
out of window capacity mid-item and stopped cleanly after writing its state,
so the item hands off to another engine instead of failing
(handoff-protocol.md §3). A domain constant because the meaning belongs to
the protocol, not to any one subprocess adapter."""

EXIT_CODE_BACKEND_MISCONFIGURED = 78
"""EX_CONFIG: the runner stopped because its own backend is misconfigured (an
unreachable local server, a model not pulled, a context window too small). No retry
fixes a configuration, so the job parks on an `engine_misconfigured` gate."""


RETIRED_ENGINES: Mapping[str, str]   # {"cursorloop": " -- ... retired by ADR-0078 ...",
                                     #  "agyloop":    " -- ... retired by ADR-0078 ..."}
"""Engine ids the family once shipped and has since deleted. A configuration, flag or
allow-list that names one is refused out loud, naming the decision. A stored row that
names one stays valid history and reads as an `UnrecognizedEngineId`."""


class EngineId(StrEnum):
    CLAUDELOOP = "claudeloop"; CODEXLOOP = "codexloop"
    GPTOSSLOOP = "gptossloop"   # the sovereign default: the local runner on GPT-OSS
    QWENLOOP = "qwenloop"       # the same runner on a Qwen model, opt-in (ADR-0064)
    CLAUDELOOP_LOCAL = "claudeloop-local"

    @classmethod
    def _missing_(cls, value): ...
    # EngineId("cursorloop") / EngineId("agyloop") raise ValueError with the
    # RETIRED_ENGINES clause appended; any other unknown value gets the enum's own
    # ValueError. There is no CURSORLOOP or AGYLOOP member: code that names one
    # fails with AttributeError (ADR-0078).


class EngineTier(StrEnum):
    LOCAL = "local"   # runs on hardware the operator owns; costs nothing per token
    PAID = "paid"     # runs on a vendor's account


TIER_PREFERENCE: tuple[EngineTier, ...] = (EngineTier.LOCAL, EngineTier.PAID)
# 8.a: the sovereign path is the preference, not the fallback (ADR-0038).


class Loop(StrEnum):            # the family's two loops, exactly two (8.c)
    SOVEREIGN = "sovereignloop"
    PAID = "paidloop"


LOOP_BY_TIER: Mapping[EngineTier, Loop]   # LOCAL -> sovereignloop, PAID -> paidloop
DEFAULT_LOOP = Loop.SOVEREIGN
# States the canon. The selector does not read a paid declaration yet: it prefers
# the local tier and falls back to paid whenever no local engine is eligible.
PAID_DEFAULT_ENGINE = EngineId.CLAUDELOOP
# The canon's paid default (8.b). The selector does not act on it yet: within the
# paid tier it rotates by weight.
REPEALED_FROM_LOOPS: frozenset[EngineId] = frozenset()   # empty since OpenCode was deleted
RENAMED_ENGINES: Mapping[EngineId, str]
# {QWENLOOP: "since ADR-0064 qwenloop runs a Qwen model (qwen3:14b unless
#  QWENLOOP_MODEL names another); the gpt-oss engine it used to be is gptossloop"}


class PluginSystem(StrEnum):    # how a loop takes extensions beyond its plan
    SKILLS_CONTEXT = "skills-context"   # vibey-skills packets written into the plan
    CLAUDE_PLUGINS = "claude-plugins"   # Claude Code's own plugin system
    VIBEY_BUNDLE = "vibey-bundle"       # the locked capability snapshot, as text + MCP


@dataclass(frozen=True, slots=True)
class EngineAffordances:        # what a person can hand a loop besides its plan
    images: bool | None = None; files: bool | None = None
    paste_text: bool | None = None; paste_images: bool | None = None
    plugins: PluginSystem | None = None; mcp: bool | None = None
    skills: bool | None = None; web_search: bool | None = None
    evidence: Mapping[str, str] = {}    # field -> where in the runner's code it is shown
    def full_access_gaps(self) -> tuple[str, ...]: ...   # unknown is a gap, not a grant


@dataclass(frozen=True, slots=True)
class EngineControls:           # the runner's own verbs for a run in flight; None = unverified
    stop: tuple[str, ...] | None = None
    wind_down: tuple[str, ...] | None = None
    prompt: tuple[str, ...] | None = None


class EventEnvelope(StrEnum):   # how a runner shapes one line of events.jsonl
    TYPE = "type"; EVENT_TYPE_PAYLOAD = "event_type+payload"; EVENT_TYPE = "event_type"


@dataclass(frozen=True, slots=True)
class EventLog:
    path: str | None = None           # template over {cwd}, {state_dir}, {run_id}
    envelope: EventEnvelope | None = None


@dataclass(frozen=True, slots=True)
class UnrecognizedEngineId(UnrecognizedValue): ...   # a stored id this vibey does not know
type StoredEngineId = EngineId | UnrecognizedEngineId
ENGINE_ID_PARSER: StoredValueParserInterface[EngineId, UnrecognizedEngineId]


class Capability(StrEnum):
    SAVEPOINTS = "savepoints"; UNWIND = "unwind"
    STRUCTURED_VERDICT = "structured_verdict"
    MID_RUN_PROMPT = "mid_run_prompt"; MID_RUN_MODEL = "mid_run_model"
    MID_RUN_EFFORT = "mid_run_effort"; ATTACHMENTS = "attachments"
    SLASH_COMMANDS = "slash_commands"; WEB_SEARCH = "web_search"
    SNAPSHOT = "snapshot"; SANDBOX = "sandbox"


class IsolationLevel(StrEnum):
    WORKTREE = "worktree"; CONTAINER = "container"; VM = "vm"


@dataclass(frozen=True, slots=True)
class EngineInvocation:
    argv: tuple[str, ...]
    achieved: Effort
    notes: str = ""


@dataclass(frozen=True, slots=True)
class EngineDescriptor:
    engine_id: EngineId
    binary: str
    min_version: str
    state_dir: str
    done_marker: str
    auth_env: tuple[str, ...]
    capabilities: frozenset[Capability]
    effort_projection: Mapping[Effort, EngineInvocation]
    session_verb: str
    isolation_flags: Mapping[IsolationLevel, tuple[str, ...]]
    cost_per_mtok_in: float
    cost_per_mtok_out: float
    context_window: int
    base_weight: int = 1
    supports_cwd_flag: bool = True   # False for a binary that rejects --cwd
    plan_flag: str | None = None     # None = bare positional; else the flag name
                                     # (one engine ADR-0078 retired took --plan; none does today)
    resume_run_id_flag: str | None = None   # keeps vibey's run id when resuming a session
    tier: EngineTier = EngineTier.PAID      # LOCAL for engines on the operator's hardware
    launch_flags: tuple[str, ...] = ()      # passed to every new `run`; checked by conformance
    capabilities_flag: str | None = None    # the `run` flag that takes the locked capability
                                            # snapshot (ADR-0103); None = takes no snapshot
    doctor_args: tuple[str, ...] = ()       # extra args for `<binary> doctor` in preflight
    env_passthrough: tuple[str, ...] = ()   # env vars the engine's process may read; a
                                            # trailing * names a prefix (CLAUDELOOP_*)
    affordances: EngineAffordances = EngineAffordances()   # reported by `vibey loops`
    controls: EngineControls = EngineControls()
    events: EventLog = EventLog()

    def invoke(self, effort: Effort) -> EngineInvocation:
        """Falls back to the highest projection at or below `effort` — the
        descriptor's own saturation point — instead of raising on a missing
        exact tier. Still raises KeyError when the descriptor has no
        projection at or below the requested effort."""

    def saturates_at(self, effort: Effort) -> bool:
        return self.invoke(effort).achieved < effort


@dataclass(frozen=True, slots=True)
class JobRequirement:
    effort: Effort
    capabilities: frozenset[Capability] = frozenset()
    excluded: frozenset[EngineId] = frozenset()   # the "must differ" constraint
```

`supports_cwd_flag` and `plan_flag` exist because each engine's CLI was
verified against its actual `--help` output, not assumed: passing a flag a
binary doesn't have, or a positional path to a binary that wants a flag,
fails at argument parsing before the session ever starts.

The five descriptors themselves (`CLAUDELOOP`, `CODEXLOOP`, `GPTOSSLOOP`, `QWENLOOP`,
`CLAUDELOOP_LOCAL`) live outside the domain, in
`src/vibey/infrastructure/engines/descriptors.py`: `DEFAULT_DESCRIPTORS` holds the two paid
ones, `LOCAL_DESCRIPTORS` the three local ones, and `ALL_DESCRIPTORS` all five.
[rotation-and-engines.md](rotation-and-engines.md) §1 tabulates them.

---

## 5. `capacity.py`

Inherited from the `*loop` family, unchanged in spirit and in the one rule that
matters.

```python
@dataclass(frozen=True, slots=True)
class Available: ...

@dataclass(frozen=True, slots=True)
class WindowExhausted:
    resets_at: datetime | None = None
    rate_limit_type: str | None = None

@dataclass(frozen=True, slots=True)
class CreditsExhausted:
    can_purchase: bool = True
    # There is deliberately NO resets_at field here, and there never will be.
    # A credits balance has no clock. Only a human top-up changes it.

@dataclass(frozen=True, slots=True)
class AuthenticationFailed:
    detail: str = ""

CapacityState = Available | WindowExhausted | CreditsExhausted | AuthenticationFailed
```

---

## 6. `circuit.py`

```python
class CircuitState(StrEnum):
    CLOSED = "closed"; HALF_OPEN = "half_open"; OPEN = "open"


@dataclass(frozen=True, slots=True)
class DeadlineProbe:
    at: datetime

@dataclass(frozen=True, slots=True)
class BackoffProbe:
    next_at: datetime
    attempt: int

ProbeSchedule = DeadlineProbe | BackoffProbe


@dataclass(frozen=True, slots=True)
class Circuit:
    state: CircuitState
    capacity: CapacityState
    probe: ProbeSchedule | None
    consecutive_failures: int = 0
    ewma_failure: float = 0.0


def schedule_probe(capacity: CapacityState, *, now: datetime, attempt: int) -> ProbeSchedule | None:
    """The type system carries the rule: CreditsExhausted can only ever produce
    a BackoffProbe, never a DeadlineProbe — because there is no deadline.
    Available -> None (no probe needed). WindowExhausted with a known
    resets_at -> a DeadlineProbe jittered off that time (deterministically,
    seeded from the reset time and attempt so retries stay reproducible).
    WindowExhausted with no reset time -> a backoff schedule (base 2s,
    doubling, capped at 5 minutes). CreditsExhausted -> a backoff schedule
    floored at 5 minutes and capped at 30, so a dead balance is never
    hammered. The exponent is capped at 2**32 to keep timedelta in range.
    AuthenticationFailed -> None; waiting cannot fix credentials."""


ENGINE_FAILURE_THRESHOLD = 3                       # consecutive ENGINE-class failures open it
ENGINE_FAILURE_PROBE_BASE = timedelta(minutes=5)   # first probe after the threshold
ENGINE_FAILURE_PROBE_CAP = timedelta(minutes=30)   # longest wait between probes


@dataclass(frozen=True, slots=True)
class EngineFailurePolicy:
    """When ENGINE-class failures open a circuit and when it is probed again.
    Opening without a probe time would be a one-way door: an open engine cannot be
    selected to prove it has recovered."""
    threshold: int = ENGINE_FAILURE_THRESHOLD
    probe_base: timedelta = ENGINE_FAILURE_PROBE_BASE
    probe_cap: timedelta = ENGINE_FAILURE_PROBE_CAP
    def trips(self, consecutive_failures: int) -> bool: ...
    def probe_at(self, *, now: datetime, consecutive_failures: int) -> datetime: ...


@dataclass(frozen=True, slots=True)
class UnrecognizedCircuitState(UnrecognizedValue): ...
# A stored circuit state a newer vibey wrote. An older selector cannot tell whether it
# admits a run, so it does not select the engine; it never crashes on the row.
type StoredCircuitState = CircuitState | UnrecognizedCircuitState
```

### The one property test that matters most

```python
@given(capacity=capacity_states(), now=datetimes(), attempt=st.integers(0, 100))
def test_credits_never_produce_a_deadline(capacity, now, attempt):
    probe = schedule_probe(capacity, now=now, attempt=attempt)
    if isinstance(capacity, CreditsExhausted):
        assert not isinstance(probe, DeadlineProbe)
```

---

## 7. `rotation.py`

```python
@dataclass(frozen=True, slots=True)
class EngineRuntime:
    """The live state application/ assembles for one engine before a
    selection round: the static descriptor plus whatever changes call to
    call (circuit, install/auth checks)."""
    engine_id: EngineId
    descriptor: EngineDescriptor
    circuit: Circuit
    installed: bool
    conformance_ok: bool
    auth_valid: bool


@dataclass(frozen=True, slots=True)
class Candidate:
    engine_id: EngineId
    base_weight: int
    current: int
    order: int
    health_factor: float
    fidelity_factor: float
    cost_factor: float
    affinity_factor: float
    tier: EngineTier = EngineTier.PAID    # which side of TIER_PREFERENCE (ADR-0038)

    @property
    def effective_weight(self) -> int:
        """0 if the combined weight is non-positive; otherwise rounded but
        floored at 1. A positive weight must never round down to zero — a
        half-open probe on a base_weight-1 engine is 1 * 0.25 = 0.25, and a
        plain round() would make that 0, so the probe could never fire and
        the engine would stay open forever."""
        raw = (self.base_weight * self.health_factor * self.fidelity_factor
               * self.cost_factor * self.affinity_factor)
        if raw <= 0:
            return 0
        return max(1, round(raw))


@dataclass(frozen=True, slots=True)
class Selection:
    engine_id: EngineId
    candidates: tuple[Candidate, ...]     # updated SWRR state


def eligible(
    runtimes: Sequence[EngineRuntime], *, requirement: JobRequirement,
    allow_list: frozenset[EngineId] | None = None,
) -> tuple[EngineRuntime, ...]:
    """Filters out engines that aren't installed, don't pass conformance,
    have invalid auth, have an OPEN circuit, are in `requirement.excluded`,
    aren't on an explicit `allow_list`, or lack a required capability."""

def rejections(
    runtimes: Sequence[EngineRuntime], *, requirement: JobRequirement,
    allow_list: frozenset[EngineId] | None = None,
) -> tuple[str, ...]:
    """Why each engine `eligible` turned down, one phrase per engine ("claudeloop: its
    circuit is open"), by exactly `eligible`'s rules -- the message a deferred job
    carries, so each cause gets its own fix."""

def preferred_tier(candidates: Sequence[Candidate]) -> tuple[Candidate, ...]:
    """Local-first (ADR-0038, sub-doctrine 8.a): tiers are tried in TIER_PREFERENCE
    order, and SWRR runs within the first tier holding a candidate with a positive
    effective weight. A paid engine is chosen only when no local one can win a round.
    When no tier qualifies, every candidate is returned and `select` raises."""

def select(candidates: Sequence[Candidate]) -> Selection: ...      # smooth WRR
def health_factor(circuit: Circuit) -> float: ...
def fidelity_factor(descriptor: EngineDescriptor, requested: Effort) -> float: ...
def cost_factor(descriptor, *, median_cost: float, enabled: bool) -> float: ...
def affinity_factor(*, holds_warm_session: bool, rotation_forced: bool) -> float: ...
```

- `health_factor`: `1.0` closed (decaying with `ewma_failure`), `0.25`
  half-open, `0.0` open. Half-open is a *quarter*, not a half (ADR-0005): a
  circuit under test should win a round only when the alternatives are
  genuinely worse, not on even footing with a healthy engine.
- `fidelity_factor`: `1.0` at the requested tier, `0.7` one tier short,
  `0.5` two-or-more tiers short — an engine that saturates far below what was
  asked for is worse than one that just misses.
- `affinity_factor`: `2.0` for a warm session unless rotation is forced
  (then `1.0`) — this is what keeps an ordinary retry from becoming a
  handoff on every retry.

### Properties

| Property | Statement |
|---|---|
| **No starvation** | Over `sum(effective_weight)` consecutive selections, every candidate with `effective_weight > 0` is selected at least once |
| **Weight fidelity** | Selection counts converge to weight ratios within ±1 over any full period |
| **Smoothness** | Selections are spread across the period rather than bunched: a candidate never monopolizes every slot while another with `effective_weight > 0` waits. SWRR interleaves proportionally but does not forbid repeats — with weights 5:1 the heavy candidate wins three rounds in a row before the light one is chosen |
| **Determinism** | Identical candidate state produces an identical selection |
| **Totality** | `select` raises `NoEligibleEngine` iff every `effective_weight` is 0, or if the input is empty |
| **Unique identity** | `select` raises `ValueError` if two candidates share an `engine_id` |
| **Exclusion honored** | An engine in `requirement.excluded` is never returned |

---

## 8. `ledger.py`

```python
class EventKind(StrEnum):
    SESSION_SEEDED = "SessionSeeded"; TURN_REQUESTED = "TurnRequested"
    TURN_COMPLETED = "TurnCompleted"; TOOL_INVOKED = "ToolInvoked"
    TRANSCRIPT_RECORDED = "TranscriptRecorded"  # turn text; never a turn boundary
    FILE_EDITED = "FileEdited"; VERDICT_RENDERED = "VerdictRendered"
    CAPACITY_REJECTED = "CapacityRejected"
    QUESTION_ASKED = "QuestionAsked"
    STAGE_SETTLED = "StageSettled"
    ANSWER_GIVEN = "AnswerGiven"
    DECISION_RECORDED = "DecisionRecorded"; ASSUMPTION_STATED = "AssumptionStated"
    FINDING_RAISED = "FindingRaised"; FINDING_RESOLVED = "FindingResolved"
    ARTIFACT_PRODUCED = "ArtifactProduced"; SAVEPOINT_CREATED = "SavePointCreated"
    HANDOFF_INITIATED = "HandoffInitiated"; HANDOFF_ACCEPTED = "HandoffAccepted"
    PHASE_TRANSITIONED = "PhaseTransitioned"; BUDGET_SPENT = "BudgetSpent"
    VISUAL_DESIGN_OPTED_IN = "VisualDesignOptedIn"
    VISUAL_DESIGN_DECLINED = "VisualDesignDeclined"
    VISUAL_DESIGN_ACCEPTED = "VisualDesignAccepted"
    VISUAL_DESIGN_WAIVED = "VisualDesignWaived"
    DEPLOYMENT_OPTED_IN = "DeploymentOptedIn"; DEPLOYMENT_DECLINED = "DeploymentDeclined"
    # The last step of a delivered project: its work was pushed (a pull request opened,
    # or a new repository created), or the operator chose not to. Never a deployment.
    PUBLISH_COMPLETED = "PublishCompleted"; PUBLISH_SKIPPED = "PublishSkipped"
    DELIVERY_ESTIMATE_RECORDED = "DeliveryEstimateRecorded"
    # Queue priority (ADR-0054), in the same transaction as the job rows they describe
    JOB_PRIORITY_BUMPED = "JobPriorityBumped"
    JOB_PRIORITY_UNBUMPED = "JobPriorityUnbumped"
    JOB_PRIORITY_REFUSED = "JobPriorityRefused"
    # Queue reaping (ADR-0056): object, condition, measured value, threshold, action
    QUEUE_REAPED = "QueueReaped"
    # `vibey budget set`/`clear`: field, old, new, by, account; with the config write
    BUDGET_CAP_CHANGED = "BudgetCapChanged"
    # ULTRA (ADR-0063): `vibey ultra start` / `stop` (the latest decides whether the next
    # BUILD pass runs), one event per finished improvement pass, and the no-cap
    # declaration changing (`vibey budget no-cap` / `cap`; trusted only)
    ULTRA_STARTED = "UltraStarted"; ULTRA_STOPPED = "UltraStopped"
    ULTRA_PASS_COMPLETED = "UltraPassCompleted"
    ULTRA_NO_CAP_CHANGED = "UltraNoCapChanged"
    # A gate answered once: gate, kind, answer, request id, by, account; with the answer
    GATE_ANSWERED = "GateAnswered"
    # A gate closed by `vibey abandon`, never answered: gate, kind, job, request id,
    # reason, by, account; with the move into abandoned and the gate's own row
    GATE_WITHDRAWN = "GateWithdrawn"
    # A device paired with the hub, or its pairing revoked (ADR-0068, ADR-0071): device
    # id, name and granted scopes, never its key; written to every project's ledger
    HUB_DEVICE_PAIRED = "HubDevicePaired"; HUB_DEVICE_REVOKED = "HubDeviceRevoked"
    ENGINE_FAILED_OVER = "EngineFailedOver"    # ADR-0070
    ENGINE_PROBED = "EngineProbed"
    ENGINE_HANDED_BACK = "EngineHandedBack"
    # Hybrid dispatch (ADR-0079): a job held for a local slot (once per job and attempt),
    # a paid overflow (slots, wait, cap and what was left -- the cap counts these), and
    # `auto`'s measurement of local-slot contention with the mode it chose
    ENGINE_SLOT_WAIT_STARTED = "EngineSlotWaitStarted"
    ENGINE_OVERFLOW_SELECTED = "EngineOverflowSelected"
    ENGINE_DISPATCH_MEASURED = "EngineDispatchMeasured"
    # A gate notice: gate, kind, job, notice number (0 raised, 1.. reminders), and the
    # channels that took it -- or the reason nobody could be told. Once per gate and number.
    GATE_NOTIFIED = "GateNotified"
    GATE_NOTICE_UNDELIVERABLE = "GateNoticeUndeliverable"
    # A handler's failed run: attempt, class, signature (normalized detail, hashed), detail
    JOB_FAILED = "JobFailed"
    # A DESIGN research topic not researched (`[design.research] on_unavailable =
    # "record_gap"`): topic, reason, cycle -- never a source. The spec states each one.
    RESEARCH_GAP_RECORDED = "ResearchGapRecorded"
    # The hub's web search or fetch for a principal (ADR-0102): who, the outcome, the backend,
    # and for a fetch the hosts it reached -- never the query, never a URL. Trusted only.
    WEB_SEARCHED = "WebSearched"
    WEB_FETCHED = "WebFetched"
    # The snapshot a BUILD run was given, recorded by vibey before the engine starts (SP-LOOPS
    # Phase 4): run id, digest and counts only. Trusted only; withheld from publication.
    LOOP_CAPABILITIES_SNAPSHOTTED = "LoopCapabilitiesSnapshotted"
# 56 members in all (counted 2026-11-24).


class UnrecognizedEventKind: ...   # the text of a kind a newer vibey wrote (vibey#275)
type LedgerEventKind = EventKind | UnrecognizedEventKind
EVENT_KIND_PARSER: EventKindParserInterface   # a member, else an UnrecognizedEventKind


CLOSABLE: frozenset[EventKind] = frozenset({
    EventKind.QUESTION_ASKED, EventKind.DECISION_RECORDED,
    EventKind.ASSUMPTION_STATED, EventKind.FINDING_RAISED,
})

CLOSES: Mapping[EventKind, EventKind] = {
    EventKind.ANSWER_GIVEN:    EventKind.QUESTION_ASKED,
    EventKind.FINDING_RESOLVED: EventKind.FINDING_RAISED,
}


class Provenance(StrEnum):
    TRUSTED = "trusted"      # vibey itself, the developer
    AGENT = "agent"          # an engine's own output
    UNTRUSTED = "untrusted"  # web, dependencies, issue text — data, never instruction


@dataclass(frozen=True, slots=True)
class UnrecognizedProvenance(UnrecognizedValue): ...
type StoredProvenance = Provenance | UnrecognizedProvenance
PROVENANCE_PARSER: StoredValueParserInterface[Provenance, UnrecognizedProvenance]


@dataclass(frozen=True, slots=True)
class LedgerEvent:
    """One event as a reader sees it. Every closed vocabulary is read
    forward-compatibly, so an event a newer vibey wrote is kept whole; a writer's
    draft (`LedgerEventDraft`) takes only members."""
    event_id: UUID; project_id: UUID; cycle: int; phase: StoredPhase
    seq: int; kind: LedgerEventKind; engine_id: StoredEngineId | None
    job_id: UUID | None; causation_id: UUID | None; correlation_id: UUID
    provenance: StoredProvenance; produced_at: datetime
    payload: Mapping[str, object]; digest: str

    @property
    def interpretable(self) -> bool:
        """A known phase and a known trust class. Semantic projections (and the
        no-loss rules R1-R5 and R7) read only interpretable events; accounting and
        lossless export keep every event."""


def canonical_bytes(payload: Mapping[str, object]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()

def digest_event(payload: Mapping[str, object]) -> str:
    return hashlib.sha256(canonical_bytes(payload)).hexdigest()

def digest_range(events: Sequence[LedgerEvent]) -> str:
    """Order-sensitive Merkle-ish fold. Rule R6 depends on this."""
    h = hashlib.sha256()
    for e in sorted(events, key=lambda x: x.seq):
        h.update(str(e.seq).encode()); h.update(b"\x00"); h.update(e.digest.encode())
    return h.hexdigest()


def open_items(events: Sequence[LedgerEvent], kind: EventKind) -> tuple[str, ...]:
    """Ids opened by `kind` and not yet closed or superseded, in the order
    they were opened. Raises ValueError if `kind` is not in CLOSABLE. A
    DecisionRecorded event whose payload carries a `supersedes` id closes
    that prior decision the same way an explicit closing event would."""
```

---

## 9. `handoff.py` and `noloss.py`

Specified in full in [handoff-protocol.md](handoff-protocol.md). `handoff.py`
defines the envelope and brief types; `noloss.py` is the pure gate that
verifies a brief against the ledger before a handoff is allowed to complete.

```python
# handoff.py
class HandoffReason(StrEnum):
    ROTATION = "rotation"; CAPACITY = "capacity"; ESCALATION = "escalation"
    FAILURE = "failure"; PHASE_TRANSITION = "phase_transition"; OPERATOR = "operator"


class GateMode(StrEnum):
    STRICT = "strict"; FULL_TRANSCRIPT = "full_transcript"
    HUMAN = "human"; FORCED = "forced"


class GateRule(StrEnum):
    R1_REMAINING = "R1"; R2_QUESTIONS = "R2"; R3_DECISIONS = "R3"
    R4_ASSUMPTIONS = "R4"; R5_FINDINGS = "R5"; R6_RANGE = "R6"
    R7_ARTIFACTS = "R7"; R8_BUDGET = "R8"; R9_CONSTRAINTS = "R9"
    R10_CONTAINMENT = "R10"


@dataclass(frozen=True, slots=True)
class Violation:
    rule: GateRule
    item_id: str | None
    detail: str


@dataclass(frozen=True, slots=True)
class GateResult:
    ok: bool
    mode: GateMode
    attempts: int
    violations: tuple[Violation, ...]
    rules_run: tuple[GateRule, ...]


# The refs a HandoffBrief is built from, and closes against the ledger:
@dataclass(frozen=True, slots=True)
class DecisionRef:
    decision_id: str
    restatement: str

@dataclass(frozen=True, slots=True)
class AssumptionRef:
    assumption_id: str
    restatement: str

@dataclass(frozen=True, slots=True)
class QuestionRef:
    question_id: str
    text: str
    blocking: bool

@dataclass(frozen=True, slots=True)
class RemainingItem:
    text: str
    item_id: str | None = None

@dataclass(frozen=True, slots=True)
class ArtifactRef:
    artifact_id: str
    path: str


@dataclass(frozen=True, slots=True)
class HandoffBrief:
    objective: str
    constraints: tuple[str, ...]
    decisions: tuple[DecisionRef, ...]
    assumptions: tuple[AssumptionRef, ...]
    done: tuple[str, ...]
    remaining: tuple[RemainingItem, ...]
    open_questions: tuple[QuestionRef, ...]
    open_findings: tuple[FindingRef, ...]
    artifacts: tuple[ArtifactRef, ...]
    invariants: tuple[str, ...]
    style_rules: tuple[str, ...]
    next_action: str


@dataclass(frozen=True, slots=True)
class LedgerRef:
    """The ledger range a brief was verified against — what R6 checks."""
    uri: str
    from_seq: int
    to_seq: int
    event_count: int
    digest: str


@dataclass(frozen=True, slots=True)
class RepoState:
    branch: str
    head_sha: str
    worktree_path: str
    dirty_paths: tuple[str, ...]
    last_savepoint: str | None
    integration_branch: str | None


@dataclass(frozen=True, slots=True)
class HandoffEnvelope:
    """The full record persisted (to disk, in the receiving worktree) every
    time work moves from one engine to another."""
    schema_version: int
    handoff_id: UUID
    project_id: UUID
    cycle: int
    phase: Phase
    from_engine: EngineId | None
    to_engine: EngineId
    reason: HandoffReason
    produced_at: datetime
    brief: HandoffBrief
    repo_state: RepoState
    ledger_ref: LedgerRef
    budget: BudgetSnapshot          # = budget.py's BudgetLedger, re-exported
    gate: GateResult
```

```python
# noloss.py
def verify(
    *, ledger, brief, ref, budget, spec_constraints=(), mode=GateMode.STRICT, attempts=1,
) -> GateResult:
    """Pure. No model call. This function is the reason rotation is safe."""
```

`verify` runs ten independent checks, each producing zero or more
`Violation`s, keyed by the `GateRule` it enforces. R1–R5 and R7 read only the
`interpretable` events of the range (§8); R6 and R8 read every event, so an event a newer
vibey wrote still counts toward the digest and the spend.

| Rule | Checks |
|---|---|
| R1 | Every item in the latest `VerdictRendered` event's `remaining_work` appears in `brief.remaining` |
| R2 | Every open `QuestionAsked` id (per `open_items`) appears in `brief.open_questions` |
| R3 | Every open `DecisionRecorded` id appears in `brief.decisions` |
| R4 | Every open `AssumptionStated` id appears in `brief.assumptions` |
| R5 | Every open `FindingRaised` id appears in `brief.open_findings` |
| R6 | `ref.digest`, `ref.event_count`, and `ref.to_seq` all match the ledger range actually supplied |
| R7 | Every `ArtifactProduced` event whose payload sets `referenced_by_open_item` appears (by `artifact_id`) in `brief.artifacts` — the event's writer, not the gate, decides what counts as referenced |
| R8 | The ledger's summed `BudgetSpent` dollars/turns match `budget.dollars_spent` / `budget.turns_spent` |
| R9 | Every hard `spec_constraints` string appears in `brief.constraints` |
| R10 | No brief text field contains a phrase from the containment denylist (tool grants, permission changes, acceptance-criteria mutation, prompt-injection phrases like "ignore previous instructions", `sudo`) |

Under `GateMode.FULL_TRANSCRIPT`, R1–R5, R7, and R9 are auto-satisfied
(closure over the brief no longer means anything once the whole ledger range
is inlined into the prompt) — but R6, R8, and R10 still run, because they
check facts about the range and the brief's containment, not brief
completeness. R10 is the security control from the architecture threat model:
an untrusted brief field is data the *next* engine reads, so it is scanned
for injection before that handoff completes.

---

## 10. `job.py`, `spec.py`, `review.py`, `budget.py`

```python
# job.py
class JobState(StrEnum):
    READY="ready"; LEASED="leased"; SUCCEEDED="succeeded"; FAILED="failed"
    AWAITING_HUMAN="awaiting_human"; AWAITING_CAPACITY="awaiting_capacity"
    CANCELLED="cancelled"

@dataclass(frozen=True, slots=True)
class UnrecognizedJobState(UnrecognizedValue): ...   # never claimed; still counted
type StoredJobState = JobState | UnrecognizedJobState
JOB_STATE_PARSER: StoredValueParserInterface[JobState, UnrecognizedJobState]

# The gates the queue, the worker and BUILD raise on a job's behalf
ATTEMPTS_EXHAUSTED_GATE_KIND = "attempts_exhausted"       # every attempt failed (ADR-0024)
DELIVERY_EXHAUSTED_GATE_KIND = "delivery_exhausted"       # its worker died every time (ADR-0056)
ESCALATION_EXHAUSTED_GATE_KIND = "escalation_exhausted"   # build.implement's ladder is spent
DEFECT_GATE_KIND = "defect"            # the last failures were identical: rerun after a fix, or abandon
FOREIGN_BRANCH_GATE_KIND = "foreign_branch"   # a branch BUILD cannot prove is this project's
HANDOFF_INPUTS_GATE_KIND = "handoff_inputs_missing"   # a handed-off run cannot get the same run inputs
LOOP_CAPABILITIES_GATE_KIND = "loop_capabilities_unresolved"   # the capability snapshot cannot be given
QUEUE_GATE_KINDS = frozenset({ATTEMPTS_EXHAUSTED_GATE_KIND, DELIVERY_EXHAUSTED_GATE_KIND,
                              DEFECT_GATE_KIND})          # raised by the queue, read back only by it
GRANT_EXHAUSTION_KINDS = frozenset({ATTEMPTS_EXHAUSTED_GATE_KIND,
                                    ESCALATION_EXHAUSTED_GATE_KIND})   # offer more attempts

class FailureClass(StrEnum):
    CAPACITY="capacity"   # opens the circuit
    ENGINE="engine"       # opens after 3
    WORK="work"           # the code is wrong — circuit untouched
    VIBEY="vibey"         # our bug — circuit untouched

def backoff(attempt: int, *, base=timedelta(seconds=2), cap=timedelta(minutes=15)) -> timedelta: ...
def idempotency_key(project_id: UUID, cycle: int, kind: str, subject: str) -> str: ...


# queue_priority.py -- who may move a job ahead, and what moves with it (ADR-0054)
MOVABLE_STATES = {READY, LEASED, AWAITING_HUMAN, AWAITING_CAPACITY}

@dataclass(frozen=True, slots=True)
class Caller:                            # uid from the OS, name from pwd -- never $USER
    uid: int; name: str

class PriorityGrant:                     # the reviewed config's owner, + declared sources
    def decide(self, source: str | None, caller) -> PriorityDecision: ...
    # no source: admitted iff caller owns the anchor -> "operator:NAME"
    # a source:  admitted iff declared AND caller owns the anchor -> "source:NAME"

@dataclass(frozen=True, slots=True)
class QueuedJob:                         # the part of a row that decides its place
    id: UUID; state: StoredJobState; priority: int; run_after: datetime
    bump_seq: int | None = None; depends_on: tuple[UUID, ...] = ()
    bump_named: bool = False; phase_known: bool = True

class ClaimOrder:                        # the claim's ORDER BY, as a sort key
    def key(self, job: QueuedJob) -> tuple[bool, int, int, datetime, UUID]: ...
    # (bump_seq is None, bump_seq, -priority, run_after, id)

class BumpPlanner:                       # target + unfinished deps, deps first, relative
    def plan(self, target, jobs, *, finished_ok=False) -> BumpPlan: ...
    # order kept; a dependency that can never finish, or a ring, is refused
class UnbumpPlanner:                     # leave the named set, re-derive the lane; refused
    def plan(self, target, jobs) -> UnbumpPlan: ...   # while another named job needs it


# spec.py
class ConstraintKind(StrEnum):
    HARD = "hard"; SOFT = "soft"

@dataclass(frozen=True, slots=True)
class Constraint:
    text: str
    kind: ConstraintKind

@dataclass(frozen=True, slots=True)
class AcceptanceCriterion:
    criterion_id: str; given: str; when: str; then: str; fit: str

@dataclass(frozen=True, slots=True)
class NonFunctionalRequirement:
    nfr_id: str; attribute: str
    scale: str; meter: str; must: str; wish: str | None; fit_criterion: str
    # Planguage. "fast" is not an NFR; a scale and a meter are.

@dataclass(frozen=True, slots=True)
class DesignSpec:
    objective: str
    constraints: tuple[Constraint, ...]        # each hard|soft — R9 checks the hard ones
    non_goals: tuple[str, ...]
    criteria: tuple[AcceptanceCriterion, ...]
    nfrs: tuple[NonFunctionalRequirement, ...]
    walking_skeleton: str
    research_gaps: tuple[ResearchGap, ...] = ()   # topics not researched
    # (`[design.research] on_unavailable = "record_gap"`); taken from the ledger by the
    # synthesis handler, never from a model, so the spec states every gap

    def is_buildable(self) -> tuple[str, ...]:
        """Returns violations; empty means the DESIGN → BUILD guard can pass."""

    def hard_constraints(self) -> tuple[str, ...]:
        """The text of every HARD constraint — what noloss.py's R9 checks
        a handoff brief against."""


# review.py
class Severity(StrEnum): CRITICAL="critical"; HIGH="high"; MEDIUM="medium"; LOW="low"
class Ambiguity(StrEnum): CLEAR="clear"; NEEDS_CLARIFICATION="needs_clarification"
class UserVerdict(StrEnum): ACCEPT="accept"; CHANGES="changes"; CANCEL="cancel"

@dataclass(frozen=True, slots=True)
class FindingRef:
    """A pointer to a FindingRaised ledger event, carrying just enough to
    route the review loop-back decision without re-reading the ledger."""
    finding_id: str
    severity: Severity
    ambiguity: Ambiguity

@dataclass(frozen=True, slots=True)
class AssumptionDelta:
    assumption_id: str; text: str; seq: int

@dataclass(frozen=True, slots=True)
class FindingDelta:
    finding_id: str; severity: Severity; ambiguity: Ambiguity
    text: str; seq: int; resolved: bool = False

@dataclass(frozen=True, slots=True)
class DeltasReport:
    assumptions: tuple[AssumptionDelta, ...]
    findings: tuple[FindingDelta, ...]

def render_deltas_markdown(report: DeltasReport) -> str: ...   # deltas.md
def render_demo_markdown(spec: DesignSpec, *, evidence=None) -> str: ...   # DEMO.md, per criterion
def render_run_it_script(commands: Sequence[str] = ()) -> str: ...   # run-it.sh
def render_walkthrough_markdown(*, spec=None, summary="", work_items=()) -> str: ...   # walkthrough.md

def classify_finding_severity(text: str, category: str = "") -> Severity:
    """Keyword-based substring triage: security/vulnerability/cve/injection/
    "data loss"/corrupt/leak/critical/invariant -> CRITICAL; defect/missing/broken/
    fails/failure/regression/crash/error/high -> HIGH; cosmetic/nit/typo/
    doc/comment/formatting/low -> LOW; otherwise MEDIUM."""

def check_clear_conditions(text: str, *, spec=None, decisions=()) -> tuple[bool, str]:
    """Evaluates three of the four conjunctive conditions for
    Ambiguity.CLEAR: (1) the desired end state is stated unambiguously
    (>= 3 words, no hedging phrase such as "maybe", "not sure", "rethink"),
    (3) it implies no new NFR or architectural constraint (no phrase such
    as "requests per second", "microservices", "migrate to"), (4) it does
    not contradict a recorded decision (does not name a recorded
    alternative together with "switch"). Condition (2) — mapping to an
    existing or obviously-testable acceptance criterion — is NOT
    implemented: `spec` is accepted but unused."""

def triage_finding(finding_id: str, text: str, *, category="", spec=None, decisions=()) -> FindingRef:
    """Combines classify_finding_severity and check_clear_conditions into
    the FindingRef next_phase_after_review actually routes on."""


# budget.py
@dataclass(frozen=True, slots=True)
class BudgetLedger:
    turns_spent: int; dollars_spent: float
    max_turns: int | None; max_dollars: float | None

    @property
    def any_exhausted(self) -> bool: ...
    def would_exceed(self, projected: float) -> bool: ...
    def spend(self, *, turns=0, dollars=0.0) -> BudgetLedger: ...
```

`would_exceed` is checked **before** an effort escalation, not after — the
escalation ladder is the mechanism most likely to cause a cost snowball, so the
cap is evaluated on the projection, not the outcome.

---

## 11. `visual.py` and `media.py`

The visual-design interstitial's inventory, and the media-provider selection
that will eventually fill it in. Both are shape-only: generation, providers,
and moderation are separate, not-yet-implemented milestones (tasks 5.9–5.11,
plus the remaining design-system artifacts of 5.8); these modules only cover
*what a complete inventory looks like* and *which provider, if any, is
eligible*. The `visual.inventory` / `visual.plan` handlers consume `visual.py` through
`application/visual_spec.py` and `application/interfaces/visual.py`, and the
task-5.13 accept/waive gate (`application/visual_acceptance.py`) reads the
inventory they publish;
`media.py` has no consumer outside `domain/` yet.

```python
# visual.py
class MediaModality(StrEnum):
    IMAGE = "image"; AUDIO = "audio"; VIDEO = "video"

class SurfaceAction(StrEnum):
    CREATE = "create"; UPDATE = "update"

@dataclass(frozen=True, slots=True)
class MediaManifestEntry:
    asset_key: str
    modality: MediaModality
    prompt: str

@dataclass(frozen=True, slots=True)
class ScreenSurface:
    screen_id: str
    name: str
    action: SurfaceAction
    responsive_states: tuple[str, ...]
    accessibility_requirements: tuple[str, ...]
    media_manifest: tuple[MediaManifestEntry, ...]

@dataclass(frozen=True, slots=True)
class VisualInventory:
    surfaces: tuple[ScreenSurface, ...]

    def is_complete(self) -> tuple[str, ...]:
        """Returns violations; empty means the inventory can enter
        visual.plan. Requires at least one surface, and every surface to
        carry responsive states, accessibility requirements, and media
        manifest entries."""
```

```python
# media.py
@dataclass(frozen=True, slots=True)
class MediaProviderDescriptor:
    provider_id: str
    modalities: frozenset[MediaModality]        # MediaModality imported from visual.py
    reference_input_limit: int
    output_formats: frozenset[str]
    region: str
    retention_policy: str
    safety_policy: str
    cost_per_unit: float
    long_running: bool
    external: bool   # False: local/self-hosted, tried first. True: hosted fallback.

@dataclass(frozen=True, slots=True)
class MediaRequirement:
    modality: MediaModality
    allow_external: bool = False
    max_cost_per_unit: float | None = None

@dataclass(frozen=True, slots=True)
class MediaProviderRuntime:
    descriptor: MediaProviderDescriptor
    circuit_open: bool = False

def eligible(runtimes: Sequence[MediaProviderRuntime], *, requirement: MediaRequirement) -> tuple[MediaProviderRuntime, ...]:
    """Filters out providers with an open circuit, that lack the required
    modality, that are external when external isn't allowed, or that exceed
    a cost ceiling."""

@dataclass(frozen=True, slots=True)
class MediaCandidate:
    provider_id: str
    base_weight: int
    current: int
    order: int

    @property
    def effective_weight(self) -> int:
        return max(0, self.base_weight)

@dataclass(frozen=True, slots=True)
class MediaSelection:
    provider_id: str
    candidates: tuple[MediaCandidate, ...]   # updated SWRR state

def select(candidates: Sequence[MediaCandidate]) -> MediaSelection:
    """Smooth Weighted Round Robin, one modality at a time — the same
    algorithm as rotation.py's engine selection, reimplemented rather than
    shared because the two rotate different identity types and must be free
    to diverge (media has no capacity/circuit-breaker concept yet). Raises
    NoEligibleEngine on an empty candidate list or an all-zero-weight set;
    raises ValueError on a duplicate provider_id."""
```

The domain never imports an SDK or knows a provider/model name. It evaluates
capability, policy, region, health, and budget facts supplied by `application/`;
the infrastructure adapter performs the actual generation.

---

## 12. `briefing.py`

```python
def build_deterministic_brief(
    events: Sequence[LedgerEvent], *,
    objective="See the accepted spec in .vibey/context/spec.md.",
    spec_constraints=(), invariants=(), style_rules=(),
) -> HandoffBrief:
    """vibey's own floor producer for a HandoffBrief (handoff-protocol.md
    §6.5, option 4). Built directly from domain/projections.py's
    build_open_items and build_decision_log over the same ledger the no-loss
    gate checks against, so it always passes the gate by construction — no
    model call, less fluent than an LLM-written brief, but never lossy. This
    is what makes "all engines are down" a degraded-quality scenario rather
    than a data-loss one."""
```

`next_action` is taken from the first item in the latest `VerdictRendered`
event's `remaining_work`, or `"Review and accept."` if there is none;
`decisions` includes only decision refs that are not yet superseded.

---

## 13. `plan.py`

BUILD decomposition: the work-item graph and its two structural rules
(task 6.1, phase-protocols.md §2.1). `build.decompose` turns an accepted spec
into a dependency-ordered work-item graph.

```python
@dataclass(frozen=True, slots=True)
class VerificationSpec:
    """Exactly how a work item's completion will be checked."""
    commands: tuple[str, ...]
    criteria_checked: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class WorkItem:
    item_id: str
    title: str
    acceptance_ids: tuple[str, ...]
    depends_on: tuple[str, ...]
    est_effort: Effort
    files_touched_hint: tuple[str, ...]
    verification: VerificationSpec

class DecompositionPlanner:  # behind domain/interfaces/plan_interface.py
    def violations(
        self, items: Sequence[PlannedItemInterface], *,
        criteria_ids: Sequence[str], walking_skeleton_item_id: str,
    ) -> tuple[str, ...]:
        """Returns every violation, each named; empty means the decomposition
        can enter BUILD. Judged over the whole plan, before anything is
        enqueued. Checks: no duplicate item_id; every depends_on target
        exists; no dependency cycle (each strongly connected group named once,
        a self-dependency included); every acceptance criterion maps to >= 1
        work item (an unmapped criterion is a decomposition bug, not a
        judgment call); the named walking-skeleton item exists and has no
        dependencies — it goes first, alone, and must go green before anything
        else starts."""

    def in_dependency_order[ItemT: PlannedItemInterface](
        self, items: Sequence[ItemT]
    ) -> tuple[ItemT, ...]:
        """The same items, every dependency before its dependents. Stable (of
        the items ready together, the one listed first goes first), so an
        ordered plan comes back unchanged and the skeleton stays first. A
        cycle raises ValueError rather than returning part of the plan."""

DECOMPOSITION_PLANNER: DecompositionPlannerInterface = DecompositionPlanner()

def fold_verification_only(items: Sequence[WorkItem]) -> tuple[WorkItem, ...]:
    """Absorbs every item that builds nothing (an empty files_touched_hint) into the
    item it verifies: its criteria and checks move to the dependency listed last,
    which also inherits what the folded item waited for. An item with nothing to
    build, handed to an engine, is a session with nothing to do."""

def validate_decomposition(
    items: Sequence[WorkItem], *, criteria_ids: Sequence[str], walking_skeleton_item_id: str,
) -> tuple[str, ...]:
    """A facade over DECOMPOSITION_PLANNER.violations, kept because the
    work-plan producers call this name."""

def build_parallelism(*, config_parallelism: int | None, eligible_items: int, cpu_count: int) -> int:
    """min(config, eligible_items * 2, cpu_count). config_parallelism comes
    from phases.build.parallelism in vibey.toml (None means the default of
    4); eligible_items and cpu_count are supplied by the caller — the domain
    does not read them from the environment."""
```

---

## 14. `projections.py`

Pure projections over a replayed event range (architecture-and-roadmap.md
§4): every one of them is derived and disposable — rebuildable from the
ledger alone — which is what makes it safe to materialize any of them for
query speed without ever becoming a second source of truth.

```python
@dataclass(frozen=True, slots=True)
class OpenItemsView:
    questions: tuple[str, ...]
    decisions: tuple[str, ...]
    assumptions: tuple[str, ...]
    findings: tuple[str, ...]

def build_open_items(events: Sequence[LedgerEvent]) -> OpenItemsView: ...


@dataclass(frozen=True, slots=True)
class DecisionLogEntry:
    """ADR-shaped: every decision ever recorded, open or superseded."""
    decision_id: str; title: str; choice: str; rationale: str
    alternatives: tuple[str, ...]; superseded_by: str | None; seq: int

def build_decision_log(events: Sequence[LedgerEvent]) -> tuple[DecisionLogEntry, ...]: ...


@dataclass(frozen=True, slots=True)
class CostReportEntry:
    phase: Phase; engine_id: EngineId | None; turns: int; dollars: float

def build_cost_report(events: Sequence[LedgerEvent]) -> tuple[CostReportEntry, ...]:
    """Sums BudgetSpent events, grouped by (phase, engine_id)."""


@dataclass(frozen=True, slots=True)
class WorkLedgerEntry:
    """Per work-thread status, keyed by causation_id — the engine run that
    produced the verdict, and the closest thing the event log has to a stable
    work-item identifier. NOT correlation_id: that is the delivery's id and is
    identical for every event of the delivery (domain/correlation.py), so
    keying on it would collapse every work thread of a project into one row.
    Narrower than the full work_item table (which additionally tracks branch/
    worktree/verification state); answers "is this thread of work done, and
    what's left" from replay alone."""
    causation_id: str; complete: bool; remaining_work: tuple[str, ...]; last_seq: int

def build_work_ledger(events: Sequence[LedgerEvent]) -> tuple[WorkLedgerEntry, ...]: ...

def build_deltas(events: Sequence[LedgerEvent]) -> DeltasReport:
    """Every AssumptionStated and FindingRaised event in the run, so neither
    can be silently omitted from the review; findings carry their resolved
    state from any matching FindingResolved event."""

def answer_why_question(events: Sequence[LedgerEvent], question: str) -> str:
    """Answers a developer's free-text question by keyword-matching it
    against recorded DecisionRecorded and AssumptionStated events, so the
    answer explains the rationale actually on the ledger rather than
    inventing a new one from a fresh model call."""
```

---

## 15. `config.py`

Parsing and validation of the `vibey.toml` schema — see
[configuration reference](../reference/configuration.md) for the full field
list with defaults. Pure: this module accepts already-loaded TOML text or a
dict and returns either a validated `VibeyConfig` or raises `ConfigError`; it
never touches the filesystem — reading the file is an infrastructure concern.

```python
VALID_ISOLATION_LEVELS = ("worktree", "container", "vm")
VALID_EFFORTS = ("trivial", "low", "standard", "high", "max")
# "ultra" is deliberately absent: ULTRA is chosen with `vibey ultra`, never configured
DEFAULT_ENGINES = ("gptossloop",)   # the sovereign default, on without declaration
KNOWN_ENGINES = ("claudeloop", "codexloop", "gptossloop", "qwenloop", "claudeloop-local")
# "cursorloop" and "agyloop" are refused with ConfigError naming ADR-0078
# (RETIRED_ENGINES in engine.py)
LOCAL_ENGINE_FEATURES = {"gptossloop": "gptossloop", "qwenloop": "qwenloop",
                         "claudeloop-local": "claudeloop_local"}
LOCAL_ENGINES_ON_BY_DEFAULT = frozenset({"gptossloop"})   # ADR-0064

class ConfigError(VibeyError):
    def __init__(self, path: str, message: str) -> None: ...

@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str; repo: str = "."; max_cycles: int = 10; strict_loopback: bool = False

@dataclass(frozen=True, slots=True)
class IsolationConfig:
    level: str = "worktree"; allow_push: bool = False; egress: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class BudgetConfig:
    max_dollars_per_cycle: float | None = None
    max_dollars_total: float | None = None
    max_turns_per_item: int | None = None

@dataclass(frozen=True, slots=True)
class ClaudeloopLocalConfig:   # [engines.claudeloop_local] (ADR-0038)
    profile: str = "local"          # a [profiles.NAME] table in claudeloop's own config
    context_window: int = 32_768    # keep equal to the profile's and OLLAMA_CONTEXT_LENGTH
    structured_verdict: bool = False   # claimed only once conformance proves it

@dataclass(frozen=True, slots=True)
class EnginesConfig:
    enabled: tuple[str, ...] = DEFAULT_ENGINES
    weights: dict[str, int] = field(default_factory=dict)
    claudeloop_local: ClaudeloopLocalConfig = field(default_factory=ClaudeloopLocalConfig)

@dataclass(frozen=True, slots=True)
class PhaseConfig:
    effort: str = "standard"
    engines: tuple[str, ...] | None = None
    parallelism: int | None = None

@dataclass(frozen=True, slots=True)
class PhasesConfig:
    design: PhaseConfig  # default effort="high"
    build: PhaseConfig   # default effort="low"
    review: PhaseConfig  # default effort="high"

@dataclass(frozen=True, slots=True)
class ProvisionConfig:
    plugins: tuple[str, ...] = ()

@dataclass(frozen=True, slots=True)
class DeployConfig:
    enabled: bool = False; target: str = "openstack"; iac: str = "bicep"
    # "openstack" is the sovereign default cloud (8.b); "azure" has the built adapter

@dataclass(frozen=True, slots=True)
class FeaturesConfig:
    gptossloop: bool = True        # on unless switched off (ADR-0064)
    qwenloop: bool = False
    claudeloop_local: bool = False

@dataclass(frozen=True, slots=True)
class QwenloopConfig:
    backend: str = "auto"   # one of "auto", "llama.cpp", "vllm"
    portable_profile: str = "qwen2.5-coder-14b-q5-k-m"
    nvidia_profile: str = "qwen2.5-coder-14b-bf16"
    idle_timeout_seconds: int = 900
    startup_timeout_seconds: int = 180
    context_window: int = 32_768

@dataclass(frozen=True, slots=True)
class VibeyConfig:
    project: ProjectConfig
    isolation: IsolationConfig = field(default_factory=IsolationConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    engines: EnginesConfig = field(default_factory=EnginesConfig)
    phases: PhasesConfig = field(default_factory=PhasesConfig)
    provision: ProvisionConfig = field(default_factory=ProvisionConfig)
    deploy: DeployConfig = field(default_factory=DeployConfig)
    notifications: NotificationsConfig      # desktop alerts and signed webhooks
    telemetry: TelemetryConfig              # in-process span and sample caps
    features: FeaturesConfig = field(default_factory=FeaturesConfig)
    qwenloop: QwenloopConfig = field(default_factory=QwenloopConfig)
    # The sovereign-default operational surfaces (ADR-0042; sub-doctrine 8.b), each a
    # self-hosted adapter by default and a paid relay only by declaration:
    tracker: TrackerConfig; docs: DocsConfig; secrets: SecretsConfig
    files: FilesConfig; email: EmailConfig; sms: SmsConfig
    messaging: MessagingConfig; config_store: ConfigStoreConfig
    cache: CacheConfig; bus: BusConfig; blob: BlobConfig; siem: SiemConfig
    surfaces: SurfacesConfig                # shared adapter settings (timeouts)
    queue: QueueConfig                      # priority sources (ADR-0054), reap thresholds (ADR-0056)
    design: DesignConfig                    # incl. [design.research] on_unavailable
    build: BuildConfig                      # slicing into CDD layers (ADR-0092)
    engine_dispatch: EngineDispatchConfig   # [engines] mode, slots, overflow (ADR-0079)
    publish: PublishConfig                  # [publish] mode off | interview | auto
    # 29 tables in all; every one has a default, so only [project] is required.

def parse_toml_string(text: str) -> dict[str, Any]: ...   # stdlib tomllib.loads

def parse_config(data: dict[str, Any]) -> VibeyConfig:
    """Raises ConfigError on the first violation found. A local engine may
    only be requested (in engines.enabled or any phase's engines list) while
    its switch is on: `qwenloop` once features.qwenloop is true, `gptossloop`
    unless features.gptossloop is false. The sovereign default is added to any
    engines.enabled list; without an explicit list, every switched-on local
    engine is added to the default engine set automatically."""

def load_config_from_string(text: str) -> VibeyConfig: ...
    # = parse_config(parse_toml_string(text))
```

Config parsing can live in `domain/` because `tomllib` is stdlib. Reading the
file is `infrastructure/config_loader.py::load_config_from_path`, and it has a runtime
caller: `StartupConfigResolver.resolve` parses `./vibey.toml` in full at process start
(`bootstrap.py`) and configures the operational surfaces, telemetry and the queue from it;
a file that fails to parse is logged and skipped. `load_runtime_config_from_path` copies the
runtime tables (`notifications`, `telemetry`, `gates`, `engine_environment`, `design`,
`build`, `human_gates`, `publish` and the dispatch keys of `[engines]`) into the project
record at `vibey new`. (An earlier version of this page said the loader had no runtime
caller; that was true on 2026-09-15 and is not now.) `[engines] enabled` and `weights`,
`[phases]`, `[budget]`, `[provision]` and `[deploy]` are parsed but not read at runtime as of
2026-11-24. The `VIBEY_FEATURE_*` overrides are applied by
`infrastructure/engines/local_engines.py::LocalEngineSettings`, the one resolver
the worker, `vibey doctor` and `vibey loops` share. The full schema is in
[`docs/reference/configuration.md`](../reference/configuration.md).

---

## 16. `provision.py`

Agent-surface provisioning content rules (task 6.3, ADR-0011): one source of
truth for the non-negotiables/plugins/context block, materialized
idempotently into five router files (`CLAUDE.md`, `AGENTS.md`, `CURSOR.md`,
`GEMINI.md`, `QWEN.md`). `CURSOR.md` and `GEMINI.md` belonged to `cursorloop` and
`agyloop`, which ADR-0078 retired; `RouterFile` still lists them, so they are still written,
though no engine vibey runs reads them. Pure content generation and the
marker-delimited merge that preserves hand-written guidance outside vibey's
block; the actual filesystem/git I/O lives in `infrastructure/provision/`.

```python
BEGIN_MARKER = "<!-- vibey:begin -->"
END_MARKER = "<!-- vibey:end -->"

class RouterFile(StrEnum):
    """Agent guidance surfaces, including qwenloop's local-agent router."""
    CLAUDE = "CLAUDE.md"; AGENTS = "AGENTS.md"; CURSOR = "CURSOR.md"
    GEMINI = "GEMINI.md"; QWEN = "QWEN.md"

@dataclass(frozen=True, slots=True)
class ProvisionSpec:
    non_negotiables: tuple[str, ...]
    plugins: tuple[str, ...]

def render_block(spec: ProvisionSpec) -> str:
    """Renders the marker-delimited, generated block: non-negotiables,
    skill plugins, and a pointer to .vibey/context/."""

def merge_router(existing: str | None, block: str) -> str:
    """Preserves any hand-written content outside vibey's markers; replaces
    only vibey's own block between BEGIN_MARKER/END_MARKER, or appends the
    block to unmarked existing content (or returns it standalone if there is
    no existing content)."""

def content_digest(content: str) -> str:
    return hashlib.sha256(content.encode()).hexdigest()

def needs_write(existing: str | None, rendered: str) -> bool:
    """The idempotence check (ADR-0011): true only when writing would
    actually change the file, so re-provisioning with correct digests
    already present writes nothing."""
```

---

## 17. `worktree.py`

Pure naming rules for BUILD work-item worktrees (task 6.2): no I/O, just the
deterministic path/branch scheme the infrastructure worktree manager uses,
kept pure so the manager and any future caller (e.g. a status report) never
disagree about where a work item's worktree lives.

```python
def validate_item_id(item_id: str) -> None:
    """Raises ValueError unless item_id is 1-64 chars, lowercase
    alphanumeric and hyphens, starting with alphanumeric."""

@dataclass(frozen=True, slots=True)
class WorktreeNaming:
    project_id: UUID
    cycle: int                      # >= 1
    namespace: str = "vibey"        # the first segment of every branch

    scope -> str                    # project_id.hex[:8]
    managed_root -> str             # ".vibey/worktrees/<scope>/<cycle>"
    integration_branch -> str       # branch("integration")
    def worktree_subpath(self, item_id: str) -> str:  # "<managed_root>/<item_id>"
    def branch(self, item_id: str) -> str:            # "<namespace>/<scope>/<cycle>/<item_id>"
    def legacy_branch(self, item_id: str) -> str:     # "<namespace>/<cycle>/<item_id>"
    def resolve_base(self, ref: str) -> str:          # legacy integration -> own
    def is_managed(self, ref: str) -> bool:           # ref in "<namespace>/"

@dataclass(frozen=True, slots=True)
class BranchOwnership:
    branch: str
    project_id: str | None          # as recorded; None when nothing was
    base: str | None                # the commit the branch was cut from
    def verify(self, project_id: UUID) -> str:        # the base, or ForeignBranchRefused
```

Every name raises `ValueError` (via `validate_item_id`) before it is produced, so no
path or branch is ever built from an unvalidated id. The integration branch uses the
reserved item id `integration` (`vibey/<scope>/<cycle>/integration`).

**Names carry the project.** They were keyed by cycle alone (`vibey/<cycle>/<item>`), and
every project in a repository shares its refs, so a delivery in cycle 1 built on an
unrelated project's `vibey/1/ws`. `scope` makes two projects' names differ; eight hex
digits make a collision unlikely, not impossible, so `BranchOwnership` is the proof: the
infrastructure records it beside every branch it creates (in the branch's config section)
and `verify` refuses any branch whose record does not name this project
(`ForeignBranchRefused`, parked on the `foreign_branch` gate). `legacy_branch` is only
recognised, never created: an old job's cycle-keyed integration base is read, by
`resolve_base`, as the project's own ([ADR-0008](../architecture/decisions/0008-worktree-isolation.md)).

Returns a relative path string rather than a `pathlib.Path`: `domain/`
forbids `pathlib` (checked by `test_domain_purity.py`), so joining this onto
a repo root is the infrastructure layer's job.

---

## 18. `verbosity.py`

Resolving how loud the process should be, from CLI flags. Pure: no logging
library, no I/O — the ladder is a domain decision because it has to mean the
same thing everywhere; an operator who learns `-dd` on one runner should not
get something different from the next one.

```python
VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

class Verbosity(IntEnum):
    """QUIET and NORMAL differ only in level. The three DEBUG tiers differ in
    *scope*: our own logs, then third-party libraries, then full payloads —
    because "more detail" past DEBUG is not a level, it is a wider net."""
    QUIET = -1; NORMAL = 0; VERBOSE = 1; TRACE = 2; FIREHOSE = 3


@dataclass(frozen=True, slots=True)
class LogPlan:
    """The resolved logging intent a composition root acts on."""
    level: str
    include_third_party: bool
    include_payloads: bool


def parse_verbosity(*, verbose: int = 0, quiet: bool = False) -> Verbosity:
    """Raises ValueError if --quiet and --verbose are both set."""

def resolve_log_plan(*, verbose: int = 0, quiet: bool = False, log_level: str | None = None) -> LogPlan:
    """An explicit --log-level always wins over the -d count — naming a
    level and having it silently overridden by a count (possibly set in an
    alias) would be more surprising than honouring it. The count still
    widens scope independently, so `--log-level WARNING -ddd` is a
    legitimate way to ask for warnings from everything: include_third_party
    from TRACE and up, include_payloads from FIREHOSE."""
```

**The count flag is `-d`, not `-v`.** Since #1898, `vibey -v` / `--version` prints the
versions of `vibey-engine` and `krypton-app` and exits, and the count is `-d` /
`--verbose` (`-d`, `-dd`, `-ddd`; `src/vibey/cli/main.py`). The `verbose` parameter above
is that `-d` count.

---

## 19. Security primitives: `command_guard.py`, `scope_guard.py`, `prompt_shield.py`

Three self-contained defensive modules with full unit coverage. They are
plain classes rather than frozen dataclasses, and `frame_untrusted_input` is
deterministic only when a `nonce` is passed. **None of them are constructed
anywhere in `bootstrap.py`**, and nothing in `application/` or
`infrastructure/` calls them — see
[SECURITY.md](../../SECURITY.md) for the current disclosure of what this
means for the guarantees vibey actually provides today; do not rely on any
of them being enforced inside a run until that changes. One caller exists outside
`src/vibey/`: the triaged-delivery intake, `scripts/intake_trust.py`, frames admitted issue
text through `PromptShield` so the model reads it as data. (The ACP agent has its own
untrusted-text handling in `domain/acp/untrusted_text.py`.)

```python
# command_guard.py — destructive-command prevention
@dataclass(slots=True, frozen=True)
class BlockedMatch:
    command: str; rule_id: str; description: str

class DestructiveCommandBlocked(Exception):
    def __init__(self, match: BlockedMatch) -> None: ...

def scan_command(command: Sequence[str] | str) -> BlockedMatch | None:
    """Matches the command string (argv joined with spaces if given a
    sequence), case-insensitively, against a fixed table of regexes:
    git reset --hard; git push with --force, -f or --force-with-lease;
    git branch -D or -d on main/master; rm with -r/-f flags on /, /*, ~, ~/
    or a bare *; mkfs[.fs]; dd ... of=/dev/*; chmod -R <mode> /;
    shutdown/reboot/poweroff/init 0|6; the :(){ :|:& };: fork bomb; SQL
    DROP DATABASE and DROP TABLE. Rule ids: GIT_HARD_RESET, GIT_FORCE_PUSH,
    GIT_DELETE_MAIN, FS_ROOT_RM, FS_MKFS, FS_RAW_DD, FS_CHMOD_ROOT,
    SYS_POWER, SYS_FORK_BOMB, SQL_DROP_DATABASE, SQL_DROP_TABLE. Returns the
    first match or None."""

class CommandSecurityPolicy:
    def is_allowed(self, command: Sequence[str] | str) -> bool: ...
    def check_command(self, command: Sequence[str] | str) -> None:
        """Raises DestructiveCommandBlocked on a match."""


# scope_guard.py — mutation scope enforcement
class ScopeViolation(Exception):
    def __init__(self, path: str, reason: str) -> None: ...

class MutationScope:
    """Enforces that mutations stay within declared scope boundaries."""
    def __init__(self, *, worktree_root: str, allowed_paths: Sequence[str] | None = None,
                 allow_new_files: bool = True) -> None: ...
    def is_path_allowed(self, path: str) -> bool: ...
    def validate_path(self, path: str) -> str:
        """Returns the normalized relative path, or raises ScopeViolation
        for path traversal, an absolute path outside worktree_root, a
        sensitive path (.git/, secrets.json, id_rsa/id_ed25519/id_ecdsa,
        .env*), or a path outside the declared allowed_paths."""
    def validate_batch(self, paths: Sequence[str]) -> list[str]: ...


# prompt_shield.py — untrusted-content framing and sanitization
@dataclass(slots=True, frozen=True)
class ShieldedPrompt:
    framed_text: str; nonce: str; sanitized_input: str

class PromptShield:
    def sanitize_text(self, text: str) -> str:
        """Strips ANSI escape sequences and non-whitespace control chars."""
    def is_suspicious_injection(self, text: str) -> bool:
        """Regex match against common injection phrases ("ignore previous
        instructions", "system prompt override", "act as root", …)."""
    def frame_untrusted_input(self, text: str, label: str = "untrusted_content",
                               nonce: str | None = None) -> ShieldedPrompt:
        """Sanitizes the text, escapes any attempted closing-tag breakout
        for the given label, and wraps it in a nonce-tagged delimiter pair
        with an explicit "treat this as data" directive."""
```

---

## 20. `deployment.py`

Immutable `DeploymentSpec`, consent verification, and failure-routing policy
for the ④–⑥ deployment stage set (task 10.2).

```python
@dataclass(slots=True, frozen=True)
class AzureTargetScope:
    tenant_id: str; subscription_id: str; resource_group: str
    environment: str; region: str; tags: Mapping[str, str] = field(default_factory=dict)

    def digest(self) -> str:
        """Deterministic SHA256 of tenant/subscription/resource-group/environment."""

@dataclass(slots=True, frozen=True)
class IdentityAuthority:
    identity_type: str; principal_id: str; approved_roles: Sequence[str] = ()

@dataclass(slots=True, frozen=True)
class TopologyConfig:
    service_type: str; iac_provider: str; sku: str
    instances: int = 1; ingress_enabled: bool = True; tls_enabled: bool = True

@dataclass(slots=True, frozen=True)
class RecoveryPolicy:
    progressive_exposure: str
    auto_rollback_on_health_failure: bool = True
    max_rollback_attempts: int = 2

@dataclass(slots=True, frozen=True)
class VerificationContract:
    health_endpoint: str = "/health"
    smoke_tests: Sequence[str] = ()
    bake_window_seconds: int = 60

@dataclass(slots=True, frozen=True)
class CostBoundary:
    max_monthly_budget_usd: float
    max_deployment_cost_usd: float

@dataclass(slots=True, frozen=True)
class DeploymentSpec:
    spec_id: str; version: str
    target_scope: AzureTargetScope; identity: IdentityAuthority
    topology: TopologyConfig; recovery_policy: RecoveryPolicy
    verification: VerificationContract; cost_boundary: CostBoundary
    secret_references: Sequence[str] = ()

    def scope_digest(self) -> str: ...
    def validate(self) -> list[str]:
        """Every field-presence and non-negative-cost check, plus: each
        secret_references entry must use an approved Key Vault reference
        scheme (@microsoft.keyvault, keyvault:, vault:, ref:, kv:) — a raw
        secret value or unrecognized scheme is a validation error, not a
        silently accepted string."""
    def is_valid(self) -> bool: ...


@dataclass(slots=True, frozen=True)
class DeploymentConsent:
    consent_id: str; target_scope_digest: str
    granted_by: str; granted_at: datetime
    explicit_mutation_authorized: bool = True

    def matches_spec(self, spec: DeploymentSpec) -> bool:
        return self.explicit_mutation_authorized and self.target_scope_digest == spec.scope_digest()


class DeploymentFailureClass(StrEnum):
    TRANSIENT_CAPACITY = "transient_capacity"; IDEMPOTENT_CONFLICT = "idempotent_conflict"
    CAP_EXHAUSTED = "cap_exhausted"; MISSING_AUTHORITY = "missing_authority"
    POLICY_DENIAL = "policy_denial"; AMBIGUOUS_CONFIGURATION = "ambiguous_configuration"
    DESTRUCTIVE_DATA_MIGRATION = "destructive_data_migration"
    RECOVERY_OUTSIDE_RUNBOOK = "recovery_outside_runbook"; APPLICATION_DEFECT = "application_defect"

class DeploymentRoute(StrEnum):
    STAY_IN_EXECUTE = "stay_in_execute"; ENTER_REVIEW = "enter_review"
    ROUTE_TO_DESIGN = "route_to_design"; ROUTE_TO_DEPLOY_DESIGN = "route_to_deploy_design"

def classify_deployment_failure(failure_class: DeploymentFailureClass) -> DeploymentRoute:
    """Per ADR-0013: transient capacity or an idempotent conflict -> stay in
    DEPLOY_EXECUTE and retry; an application defect -> back to DESIGN;
    everything else -> DEPLOY_REVIEW for a human decision."""


class ChangeAction(StrEnum):
    CREATE = "create"; MODIFY = "modify"; DELETE = "delete"; NO_CHANGE = "no_change"

@dataclass(slots=True, frozen=True)
class NormalizedResourceChange:
    resource_id: str; resource_type: str; action: ChangeAction
    estimated_monthly_cost_usd: float = 0.0
    details: Mapping[str, object] = field(default_factory=dict)

@dataclass(slots=True, frozen=True)
class PlanEvaluation:
    changes: Sequence[NormalizedResourceChange]
    total_estimated_monthly_cost_usd: float
    has_destructive_deletions: bool
    exceeds_budget: bool
    is_safe_for_automated_apply: bool
    blocking_reasons: Sequence[str]

def evaluate_iac_plan(changes, cost_boundary) -> PlanEvaluation:
    """Not safe for automated apply if any change is a DELETE, or if the
    summed estimated monthly cost exceeds cost_boundary.max_monthly_budget_usd."""


class DeploymentLadderDecision(StrEnum):
    RETRY = "retry"; ROLLBACK = "rollback"; HALT_AND_TRIAGE = "halt_and_triage"

@dataclass(slots=True, frozen=True)
class DeploymentAttemptRecord:
    attempt_number: int; elapsed_seconds: float; total_spent_usd: float
    last_failure_class: DeploymentFailureClass | None = None

def evaluate_retry_ladder(attempt, spec) -> tuple[DeploymentLadderDecision, str]:
    """Halts to triage when total spend exceeds the dollar cap, when elapsed
    time exceeds 1800s, or once attempt_number reaches
    max_rollback_attempts + 1 (with the default of 2, the third attempt
    halts). Otherwise: a transient
    failure class retries with backoff; any other failure rolls back if
    recovery_policy.auto_rollback_on_health_failure, else halts to triage."""


class ExposureType(StrEnum):
    REVISION = "revision"; SLOT = "slot"; CANARY = "canary"
    BLUE_GREEN = "blue_green"; STAMP = "stamp"

class RecoveryActionType(StrEnum):
    ROLLBACK = "rollback"; ROLL_FORWARD = "roll_forward"; FALLBACK = "fallback"

@dataclass(slots=True, frozen=True)
class RecoveryAction:
    action_type: RecoveryActionType
    target_revision_or_slot: str
    initiated_reason: str
    max_attempts: int = 2

def evaluate_exposure_step(current_percent, *, is_healthy, policy, step_size=25) -> tuple[int, RecoveryAction | None]:
    """Unhealthy -> roll back to 0% (if auto-rollback enabled) or hold at
    the current percent with a FALLBACK action. Healthy -> advance by
    step_size, capped at 100, with no action."""


class VerificationDimension(StrEnum):
    CONVERGENCE = "convergence"; HEALTH = "health"; SMOKE = "smoke"; BAKE_WINDOW = "bake_window"

@dataclass(slots=True, frozen=True)
class VerificationResult:
    passed: bool
    dimension_results: Mapping[str, bool]
    failed_dimension: VerificationDimension | None = None
    failure_reason: str | None = None

def evaluate_verification_contract(
    contract, *, convergence_succeeded, health_status_code, smoke_commands_passed, bake_window_errors_count,
) -> VerificationResult:
    """Checks all 4 dimensions in order — convergence, then a 2xx health
    status, then smoke tests, then a zero-error bake window — and fails
    fast on the first one that doesn't pass."""
```

---

## 21. Errors

`src/vibey/domain/errors.py` defines 44 classes (counted 2026-11-24), all under
`VibeyError`:

```python
class VibeyError(Exception): ...
class InvalidPhaseError(VibeyError): ...       # a PhaseState with invalid fields
class IllegalTransitionError(VibeyError): ...  # evaluate_transition denied it
class NoEligibleEngine(VibeyError): ...        # no candidate with positive weight
class EscalationExhausted(VibeyError):
    def __init__(self, attempt: int) -> None: ...
class HandoffRejected(VibeyError):
    def __init__(self, result: GateResult) -> None: ...
class InvalidSpecError(VibeyError): ...
class BudgetExceeded(VibeyError): ...
class InvalidBudgetChange(VibeyError): ...     # `vibey budget set` asked for a non-cap
class InvalidActorLabel(VibeyError): ...       # a `--by` name that cannot be recorded
class UnknownGate(VibeyError, LookupError): ...
class GateAlreadyAnswered(VibeyError): ...     # answered once already; the first answer stands
class ForeignBranchRefused(VibeyError): ...    # BUILD cannot prove the branch is this project's
class UnknownProject(VibeyError):
    """No project exists with the given id."""
class InputStoreError(VibeyError): ...         # run inputs (ADR-0104, ADR-0105)
class InputStoreUnavailable(InputStoreError): ...   # e.g. a SeaweedFS store that did not answer
class HandoffInputsMissing(VibeyError): ...    # a handed-off run cannot get its predecessor's inputs
class RunInputRefused(VibeyError): ...         # not a `paste` or `file`, or a bad name
class UnknownLane(VibeyError, LookupError): ...
class WrongPhase(VibeyError):
    """The project is not in a phase the requested command applies to."""
class CheckoutHeld(VibeyError): ...            # two live projects never share a checkout (0021)
class InvalidAbandonment(VibeyError): ...      # `vibey abandon` with an unrecordable reason
class AbandonmentRefused(VibeyError): ...      # done, or a phase it cannot be abandoned from
class InvalidAnswer(VibeyError):
    """A human-gate answer was not in the expected QUESTION_ID=ANSWER form."""
class UnknownProvider(VibeyError):
    """The requested engine provider is not one vibey knows how to build."""
class SovereignResearchUnavailable(VibeyError): ...   # research refused a topic rather than invent a source
class ReorderRefused(VibeyError): ...      # queue priority (ADR-0054): every one is recorded
class UnknownJob(ReorderRefused): ...
class NotReorderable(ReorderRefused): ...  # finished, or a state/phase this vibey does not know
class DependencyCycle(ReorderRefused): ... # a ring the planner will not order
class DependencyCannotFinish(ReorderRefused): ...  # a failed or cancelled dependency
class DependentsStillBumped(ReorderRefused): ...   # un-bump them first
class ReorderConflict(ReorderRefused): ... # the database broke a lock cycle; retry
class PriorityRefused(ReorderRefused): ... # no grant (12.j)
class HandbackRefused(VibeyError): ...     # no successful probe since the failover (ADR-0070)
class LeaseReapIncomplete(VibeyError): ... # some expired leases could not be reaped (ADR-0056)
class ClassifiedFailure(VibeyError): ...   # a failure that already knows its FailureClass
class OutputBudgetExhausted(ClassifiedFailure): ...   # a local model spent its output budget, no answer
class ModelAnswerRejected(ClassifiedFailure, ValueError): ...   # wrong shape after one re-ask
class LifecycleRefused(VibeyError): ...    # a hub start/pause/resume/unwind refused (ADR-0091)
class LifecycleInvalid(LifecycleRefused): ...      # what the device sent is not acceptable
class LifecycleConflict(LifecycleRefused): ...     # a folder or checkout is taken
class LifecycleUnavailable(LifecycleRefused): ...  # not allowed, or the Sabbath window
class LifecycleFailed(LifecycleRefused): ...       # the command the host ran failed
```

`ConfigError` (§15) lives in `config.py`, and a handful of modules define errors of their
own beside the code that raises them (for example `WebToolRefused` and its siblings in
`web_tools.py`).

---

## 22. What must never appear in `domain/`

Checked by `import-linter` (`.importlinter`, contract `domain-independence`)
and by `tests/domain/test_domain_purity.py`, which walks the AST:

- `import asyncio`, `async def`, `await`, `async with`, `async for`
- `open()`, `pathlib`, `subprocess`, `socket`, `os.getenv()`
- `asyncpg`, `psycopg`, `httpx`, `requests`, `typer`, `structlog`,
  `pydantic`, `textual`
- `vibey_bootstrap` — forbidden by name (ADR-0017); dependency-free family
  packages (`vibey_gh`, `vibey_skills`, `vibey_runners.common`) are allowed
- `vibey.application`, `vibey.infrastructure`, `vibey.cli`, `vibey.tui`
- `datetime.now()`, `datetime.today()`, `time.time()` — time is always a
  parameter, never ambient

`os.environ` access is **not** caught today: the AST walker checks only calls
of the form `module.attr()`, and although the test module defines an
`("os", "environ")` pair in `FORBIDDEN_CALLS`, that set is never consulted.
No domain module reads the environment; the rule is held by review, not by the
test.

That last one is why every function here takes `now: datetime`. It is what makes
the wait-policy and circuit-breaker tests deterministic instead of flaky.

**One interface beside every class.** Since
[ADR-0016](../architecture/decisions/0016-classes-behind-interfaces.md), each class in
`domain/` has a declaring Protocol in `domain/interfaces/` (`sovereign_model.py` implies
`interfaces/sovereign_model_interface.py`). Interfaces declare; they never consume.

---

## 23. The rest of `domain/`, one line each

Sections 2–22 cover the core the original plan named. These modules were added later;
each line is the module's own docstring, shortened, with the decision record that explains
it. Read the module before relying on any of them.

| Module | What it holds |
|---|---|
| `abandonment` | Abandoning a project (`vibey abandon`): the operator's clean exit |
| `actor_label` | Who a person-made record says made it: a label the caller chose, or its account |
| `budget_caps` | A project's cycle caps: what a change to them is, and the record of every change |
| `correlation` | The delivery correlation id: one identifier for one delivery, end to end |
| `defect` | Telling a defect from bad luck: when a job's failures are all the same one (the `defect` gate) |
| `design_default_scope` | The narrowest-scope default for a DESIGN interview question |
| `driver_brief` | The driver's handoff brief and its no-loss gate ([ADR-0070](../architecture/decisions/0070-failover-to-the-sovereign-engine-and-handback-on-a-recorded-probe.md)) |
| `engine_dispatch` | Hybrid engine dispatch: local slots, wait, paid overflow and its daily cap ([ADR-0079](../architecture/decisions/0079-hybrid-engine-dispatch.md)) |
| `failover` | Failover to the sovereign engine, and handback after a recorded probe (ADR-0070) |
| `gate_answer` | A gate is answered once: what identifies one answering request |
| `gate_auto_answer` | Which waiting gates a worker may answer for the operator who asked it to, and with what |
| `gate_notice` | Gate notices: whether a person was told a gate is waiting, as evidence |
| `gate_timeout` | Which gate kinds a project lets resolve to their default after waiting (`[human_gates] timeout_defaults`; only `choice`, `deploy_interview`, `deploy_failure_triage`, `deploy_acceptance`, `deploy_demo_review`) |
| `handoff_inputs` | Which run inputs a handed-off run must be given |
| `host_clients` | The planner and config merger for `vibey connect` ([ADR-0100](../architecture/decisions/0100-host-driven-mcp-interface-and-chat-first-surfaces.md)) |
| `host_health` | What `vibey doctor` says about the machine's health |
| `host_tools` | The host-LLM tool catalogue: every action a chat client drives through MCP (ADR-0100) |
| `hub_binding` | Where the hub may listen, and which names a request may reach it by |
| `hub_chat` | The hub's chat command parser and turn renderer (ADR-0100) |
| `hub_pairing` | Pairing a device with the hub, and what a paired device's request must prove ([ADR-0071](../architecture/decisions/0071-hub-pairing-and-trust.md)) |
| `hub_scope` | What a caller of the hub may do: scopes, the actions they cover, and the ones none does |
| `hub_target` | Where a hub credential, or a probe of the hub, may be sent: this computer's loopback only |
| `input_ledger` | The ledger, not the store, decides what a run is given |
| `integration_evidence` | What the integration gates actually did, as REVIEW's evidence |
| `ledger_chain` | The ledger's hash chain: tamper evidence derived from the rows, stored nowhere |
| `ledger_query` | A ledger search, as a value that cannot be built invalid (`vibey ledger search`) |
| `ledger_record` | A ledger event as a JSON object, written one way and read back one way |
| `ledger_tier` | Configuration values for ledger storage tiers |
| `llm_tooling` | Which of vibey's LLM-facing surfaces each client has, and what to do about one it lacks |
| `local_stack` | The local dependency configuration the installer uses (`vibey install`) |
| `loop_capabilities` | What the ledger records of the capability snapshot a run was given ([ADR-0103](../architecture/decisions/0103-the-loop-capability-bundle.md)) |
| `marketplace_source` | Which marketplace sources vibey fetches, and how (ADR-0103) |
| `model_families` | The local model families vibey knows by name ([ADR-0093](../architecture/decisions/0093-local-model-families-are-named-and-measured-not-assumed.md)) |
| `phase_timing` | Phase timing: the measured history an honest estimator needs |
| `plan_references` | A plan's verification may only run or read files something provides |
| `publication_policy` | What of a ledger a public shard may carry (`vibey ledger site`) |
| `publish` | What publishing a finished project proposes, and how a person's answer changes it (`review.publish`) |
| `queue_reap` | Queue reaping by measurement, never by feel ([ADR-0056](../architecture/decisions/0056-everything-a-queue-guards-is-reaped-by-measurement.md)) |
| `remote_command` | A vibey command run on the repository's GitHub-hosted runners (`vibey -w`, [ADR-0085](../architecture/decisions/0085-vibey-on-the-workflows.md)) |
| `repair_convergence` | When a repair that changes nothing is a reason to stop repairing (the `repair_not_converging` gate) |
| `research_gap` | What DESIGN research does when no evidence can be had, and the record it leaves |
| `residency` | Residency policy for seat slugs and model selection |
| `run_input` | A run input: one pasted text or one file given to every BUILD run of a project ([ADR-0104](../architecture/decisions/0104-run-inputs-hash-addressed.md)) |
| `run_ownership` | Whose command a run on the workflows is: request ids the hub mints for one principal (ADR-0085) |
| `sabbath` | The Sabbath window as the domain sees it (sub-doctrine 8.i, [ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md)) |
| `searxng` | The local SearXNG vibey installs and runs itself, its pure half ([ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md)) |
| `slicing` | Multi-layer slicing of a BUILD decomposition into the CDD layers ([ADR-0092](../architecture/decisions/0092-large-tasks-are-sliced-into-the-cdd-layers-before-they-run.md)) |
| `sovereign_model` | Which weights the local loop runs: `heretic` (the default, `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`) or `stock` (`gpt-oss:20b`); `VIBEY_SOVEREIGN_MODEL` picks one, `VIBEY_OLLAMA_MODEL` names any tag and wins ([ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)) |
| `state_sync` | One vibey database's rows, kept the same at both ends (`vibey state`, [ADR-0086](../architecture/decisions/0086-state-sync.md)) |
| `stored_value` | Reading a closed vocabulary back out of storage, forward-compatibly (vibey#287; §2) |
| `supervisor` | The declared supervisor: what keeps vibey's long-running processes alive (`vibey supervisor`) |
| `ultra` | ULTRA, the pure half ([ADR-0063](../architecture/decisions/0063-ultra-effort-without-a-ceiling.md)) |
| `web_tools` | Search and fetch served from the hub: what may be fetched, from where, how much, and what the ledger records (ADR-0102) |

Two packages sit beside the modules: `domain/acp/` (the ACP agent's pure half: modes,
protocol, session state and replay, settings and their trust, untrusted text, gate
permission; [ADR-0101](../architecture/decisions/0101-the-acp-agent-and-self-installing-services.md))
and `domain/interfaces/` (ADR-0016).

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `AttributeError: type object 'EngineId' has no attribute 'CURSORLOOP'` (or `'AGYLOOP'`) | Code written from an old copy of §4; the members were removed by ADR-0078 | Use `EngineId.CLAUDELOOP` or `EngineId.CODEXLOOP` for a paid engine |
| `ValueError: 'cursorloop' is not a valid EngineId -- cursorloop was retired by ADR-0078 ...` | A flag, allow-list or config named a retired engine | Remove it; see `RETIRED_ENGINES` |
| `KeyError` on a `Mapping[EngineId, ...]` with a stored engine id | The id came back as an `UnrecognizedEngineId` | Narrow with `isinstance(engine_id, EngineId)` before using it as a key (§4) |
| `tests/domain/test_domain_purity.py` fails after your change | A domain module now does I/O, awaits, reads the clock or imports an outer layer | Move that part to `application/` or `infrastructure/` and pass the value in (§22) |

## Where next

- [architecture-and-roadmap.md](architecture-and-roadmap.md), for how these types meet the
  queue, the workers and the engines.
- [handoff-protocol.md](handoff-protocol.md), for the full specification of §9's gate.
- `src/vibey/domain/` itself: this page summarises, the module decides.

## Say it in one line

vibey's domain is a rule book with no I/O: the phase machine, effort ladder, engines, rotation
and no-loss gate as pure functions that keep any value they do not recognise and never act on it.
