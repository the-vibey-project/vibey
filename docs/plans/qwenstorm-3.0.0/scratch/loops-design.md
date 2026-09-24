# ADR-0046 lane design sheet (shared by every loops-* spec writer)

This sheet is the single source of names, signatures, files, dependencies and decisions for
the `loops-*` lane specs. A spec writer expands each lane below into a full spec in
`STORM/specs/loops-<slug>.md`, following
`STORM/SPEC-TEMPLATE.md` exactly (sections: Title, Why, Required behaviour, Where to change,
Acceptance criteria, Tests to write first (TDD), Checks the lane must run, Out of scope,
Depends on, and the closing `## Hard repository rules (always)` block that says only
`See STORM/SPEC-TEMPLATE.md.`). Read
`STORM/STORM-CONTEXT.md` first; it wins over this sheet. Read `STORM/EDITING-RULES.md`: every
spec must be implementable under it (edit_file only for files >100 lines; provenance line 1).

STORM = the storm root, `$VIBEY_STORM_HOME/qwenstorm-3.0.0` (on macOS by default `~/git/vibey-storm/qwenstorm-3.0.0`). Code to read = `STORM/integration`
(branch `storm/integration`, HEAD `d3b4a388`). NEVER read `/Users/adam/git/vibey`.
Cite `file:line` from STORM/integration and say "at integration `d3b4a388`". Where another
unmerged lane changes the same lines first, name the anchor by function/text, not only by line.

## Standing rules every loops spec restates (in "Out of scope" / checks)
- One source file (+ its interface) and one test file per lane, unless this sheet names more
  (then give exact snippets for each extra file). Name exact classes, signatures, messages.
- Write the whole check block (commands) out. For src/vibey:
  `uv run ruff check . && uv run ruff format --check .`, `uv run mypy --strict src/vibey`,
  `uv run lint-imports`, focused `uv run pytest -q -p no:cacheprovider <paths>`, then the
  coverage run + `coverage report --include='src/vibey/<layer>/*' --fail-under=100` for each
  touched layer. Tenants: their own suite + static gates (CLAUDE.md "Commands worth memorizing").
- ORM always (no new raw SQL, no `import asyncpg`, no `text()`); fakes for every new seam,
  registered in `tests/fakes/registry.py` (lane `fakes-registry`): application ports go in
  `REGISTRY`; infrastructure seams are appended to `DRIVER_SEAMS` and registered in `REGISTRY`.
  New loop fakes live in `tests/fakes/loops.py` (created by the first lane that needs it:
  `loops-routing-ports`; later lanes append). No `monkeypatch.setattr`, no `mock.patch`, no
  `MagicMock/AsyncMock`; `monkeypatch.setenv/delenv/chdir` are fine. Real-broker / real-Ollama
  tests are `@pytest.mark.integration` and skip without `VIBEY_TEST_AMQP_URL` /
  `VIBEY_TEST_OLLAMA_URL`.
- 8.g: the lane that creates a behaviour records its measurement (see "Measurement" below).
  7.c: ledger events named below are written by the lane that creates the decision.
- 8.h: nothing OS-specific without both Arch Linux and macOS paths (use Python, not `sed -i`,
  for scripted edits: GNU and BSD sed differ).
- Do not edit CHANGELOG.md, docs/, ADRs, CLAUDE.md, AGENTS.md, GEMINI.md, skill trees. Do not
  push, open PRs or change remotes. Commit locally with the Title as the Conventional Commit
  subject (add a `BREAKING CHANGE:` footer only where this sheet says so).
- Protected tests are never edited: `tests/domain/test_noloss*.py`, `tests/domain/test_briefing.py`,
  `tests/infrastructure/db/test_chaos.py`, `tests/system/test_delivery_stage_set.py`, `tests/live/**`.
- Every spec header line under Title: `ADR-0046 lane <Lnn> (slug `loops-<slug>`).`

## Decisions this sheet makes (ADR-0046 left them open) — cite them in the relevant spec
- D1 Seat host without a model runtime: a seat host STARTS and is ready as soon as it holds
  its exclusive consumer; it never exits because the runtime (Ollama) does not answer. It logs
  `seat_runtime_unreachable` once (warning, fields loop/seat/url), reports it in its startup
  line (`runtime=unreachable (<url>)`) and to probes/doctor, and runs requests anyway: the
  runner's own preflight/exit code (78, EX_CONFIG) carries the fault to the caller, who
  classifies it exactly as in subprocess mode (the loop never classifies capacity, ADR §2).
  So the default chart (ollama.enabled=false) passes `helm install --wait` (#377/#379).
- D2 CLI: `vibey loop-service --loop <sovereignloop|paidloop> [--role all|router|seat]
  [--seat NAME]... [--capacity N]`. `--role` defaults to `all` (router + seat hosts + control
  + probes + dead letters in one process: the laptop shape, ADR §3/§11). `--role router`:
  router + probe consumer + dead-letter replier; `--seat` repeatable = the loop's declared
  seats (overrides config). `--role seat`: exactly one `--seat` (else exit 2 "--role seat takes
  exactly one --seat"); runs one seat host + control consumer; `--capacity` overrides the
  seat's prefetch. Seats are passed as declared names (model names for sovereignloop, engine
  ids for paidloop); the CLI slugs them with `SeatSlug`. These are exactly the flags
  updates/377.md and 379.md reference.
- D3 Exit codes of `vibey loop-service`: 0 after a drain on SIGTERM; 2 (EXIT_USAGE) for bad
  flags or no AMQP URL (R17's `QueueBackendNotConfigured` message); 78 when the broker refuses
  an exclusive consumer (`LoopInstanceRefused`, message names "sub-doctrine 8.c runs a single
  instance per model"). #379 requires non-zero and not 124: 78 satisfies it.
- D4 `vibey loop submit --plan FILE --cwd DIR [--loop sovereignloop] [--engine ID]
  [--model NAME] [--run-id UUID] [--effort standard] [--isolation worktree] [--follow]
  [--timeout SECONDS]` always sends ONE pinned run (ADR §3 "pinned runs send one message");
  `--engine` defaults to the loop's default adapter (sovereignloop→`sovereignloop`,
  paidloop→`claudeloop`), `--model` is the `model_pin`. Prints the `RunResult` as one JSON
  line. Exit = the run's exit code; 1 when none; **75 on saturation** (carried from R27: no
  `RunAccepted` in time, or `REJECTED` "worktree busy…" / "not started before start_by"); 69
  (EX_UNAVAILABLE) on `UNROUTABLE`; 2 for an engine that is not an adapter of `--loop`.
- D5 Probes are consumed by the router process (roles all/router): ADR's single
  `vibey.runs.<loop>.probe` queue. Control is consumed by every process holding seat hosts
  (roles all/seat). Dead letters (intake + every declared seat) are answered by the router
  process.
- D6 In `--role seat` (cluster) a sovereign seat host always consumes its own seat (one model
  per host, no switching). Residency switching (`ResidentSeatScheduler`) runs only in
  `--role all`, where one process hosts several sovereign seats. Two sovereign models on one
  node share that node's Ollama, which evicts (V-OLL2).
- D7 Route replies: `RunRouted.status` is `routed | unroutable | dead_lettered`. The caller
  re-decides without the loop on `unroutable` (reason recorded as `ExclusionReason.UNROUTABLE`
  in any `PaidFallbackDeclared`); `dead_lettered` or no reply by `route_wait_seconds` raises
  `EngineQueueSaturated` (busy, never a paid fallback, ADR §5).
- D8 `ExclusionReason` adds `no_weight` (eligible but effective weight 0, e.g. a closed
  circuit whose failure EWMA reached 1.0) to the ADR's eight reasons; and an unrecognized
  circuit state reads as `circuit_open` with detail `unrecognized circuit state <text>`.
- D9 Measurement (8.g) has three sinks: (a) the router's route measurements travel in
  `RunRouted` and the caller writes them into the `LoopRouted` ledger event; (b) each run's
  queue wait, duration, status and exit code travel in `RunAccepted`/`RunResult` and the
  service adapter writes a new `LoopRunMeasured` ledger event; (c) everything the caller never
  sees (switches, probes, rejections, dead letters, forwards) goes to the loop's own append-only
  `measurements.jsonl` in its state dir (plus a structlog event `loop_measured`). New kind
  `LoopRunMeasured` beside the ADR's two.
- D10 Decision events (`PaidFallbackDeclared`, `LoopRouted`, `LoopRunMeasured`) are written
  through the `PhaseLedger` port (`application/interfaces/ledger.py:105-121`) with
  `Phase.BUILD` (production: `PostgresReviewLedger(resources.ledger, phase=Phase.BUILD)`,
  provenance TRUSTED, engine named in the payload), never through the engine-event path.
- D11 Config: the key naming seats is `models` for both loops (matching #377's chart values):
  sovereign seats are model names, paid seats are engine ids. `default_model` is sovereign-only
  and defaults to the 8.d designation `gpt-oss:20b`; the RAM-tier catalogue default (#383) is
  not wired here (an operator on a machine where it does not fit sets `default_model`).
- D12 `--engines` keeps #321's meaning (it narrows; declaration is the project's config:
  vibey.toml `[engines].enabled` or the CR list). `paidloop` is accepted as a spelling in
  `[engines].enabled` and `--engines` and expands to `claudeloop` (8.b default). The CR takes
  engine ids only (no `paidloop` in the CRD enum).
- D13 R20's two children are depended on as `rmq-r20-run-dir-extraction` (child 1 = #367
  itself, RunDirTailer/RunInbox/StopSummaryReader) and `rmq-r20-process-launcher` (child 2,
  EngineProcessLauncher + ProcessSpawnerInterface/ExecutableResolverInterface, `isolate_python_env`
  moved to `infrastructure/process/python_env.py`, fakes `tests/fakes/process.py`). updates/367.md
  names no slugs; these are the names used here.
- D14 Placement refinements of ADR §10 (same layer, sibling modules): `domain/run_codec.py`
  (the codec) and `domain/run_args_policy.py` beside `domain/run_protocol.py`;
  `domain/loop_events.py` (ledger payload + measurement values) beside `domain/ledger.py`;
  `domain/engine_names.py` (legacy spellings); `LoopCursorStore` inside `route_store.py`;
  `SeatBacklog` inside `resident_schedule.py`; new `measurement_log.py`, `process.py` in
  `infrastructure/loop_service/`; the `RoutedAdapterBinder` inside `adapter.py`.
- D15 VS Code gating: every vscode/vscodeloop lane and every opencode-retirement lane starts
  with a gate check (text below). The spike `loops-vscode-spike` is research for the operator
  or a large model (not the 20B): its deliverable is evidence appended to the ADR-0046 draft.

Gate text for gated lanes (paste verbatim, adjusting the marker):
> **Gate (ADR-0046 §8, CDD bounded divergence).** Before any edit run
> `grep -n "V-VS VERDICT: FEASIBLE" STORM/specs/ADR-two-loops.md docs/architecture/decisions/0046-*.md`.
> If nothing matches, change nothing and report `gated: V-VS verdict is not FEASIBLE`.
L38/L39 use the marker `V-VS CONFORMANCE: PASS` (the operator records it after running
`vibey doctor --conformance --engine vscode` live on Arch Linux and macOS).

## Measurement vocabulary (domain/loop_events.py, lane loops-ledger-kinds)
- `MeasurementSubject(StrEnum)`: ROUTE="route", FORWARD="forward", RUN="run", REJECT="reject",
  SWITCH="switch", PROBE="probe", DEAD_LETTER="dead_letter".
- `LoopMeasurement(loop_id: LoopId, subject: MeasurementSubject, at: datetime (aware),
  seat: str|None=None, engine_id: str|None=None, model: str|None=None,
  latency_ms: float|None=None, queue_depth: int|None=None, waited_seconds: float|None=None,
  outcome: str="")` with `to_record() -> dict[str, object]` (at → isoformat; None kept).
- Who records what: router ROUTE (latency=route ms, depth=seat depth, waited=oldest wait,
  outcome=route status) and FORWARD (outcome forwarded|unroutable); seat host RUN
  (latency=run ms, waited=queued seconds, outcome=`<status>:<exit_code>`) and REJECT
  (outcome=reason); scheduler SWITCH (latency=unload ms, outcome=`<from>-><to>`); probe
  consumer PROBE (latency, outcome ran|cached); dead-letter replier DEAD_LETTER
  (outcome=`deliveries=<n>`).

## Lanes, in queue order (slug — Lnn — files — summary — deps)

### Domain (pure; `tests/domain/test_domain_purity.py` walks them)

1. `loops-engine-id-sovereignloop` — L06 — `src/vibey/domain/engine.py`,
   `src/vibey/domain/stored_value.py` (+ interface docstring), `deploy/helm/vibey/templates/crd-vibeyproject.yaml`
   (enum line 78), `tests/meta/test_crd_engine_enum.py`, `src/vibey/domain/ledger_query.py`
   (ActorResolver.resolve, :106-122); test `tests/domain/test_engine_aliases.py`.
   - `StoredValueParser.__init__(self, members, unrecognized, *, aliases: Mapping[str, M] | None = None)`;
     `known(raw)` returns the member, else `self._aliases.get(raw)`; `parse(raw)` NEVER resolves
     aliases (stored text preserved: a stored `qwenloop` parses as `UnrecognizedEngineId("qwenloop")`).
   - `EngineId`: add `SOVEREIGNLOOP = "sovereignloop"` where `QWENLOOP` is, then
     `QWENLOOP = "sovereignloop"` right after it (a Python enum alias; comment: "the rename
     wave's alias (ADR-0046 §7); lane L09 removes it"). Add
     `@classmethod _missing_(cls, value: object) -> "EngineId | None"` returning
     `ENGINE_ID_ALIASES.get(value)` for a str. After the class:
     `ENGINE_ID_ALIASES: Final[Mapping[str, EngineId]] = MappingProxyType({"qwenloop": EngineId.SOVEREIGNLOOP})`;
     `ENGINE_ID_PARSER = StoredValueParser(EngineId, UnrecognizedEngineId, aliases=ENGINE_ID_ALIASES)`.
     `UnrecognizedEngineId.members` is unchanged in code (values only), so "qwenloop" is NOT a member.
   - CRD enum: `[claudeloop, codexloop, cursorloop, agyloop, opencode, sovereignloop, qwenloop, claudeloop-local]`.
     Binding test asserts `sorted(declared) == sorted({*(e.value for e in EngineId), *ENGINE_ID_ALIASES})`.
   - `ActorResolver.resolve`: after the member loop, `for legacy in ENGINE_ID_ALIASES: if needle == legacy: return Actor(ActorScope.ENGINE, legacy)`
     (legacy events keep their stored text; searching `qwenloop` still finds them).
   - Stored-text expectations that change (update ONLY these, and list them in the commit body):
     `tests/cli/test_sovereign_provider_options.py` `recorded["engine_id"] == "qwenloop"` → `"sovereignloop"`;
     `tests/cli/test_operational_commands.py`: doctor output `"qwenloop" in res.output` →
     `"sovereignloop"`, `"no recorded conformance for qwenloop"` → `sovereignloop`, the
     `check()` tuple `("qwenloop",)` → `("sovereignloop",)`. Stop rule: any other failing test
     that is not a pure expected-text replacement → stop and report.
   - `known("qwenloop")` is `EngineId.SOVEREIGNLOOP` (so an in-flight verify job's
     `implementer_engine_id: "qwenloop"` still excludes its successor; `tests/application/test_engine_selection.py`
     keeps passing unedited).
   - deps: `engines-pool`.

2. `loops-domain-loop-id` — L01 — `src/vibey/domain/loop.py`,
   `src/vibey/domain/interfaces/loop_interface.py`; test `tests/domain/test_loop.py`.
   - `class LoopId(StrEnum)`: SOVEREIGNLOOP="sovereignloop", PAIDLOOP="paidloop".
   - `UnrecognizedLoopId(UnrecognizedValue)` (members = LoopId values); `type StoredLoopId`;
     `LOOP_ID_PARSER: Final = StoredValueParser(LoopId, UnrecognizedLoopId)`.
   - `LOOP_PREFERENCE: tuple[LoopId, ...] = (LoopId.SOVEREIGNLOOP, LoopId.PAIDLOOP)`.
   - `LOOP_OF_TIER: Mapping[EngineTier, LoopId]` = MappingProxyType({LOCAL: SOVEREIGNLOOP, PAID: PAIDLOOP}).
   - `DEFAULT_ADAPTER: Mapping[LoopId, EngineId]` = {SOVEREIGNLOOP: EngineId.SOVEREIGNLOOP, PAIDLOOP: EngineId.CLAUDELOOP} (8.b).
   - `class LoopMembership` (interface `LoopMembershipInterface`): `loop_of(descriptor: EngineDescriptor) -> LoopId`;
     `split(candidates: Sequence[Candidate]) -> Mapping[LoopId, tuple[Candidate, ...]]` (by `Candidate.tier`, every LoopId key present, order kept);
     `default_adapter(loop_id: LoopId) -> EngineId`.
   - deps: `loops-engine-id-sovereignloop`.

3. `loops-residency-policy` — L02a — `src/vibey/domain/residency.py`,
   `src/vibey/domain/interfaces/residency_interface.py`; test `tests/domain/test_residency_policy.py`.
   - `RESERVED_SEATS = frozenset({"probe", "dead"})`.
   - `class SeatSlug`: `of(name: str) -> str` (lower-case; every char outside `[a-z0-9-]` → `-`;
     empty result or reserved → `ValueError` naming the name); `of_paid(engine_id: str, model: str | None = None) -> str`
     (`engine_id` alone, or `f"{engine_id}.{self.of(model)}"`); `unique(names: Sequence[str]) -> Mapping[str, str]`
     (slug → name, declared order; a collision raises `ValueError("seats <a> and <b> share the slug <s>")`).
     `SeatSlug().of("gpt-oss:20b") == "gpt-oss-20b"`.
   - `@dataclass(frozen=True, slots=True) class ModelDeclaration: name: str; context_window: int` (≥1).
   - `@dataclass(frozen=True, slots=True) class ModelChoice: model: str; switched: bool; reason: str`
     (reason ∈ `"resident"`, `"default"`, `"first declared"`).
   - `UNROUTABLE_NO_MODEL = "no local model can carry this job"`.
   - `class ResidencyPolicy.choose(*, resident: str | None, default: str | None, declared: Sequence[ModelDeclaration], model_pin: str | None, min_context: int | None) -> ModelChoice | None`:
     can_carry(m) = m declared and (pin is None or m.name == pin) and (min_context is None or m.context_window >= min_context).
     Order: resident (if declared and can carry) → default → first declared that can. `switched = resident is not None and chosen != resident`. None → unroutable.
   - deps: none.

4. `loops-residency-schedule` — L02b — `src/vibey/domain/residency.py` (append),
   interface append; test `tests/domain/test_residency_schedule.py`.
   - `@dataclass(frozen=True, slots=True) class SeatLoad: seat: str; depth: int; oldest_wait_seconds: float | None`.
   - `class ResidencySchedule.next_seat(*, resident: str, resident_busy: bool, runs_since_switch: int, loads: Sequence[SeatLoad], max_wait_seconds: float, min_hold_runs: int) -> str | None`:
     busy → None. others = loads with seat != resident and depth > 0 (None if empty).
     resident depth == 0 → the other with the largest oldest_wait (None counts 0; ties: input order).
     Else if runs_since_switch >= min_hold_runs and some other has oldest_wait >= max_wait → the largest such. Else None.
     This is ADR §4's starvation bound.
   - deps: `loops-residency-policy`.

5. `loops-run-protocol-messages` — L04a — `src/vibey/domain/run_protocol.py`,
   `src/vibey/domain/interfaces/run_protocol_interface.py`; test `tests/domain/test_run_protocol.py`.
   - Schema constants: `SCHEMA_ROUTE="vibey.run.route/1"`, `SCHEMA_ROUTED="vibey.run.routed/1"`,
     `SCHEMA_REQUEST="vibey.run.request/1"`, `SCHEMA_ACCEPTED="vibey.run.accepted/1"`,
     `SCHEMA_PROGRESS="vibey.run.progress/1"`, `SCHEMA_RESULT="vibey.run.result/1"`, `SCHEMA_CONTROL="vibey.run.control/1"`.
   - Enums: `RunPurpose` RUN="run", PROBE="probe"; `RunStatus` EXITED, SUPERSEDED, ABANDONED,
     REJECTED, DEAD_LETTERED, DEADLINE_EXCEEDED, UNROUTABLE (values = lower-case names);
     `RouteStatus` ROUTED="routed", UNROUTABLE="unroutable", DEAD_LETTERED="dead_lettered";
     `RunControlCommand` STOP="stop", WIND_DOWN="wind_down", PROMPT_NOW="prompt-now",
     PROMPT_AT_BREAK="prompt-at-break", SUPERSEDE="supersede".
   - Frozen slotted dataclasses, validated in `__post_init__` (ValueError naming the field; every datetime aware):
     `RunSupersede(key: str (non-empty), attempt: int (≥0))`;
     `RouteCandidate(engine_id: str (non-empty), weight: int (≥0))`;
     `RouteRequest(route_id: UUID, loop_id: LoopId, project_id: UUID | None, candidates: tuple[RouteCandidate, ...] (unique engine ids), pin: str | None, model_pin: str | None, min_context: int | None (≥1), requested_at: datetime, caller: str (non-empty))`;
     `RunRouted(route_id: UUID, loop_id: LoopId, status: RouteStatus, engine_id: str | None, seat: str | None, model: str | None, switched: bool, reason: str, routed_at: datetime, route_ms: float (≥0), seat_depth: int | None, seat_oldest_wait_seconds: float | None)`
       — `status is ROUTED` ⇔ engine_id and seat both set;
     `RunRequest(run_id: UUID, loop_id: LoopId, engine_id: str, route_id: UUID | None, model_pin: str | None, purpose: RunPurpose, args: tuple[str, ...], cwd: str (absolute: starts with "/"), run_dir: str | None, supersedes: RunSupersede | None, deadline_seconds: int (≥1), start_by: datetime, capture_output: bool, requested_at: datetime, caller: str)`;
     `RunAccepted(run_id: UUID, loop_id: LoopId, engine_id: str, seat: str, model: str | None, instance: str, pid: int | None, started_at: datetime, queued_seconds: float (≥0))`;
     `RunProgress(run_id: UUID, seq: int (≥1), line: str)`;
     `RunResult(run_id: UUID, status: RunStatus, exit_code: int | None, meta_status: str | None, started_at: datetime | None, finished_at: datetime, detail: str, stdout: str | None, stderr: str | None, cached_at: datetime | None)`
       — NO completion, success or capacity field (non-negotiable 3);
     `RunControl(run_id: UUID | None, command: RunControlCommand, text: str | None, supersedes: RunSupersede | None)`
       — SUPERSEDE ⇔ supersedes set and run_id None; other commands need run_id; prompts need text.
     `type RunMessage = RouteRequest | RunRouted | RunRequest | RunAccepted | RunProgress | RunResult | RunControl`.
   - `class RunQueueNames(prefix: str = "vibey")` (interface `RunQueueNamesInterface`):
     `runs_exchange()` `f"{p}.runs"`; `dead_exchange()` `f"{p}.runs.dlx"`; `control_exchange()` `f"{p}.runs.control"`;
     `intake_queue(loop)` `f"{p}.runs.{loop}"`; `intake_key(loop)` `str(loop)`;
     `seat_queue(loop, seat)` `f"{p}.runs.{loop}.{seat}"`; `seat_key(loop, seat)` `f"{loop}.{seat}"`;
     `probe_queue(loop)` `f"{p}.runs.{loop}.probe"`; `probe_key(loop)` `f"{loop}.probe"`;
     `intake_dead_queue(loop)` `f"{p}.runs.{loop}.dead"`; `seat_dead_queue(loop, seat)` `f"{p}.runs.{loop}.{seat}.dead"`;
     `control_keys(loop)` `(str(loop), "all")`;
     `queue_arguments(*, dead_key: str, delivery_limit: int, consumer_timeout_seconds: int) -> dict[str, object]` =
     `{"x-queue-type":"quorum","x-delivery-limit":delivery_limit,"x-dead-letter-exchange":dead_exchange(),"x-dead-letter-routing-key":dead_key,"x-dead-letter-strategy":"at-least-once","x-overflow":"reject-publish","x-consumer-timeout":consumer_timeout_seconds*1000}`.
     `seat` must match `^[a-z0-9-]+(\.[a-z0-9-]+)?$` and not be reserved (ValueError).
   - deps: `loops-domain-loop-id`.

6. `loops-run-codec` — L04b — `src/vibey/domain/run_codec.py`,
   `src/vibey/domain/interfaces/run_codec_interface.py`, `src/vibey/domain/errors.py`
   (add `class MalformedRunMessage(VibeyError)`); test `tests/domain/test_run_codec.py`.
   - `RunProtocolCodec`: `encode(message: RunMessage) -> dict[str, object]` (adds `"schema"`;
     UUID→str; datetime→isoformat; enums→value; tuples→lists; nested dataclasses→dicts);
     `decode(raw: Mapping[str, object]) -> RunMessage` (dispatch on `schema`; EXACT key set;
     wrong type, naive datetime, bad UUID, unknown schema, missing key, extra key → `MalformedRunMessage`);
     `to_bytes(message) -> bytes` (`json.dumps(..., sort_keys=True, separators=(",", ":")).encode()`);
     `from_bytes(body: bytes) -> RunMessage` (bad JSON/UTF-8 → `MalformedRunMessage`).
     `FORBIDDEN_KEYS: Final = frozenset({"resets_at","capacity","capacity_state","credits","complete","success"})`.
   - Hypothesis round-trip per message type; property: no encoded message contains a forbidden
     key; decode refuses each forbidden key as an extra key. Copy the R19 test list (specs/rmq-r19-run-protocol.md).
   - deps: `loops-run-protocol-messages`.

7. `loops-run-args-policy` — L04c — `src/vibey/domain/run_args_policy.py`,
   `src/vibey/domain/interfaces/run_args_policy_interface.py`; test `tests/domain/test_run_args_policy.py`.
   - `RunArgsPolicy.reason(purpose: RunPurpose, args: tuple[str, ...]) -> str | None` exactly as
     R19 behaviour 5 (RUN: args[0] ∈ {run, resume}; PROBE: exactly ("--version",) or ("run","--help")
     or begins with "doctor"; empty args or any "\x00" refused). Pure.
   - deps: `loops-run-protocol-messages`.

8. `loops-seat-chooser` — L03 — `src/vibey/domain/seat_choice.py`,
   `src/vibey/domain/interfaces/seat_choice_interface.py`; test `tests/domain/test_seat_choice.py`.
   - `SeatCursor(engine_id: str, current: int, order: int)`; `SeatChoice(engine_id: str, seat: str, cursors: tuple[SeatCursor, ...])`;
     `SeatDecision(choice: SeatChoice | None, reason: str)`.
   - `class SeatChooser(slug: SeatSlugInterface | None = None)`:
     `choose(*, loop_id: LoopId, candidates: Sequence[RouteCandidate], cursors: Sequence[SeatCursor], model: str | None, pin: str | None, default_adapter: str) -> SeatDecision`.
     Pinned: pin in candidates, or candidates empty → choice for pin, cursors unchanged;
     otherwise `reason = f"pinned adapter {pin} is not a candidate of {loop_id}"`.
     Unpinned: candidates with weight>0 whose id `ENGINE_ID_PARSER.known(...)` is not None;
     none → `reason = f"no adapter of {loop_id} has positive weight"`. SWRR reuses
     `domain/rotation.py::select` (`:161-185`) with `Candidate(engine_id=known id, base_weight=weight, current, order, health_factor=1.0, fidelity_factor=1.0, cost_factor=1.0, affinity_factor=1.0)`.
     Cursor orders: existing kept; with no cursors the `default_adapter` gets order 0 and the rest
     follow candidate order (ADR §1: claudeloop wins ties in paidloop); new engines append.
     Seat: sovereign → `SeatSlug().of(model)` (model required, else ValueError); paid → `SeatSlug().of_paid(engine_id)`.
   - deps: `loops-residency-policy`, `loops-run-protocol-messages`.

9. `loops-ledger-kinds` — L05 — `src/vibey/domain/ledger.py` (three `EventKind` members after
   `DELIVERY_ESTIMATE_RECORDED`), `src/vibey/domain/loop_events.py` (new) +
   `src/vibey/domain/interfaces/loop_events_interface.py`, `src/vibey/domain/publication_policy.py`
   (DEFAULT_ALLOWLIST entries); test `tests/domain/test_loop_events.py`.
   - `EventKind.PAID_FALLBACK_DECLARED = "PaidFallbackDeclared"`, `LOOP_ROUTED = "LoopRouted"`, `LOOP_RUN_MEASURED = "LoopRunMeasured"` (event.kind is text; no migration).
   - `ExclusionReason(StrEnum)`: NO_HEALTH_ROW="no_health_row", NOT_INSTALLED="not_installed",
     CONFORMANCE_FAILED="conformance_failed", AUTHENTICATION_STALE="authentication_stale",
     CIRCUIT_OPEN="circuit_open", EXCLUDED_BY_JOB="excluded_by_job", MISSING_CAPABILITY="missing_capability",
     NO_WEIGHT="no_weight" (D8), UNROUTABLE="unroutable".
   - `AdapterExclusion(engine_id: str, reason: ExclusionReason, capacity_state: str | None = None, detail: str = "")`
     (capacity_state only allowed with CIRCUIT_OPEN).
   - `PaidFallbackDeclaration(engine_id: str, invocation: str ("subprocess"|"service"), sovereign: tuple[AdapterExclusion, ...])`
     → `to_payload()` = `{"loop_id":"paidloop","engine_id":…,"invocation":…,"sovereign_adapters":[{"engine_id","reason","capacity_state","detail"}…],"rule":"sub-doctrine 8.a"}`.
   - `LoopRoutedRecord(route_id: UUID, loop_id: LoopId, engine_id: str, seat: str, model: str | None, switched: bool, reason: str, route_ms: float, seat_depth: int | None, seat_oldest_wait_seconds: float | None)` → `to_payload()` (route_id as str).
   - `LoopRunMeasurement(run_id: UUID, loop_id: LoopId, engine_id: str, seat: str | None, model: str | None, status: str, exit_code: int | None, accepted: bool, queued_seconds: float | None, run_seconds: float | None)` → `to_payload()`.
   - `MeasurementSubject`, `LoopMeasurement` as in "Measurement vocabulary".
   - Property tests: no payload contains `resets_at`, `capacity`, `credits`, `complete`, `success`,
     or any datetime value (Hypothesis over exclusions incl. capacity_state "CreditsExhausted").
   - Publication allowlist: PaidFallbackDeclared {loop_id, engine_id, invocation, sovereign_adapters, rule};
     LoopRouted {loop_id, engine_id, seat, model, switched, reason, route_ms, seat_depth, seat_oldest_wait_seconds};
     LoopRunMeasured {loop_id, engine_id, seat, model, status, exit_code, queued_seconds, run_seconds}.
   - deps: `loops-domain-loop-id`.

### Rename wave (ADR §7, Migration table) and configuration

10. `loops-config-engine-names` — L08a — `src/vibey/domain/engine_names.py` (+ interface
    `domain/interfaces/engine_names_interface.py`), `src/vibey/domain/config.py`; test `tests/domain/test_engine_names.py`.
    - `LegacySpelling(where: str, legacy: str, current: str)` frozen; `EngineNameResolver`:
      `resolve(name: str, *, where: str) -> tuple[str, LegacySpelling | None]` (alias key →
      canonical value + record; else unchanged, None); `resolve_all(names, *, where) -> tuple[tuple[str, ...], tuple[LegacySpelling, ...]]` (order kept, duplicates dropped).
    - config.py: `DEFAULT_ENGINES = ("sovereignloop",)`; KNOWN_ENGINES replaces "qwenloop" by
      "sovereignloop"; `LOCAL_ENGINE_FEATURES` key `"sovereignloop": "sovereignloop"`;
      `FeaturesConfig.sovereignloop: bool = False` replaces `qwenloop` (legacy `[features] qwenloop`
      read when `sovereignloop` is absent, recorded); `_parse_engines` resolves `enabled` and
      `weights` keys, force-appends "sovereignloop"; `parse_config` resolves every `[phases.*].engines`;
      `VibeyConfig.legacy_spellings: tuple[LegacySpelling, ...] = ()` collects every record
      (where = dotted key, e.g. `engines.enabled`, `features.qwenloop`, `phases.build.engines`).
      Update the literal `"qwenloop"` checks in `parse_config` (`:680` region) to "sovereignloop".
    - Existing tests that asserted `"qwenloop"` in a parsed default pool now see
      "sovereignloop": update those expectations only (list them).
    - deps: `loops-engine-id-sovereignloop`, `engines-pool`.

11. `loops-config-sovereignloop-table` — L08b — `src/vibey/domain/config.py`; test `tests/domain/test_sovereignloop_table.py`.
    - `QwenloopConfig` → `SovereignloopConfig` (same fields); `VibeyConfig.sovereignloop`;
      `_parse_sovereignloop` reads `[sovereignloop]`, else `[qwenloop]` (+LegacySpelling
      where="[qwenloop]"); both present → `ConfigError("sovereignloop", "both [sovereignloop] and its legacy spelling [qwenloop] are set; keep [sovereignloop]")`.
      Error paths name `sovereignloop.<key>` (or `qwenloop.<key>` when read from the legacy table).
    - deps: `loops-config-engine-names`.

12. `loops-tenant-rename` — L18a — `git mv src/vibey_runners/qwen src/vibey_runners/sovereign`,
    `git mv …/src/qwenloop …/src/sovereignloop`; a checked Python script (given in full in
    the spec) rewrites ONLY `from qwenloop`/`import qwenloop`/`"qwenloop.` module paths/`--cov=qwenloop`
    in the tenant's .py/.toml files; tenant pyproject (name `sovereignloop`, script
    `sovereignloop = "sovereignloop.cli.app:main"` plus `qwenloop = "sovereignloop.cli.app:legacy_main"`);
    `sovereignloop/cli/app.py`: `typer.Typer(name="sovereignloop")` and
    `def legacy_main() -> None` printing to stderr `qwenloop is a legacy name for sovereignloop (ADR-0046); it works through 3.x` then calling `main()`;
    root `pyproject.toml` (scripts :69-76 add `sovereignloop`, keep `qwenloop` → legacy_main;
    packages :200-207; sources :227-232); `deploy/docker/Dockerfile:142`; `.github/workflows/ci.yml`
    tenant rows :531-546 (package `sovereignloop`, dir, static paths) and the console-script
    contract list :827 (add `sovereignloop`); `src/vibey_runners/common/pyproject.toml`
    forbidden list (`qwenloop` → `sovereignloop`); `uv lock`. Env names, config/cache/run-dir
    literals, and the done marker are NOT touched here (next lanes).
    Test: `src/vibey_runners/sovereign/tests/test_legacy_entry_point.py`.
    Verification: `grep -rn "import qwenloop\|from qwenloop" src tests` empty; tenant suite +
    static gates on the new paths; `uv lock --check`; `tests/meta` (tools matrix) passes.
    - deps: `loops-engine-id-sovereignloop`, `fakes-tenant-qwen-2`, `default-model-p3`.

13. `loops-tenant-legacy-env` — L18c — `src/vibey_runners/sovereign/src/sovereignloop/infrastructure/settings.py`;
    test `src/vibey_runners/sovereign/tests/test_settings_legacy.py`.
    - `ENV_CONFIG="SOVEREIGNLOOP_CONFIG"`, `ENV_BASE_URL`, `ENV_MODEL`, `ENV_API_KEY`, and the
      network variable (find `QWENLOOP_NETWORK` in the tenant) get `SOVEREIGNLOOP_*` names;
      `LEGACY_ENV = {new: old}` read when the new one is unset/empty. Default config path
      `user_config_path("sovereignloop")/config.toml`, falling back to
      `user_config_path("qwenloop")/config.toml` when the new file is absent and the old exists.
      Never moves files.
    - deps: `loops-tenant-rename`.

14. `loops-tenant-legacy-paths` — L18d — tenant `infrastructure/model_cache.py` (:25),
    `infrastructure/inference.py` (:68), `infrastructure/run_store.py` (:11), `cli/app.py`
    (`.qwenloop` literals at :566, :575, :593 and `user_cache_path("qwenloop")` at :516),
    `domain/model.py` (done marker); vibey `src/vibey/infrastructure/engines/descriptors.py`
    (QWENLOOP descriptor: `binary="sovereignloop"`, `state_dir=".sovereignloop"`,
    `done_marker="SOVEREIGNLOOP_TASK_FULLY_COMPLETE"`); test `src/vibey_runners/sovereign/tests/test_legacy_paths.py`.
    - Cache root `user_cache_path("sovereignloop")`; when absent and `user_cache_path("qwenloop")`
      exists, use the legacy root in place (NEVER copy/move 13–16 GB; ADR-0015 #5).
    - Runs written to `.sovereignloop/runs/<id>`; resume/inbox/status read `.qwenloop/runs/<id>`
      when the new one is absent.
    - Done marker `SOVEREIGNLOOP_TASK_FULLY_COMPLETE`; the completion check accepts either marker.
    - deps: `loops-tenant-legacy-env`.

15. `loops-vibey-local-engine-names` — L18e — `src/vibey/infrastructure/engines/local_engines.py`,
    `src/vibey/infrastructure/provision/agent_surface.py` (:60 add `".sovereignloop/"`); test
    `tests/infrastructure/engines/test_local_engine_names.py`.
    - `SOVEREIGNLOOP_BASE_URL_ENV`/`SOVEREIGNLOOP_MODEL_ENV`; overlay writes the new names; it
      derives nothing for a key when either the new or the legacy (`QWENLOOP_*`) name is set.
      Feature switch env for sovereignloop is `VIBEY_FEATURE_SOVEREIGNLOOP`; the legacy
      `VIBEY_FEATURE_QWENLOOP` is read when the new one is unset, and #321's
      "cannot be switched off" warning names the variable actually read. Keep exported legacy
      constant names `QWENLOOP_BASE_URL_ENV`/`QWENLOOP_MODEL_ENV` (values unchanged) in `__all__`.
    - deps: `loops-tenant-legacy-paths`, `loops-config-engine-names`.

16. `loops-cli-provider-name` — L18f — `src/vibey/cli/main.py` (`_PROVIDERS` :365, `_resolve_provider`
    :381-389, the two `provider == "qwenloop"` branches :441 and :1593, `_OLLAMA_MODEL_HELP` :360),
    `src/vibey/infrastructure/cluster_preflight.py` (PROVIDER_ENGINES :53-58 add
    `"sovereignloop": None`, keep `"qwenloop": None`); test `tests/cli/test_provider_name.py`.
    - `_PROVIDERS = ("scripted", "claudeloop", "sovereignloop", "opencode")`; default
      `"sovereignloop"`; `--provider qwenloop` is accepted, normalized to `sovereignloop`, and
      prints to stderr `--provider qwenloop is a legacy spelling; use --provider sovereignloop (accepted through 3.x)`.
      Update the two `_UNKNOWN_PROVIDER` message assertions in existing tests.
    - deps: `loops-engine-id-sovereignloop`.

17. `loops-chart-sovereignloop-names` — L18g — `deploy/helm/vibey/values.yaml`
    (`ollama.qwenloopFeature` → `ollama.sovereignloopFeature`, legacy key honoured when the new
    one is unset), `templates/worker.yaml` (:105-114 env → `SOVEREIGNLOOP_BASE_URL`,
    `SOVEREIGNLOOP_MODEL`, `VIBEY_FEATURE_SOVEREIGNLOOP`), `templates/loop-services.yaml`
    (same names, from #377), `deploy/helm/golden/render.sh` (profile `ollama-gpu-qwenloop` →
    `ollama-gpu-sovereignloop`, file renamed), regenerated goldens; test
    `tests/infrastructure/test_chart_sovereignloop_names.py`.
    - deps: `loops-vibey-local-engine-names`, `rmq-r30-chart-loop-services`.

18. `loops-config-loop-services` — L10 ("ADR-0046's config lane" in updates/348, 377, 380, 381)
    — `src/vibey/domain/loop_services_config.py` (new) +
    `src/vibey/domain/interfaces/loop_services_config_interface.py`, `src/vibey/domain/config.py`
    (VibeyConfig field + one parse line), `src/vibey/infrastructure/config_loader.py`
    (`_SURFACE_ENV_VARS` rows); test `tests/domain/test_loop_services_config.py`.
    - `[loop_services]`: `root: str = "/"` (absolute), `state_dir: str = ""` ("" = resolved at
      composition, see lane `loops-bootstrap-loop-service`; absolute when set).
      Env rows (after R01's bus/queue/engines rows): `("loop_services", "root", "VIBEY_LOOP_SERVICES_ROOT", str)`,
      `("loop_services", "state_dir", "VIBEY_LOOP_SERVICES_STATE_DIR", str)`.
    - `[loop_services.sovereignloop]` and `[loop_services.paidloop]` → `LoopConfig`:
      | key | default | constraint |
      |---|---|---|
      | models | () | sovereign: model names, slugs unique & not reserved (SeatSlug); paid: engine ids of PAID descriptors |
      | default_model | "gpt-oss:20b" | sovereign only; must be in models when models non-empty; key on paidloop → ConfigError("loop_services.paidloop.default_model", "paidloop's default adapter is claudeloop (sub-doctrine 8.b); name its seats with models") |
      | model_context | {} | sovereign; name→int ≥1; built-in default {"gpt-oss:20b": 131072}, else 32768 |
      | capacity | 1 | 1–64 (seat prefetch; 8.c: throughput is capacity, never a copy) |
      | router_prefetch | 16 | 1–1000 |
      | delivery_limit | 3 | 1–1000 |
      | consumer_timeout_seconds | 21600 | ≥60 |
      | residency_max_wait_seconds | 900 | ≥0 |
      | residency_min_hold_runs | 1 | ≥0 |
      | unload_on_switch | true | bool |
      | schedule_interval_seconds | 5.0 | >0 |
      | route_wait_seconds | 30 | ≥1 |
      | run_queue_wait_seconds | 3600 | ≥1 |
      | run_deadline_seconds | 21600 | ≥1 |
      | supersede_grace_seconds | 30 | ≥1 |
      | stale_lock_seconds | 300 | ≥0 |
      | probe_timeout_seconds | 10 | ≥1 |
      | doctor_probe_timeout_seconds | 120 | ≥1 |
      | publish_progress | true | bool |
      `.seats.<name>` tables → `SeatConfig(prefetch: int | None = None)` (1–64); names must be
      declared seats of that loop. Any other key under `[loop_services]` besides root, state_dir
      and the two loops → `ConfigError("loop_services", "loop_services has exactly two loops (8.c): sovereignloop and paidloop")`.
      A `replicas` key anywhere → `ConfigError(<dotted key>, "replicas is not a key: sub-doctrine 8.c runs a single instance per model; raise capacity instead")`.
    - Methods: `LoopServicesConfig.for_loop(loop_id: LoopId) -> LoopConfig`;
      `LoopConfig.effective_models(loop_id) -> tuple[str, ...]` (sovereign: models or (default_model,));
      `LoopConfig.prefetch_for(seat_name: str) -> int` (seats[name].prefetch or capacity);
      `LoopConfig.declarations() -> tuple[ModelDeclaration, ...]` (sovereign).
    - Parser class `LoopServicesConfigParser.parse(data: Mapping[str, Any]) -> LoopServicesConfig`
      (a class, not a module function); `parse_config` calls it; `VibeyConfig.loop_services`.
    - deps: `rmq-r01-queue-config`, `loops-residency-policy`, `loops-domain-loop-id`.

19. `loops-doctor-legacy-spellings` — L07 — `src/vibey/infrastructure/legacy_spellings.py`
    (+ `infrastructure/interfaces/legacy_spellings_interface.py`), `src/vibey/cli/main.py`
    (doctor, one block after the PostgreSQL line); test `tests/infrastructure/test_legacy_spellings.py`.
    - `LegacySpellingScanner(*, environ, user_config_dir: Path, user_cache_dir: Path, cwd: Path)`.
      `scan(config: VibeyConfig | None) -> tuple[LegacySpelling, ...]`: the config's
      `legacy_spellings`; each legacy env var set (`QWENLOOP_BASE_URL`, `_MODEL`, `_API_KEY`,
      `_CONFIG`, `_NETWORK`, `VIBEY_FEATURE_QWENLOOP`, `VIBEY_FEATURE_CLAUDELOOP_LOCAL`);
      legacy paths present (`<config>/qwenloop/config.toml`, `<cache>/qwenloop`, `<cwd>/.qwenloop/runs`).
    - Doctor prints, per record: `legacy spelling in use: <where> <legacy> -> <current> (works through 3.x; rename it)`.
      Informational: exit code unchanged. `vibey doctor` evidence gates every removal (Migration table).
    - deps: `loops-config-sovereignloop-table`, `loops-tenant-legacy-paths`,
      `loops-vibey-local-engine-names`, `loops-claudeloop-local-paid`, `installer-doctor`.

20. `loops-drop-qwenloop-alias` — L09 — scripted (Python, given in full): replace
    `EngineId.QWENLOOP` → `EngineId.SOVEREIGNLOOP` in `src/vibey` and `tests` (not the tenant;
    not `tests/live/**`, which must already not reference it — stop if it does); rename the
    descriptor constant `QWENLOOP` → `SOVEREIGNLOOP` in `infrastructure/engines/descriptors.py`
    and its importers; delete the alias line from `EngineId`. Keep `_missing_`,
    `ENGINE_ID_ALIASES` and every legacy read (forever). Test
    `tests/domain/test_engine_alias_removed.py` (`EngineId.__members__` has no QWENLOOP;
    `EngineId("qwenloop") is EngineId.SOVEREIGNLOOP`; `ENGINE_ID_PARSER.parse("qwenloop")` is
    `UnrecognizedEngineId("qwenloop")`). Verification: `grep -rn "EngineId.QWENLOOP" src tests` empty.
    - deps: `loops-doctor-legacy-spellings`, `loops-chart-sovereignloop-names`, `loops-cli-provider-name`.

### Application (outer layer, both invocation modes)

21. `loops-weighted-candidates` — L11 — `src/vibey/application/engine_selector.py`,
    `src/vibey/application/dto.py` (`WeightedCandidates`), `src/vibey/application/interfaces/engines.py`
    (EngineSelectorInterface gains two methods); test `tests/application/test_weighted_candidates.py`.
    - `@dataclass(frozen=True, slots=True) class WeightedCandidates: project_id: UUID; candidates: tuple[Candidate, ...]; exclusions: tuple[AdapterExclusion, ...]`.
    - `EngineSelector.weighted_candidates(project_id, requirement, allow_list=None, cost_aware=False, affinity_engine=None) -> WeightedCandidates`:
      today's `select_engine` body `:115-206` moved verbatim (including cursor initialization),
      never raising NoEligibleEngine; plus an exclusion for each pool engine
      (`allow_list` member, or every record when allow_list is None) that is not a candidate,
      checked in `eligible()`'s order (`domain/rotation.py:67-86`): no record → NO_HEALTH_ROW;
      not installed → NOT_INSTALLED; not conformance_ok → CONFORMANCE_FAILED; auth stale →
      AUTHENTICATION_STALE; circuit OPEN (after the half-open time check) → CIRCUIT_OPEN with
      `capacity_state=record.capacity_state`; unknown circuit → CIRCUIT_OPEN detail
      `unrecognized circuit state <text>` (D8); in requirement.excluded → EXCLUDED_BY_JOB;
      missing capability → MISSING_CAPABILITY. Records for engines this worker has no descriptor
      for are skipped (as today).
    - `EngineSelector.select_from(weighted: WeightedCandidates) -> tuple[EngineId, Selection]`:
      empty candidates → `NoEligibleEngine(f"No engines meet requirements for project {project_id}")`
      (today's message, `:160`); else `select(preferred_tier(...))` and `update_many` (`:208-226`).
    - `select_engine(...)` = `select_from(await weighted_candidates(...))`; byte-identical behaviour:
      `tests/application/test_engine_selector.py` passes unedited.
    - deps: `loops-ledger-kinds`, `fakes-engines`, `orm-engine-health`, `orm-rotation-cursor`.

22. `loops-loop-selector` — L12 — `src/vibey/application/loop_selector.py`,
    `src/vibey/application/interfaces/loop_routing.py` (NEW; `LoopSelectorInterface`),
    `src/vibey/application/dto.py` (`LoopDecision`); test `tests/application/test_loop_selector.py`.
    - `LoopDecision(loop_id: LoopId, candidates: tuple[Candidate, ...], sovereign_exclusions: tuple[AdapterExclusion, ...])`.
    - `LoopSelector(*, descriptors: Mapping[EngineId, EngineDescriptor], membership: LoopMembershipInterface | None = None)`;
      `choose(weighted: WeightedCandidates, *, excluded: Mapping[LoopId, str] | None = None) -> LoopDecision | None`:
      loops in LOOP_PREFERENCE, skipping `excluded`; the first whose candidates hold one with
      effective_weight > 0 wins. `sovereign_exclusions` = exclusions of engines whose descriptor
      tier is LOCAL + a NO_WEIGHT exclusion for each LOCAL candidate with weight 0 + (when
      SOVEREIGNLOOP is in `excluded`) an UNROUTABLE exclusion per LOCAL candidate with
      `detail=excluded[SOVEREIGNLOOP]`. No affinity crosses loops (ADR §2): a warm paid session
      never beats a sovereign candidate with positive weight. None when no loop qualifies.
    - Registry: `LoopSelectorInterface` → `EXEMPT` `PURE_POLICY` (no I/O).
    - deps: `loops-weighted-candidates`, `loops-domain-loop-id`, `fakes-registry`.

23. `loops-subprocess-fallback-declared` — L13 — `src/vibey/application/engine_selection.py`
    (SelectingEngineProvider), `src/vibey/bootstrap.py` (build_full_worker passes the two new
    arguments); test `tests/application/test_paid_fallback_subprocess.py`.
    - SelectingEngineProvider gains `decisions: PhaseLedger | None = None`,
      `loop_selector: LoopSelectorInterface | None = None`. `select_for` calls
      `weighted_candidates` then `select_from` (same inputs as today; same CapacityDeferred on
      NoEligibleEngine). When the selected engine's descriptor tier is PAID and both collaborators
      are set, it appends `EventKind.PAID_FALLBACK_DECLARED` via
      `decisions.append_event(job.project_id, job.cycle, job.id, kind, PaidFallbackDeclaration(engine_id, "subprocess", loop_selector.choose(weighted).sovereign_exclusions or recomputed).to_payload())`.
      Written after `assign_engine`. In bootstrap: `decisions=PostgresReviewLedger(resources.ledger, phase=Phase.BUILD)`,
      `loop_selector=LoopSelector(descriptors=BY_ENGINE_ID)`.
    - Tests use `tests.fakes.ledger.review_ledger(InMemoryLedger(), phase=Phase.BUILD)`,
      `tests.fakes.engines` repositories and a real EngineSelector.
    - deps: `loops-loop-selector`, `fakes-ledger`, `orm-ledger`, `engines-pool`.

24. `loops-routing-ports` — L14 — `src/vibey/application/interfaces/loop_routing.py` (append),
    `src/vibey/application/interfaces/__init__.py` (exports), `tests/fakes/loops.py` (NEW),
    `tests/fakes/registry.py`; test `tests/fakes/test_fake_loops.py`.
    - `LoopRoutingPort`: `async route(self, request: RouteRequest, *, wait: timedelta) -> RunRouted | None`.
    - `RoutedAdapterBinderInterface`: `bind(self, routed: RunRouted, *, job: JobRecord) -> EngineAdapter`.
    - Fakes: `FakeLoopRouting(replies: Mapping[LoopId, RunRouted | None])` (records `requests`;
      rebinds each scripted reply's route_id to the request's; missing loop → None);
      `FakeRoutedAdapterBinder(adapters: Mapping[str, EngineAdapter])` (records `binds`; unknown engine → KeyError).
    - deps: `loops-loop-selector`, `loops-run-protocol-messages`, `fakes-registry`, `fakes-engines`.

25. `loops-queue-saturated` — L15 — `src/vibey/application/worker.py`, `src/vibey/application/dto.py`
    (RunSpec), `src/vibey/application/build_implement_handler.py` (:222-230); test
    `tests/application/test_queue_saturation.py`.
    - R25 behaviours 1–3 carried verbatim (updates/372.md): `RunSpec.supersede_key: str | None = None`,
      `attempt: int = 0` (last); handler passes `supersede_key=str(job.id)`, `attempt=job.attempts`;
      `class EngineQueueSaturated(Exception)` with `retry_at`, `detail`; `run_once` catches it
      beside CapacityDeferred → `Defer(exc.retry_at, exc.detail, capacity=False)`. Stop rule for
      tests that compare whole RunSpec values.
    - deps: `fakes-build`.

26. `loops-selecting-loop-provider` — L16 — `src/vibey/application/loop_provider.py`
    (+ `LoopProviderInterface`? no: it implements `EngineProvider`); test `tests/application/test_loop_provider.py`.
    - `SelectingLoopProvider(*, selector: EngineSelectorInterface, loop_selector: LoopSelectorInterface, routing: LoopRoutingPort, binder: RoutedAdapterBinderInterface, health: EngineHealthServiceInterface, adapters: Mapping[EngineId, EngineAdapter], jobs: JobRepository, decisions: PhaseLedger, clock: Clock, owner: str, allow_list: frozenset[EngineId] | None = None, backoff: timedelta = timedelta(minutes=5), route_wait: timedelta = timedelta(seconds=30), local_engines: tuple[EngineId, ...] = (), metrics: TelemetryMetrics | None = None, route_ids: Callable[[], UUID] = uuid4)`.
    - `pool` as SelectingEngineProvider. `select_for(job)`: inputs; local preflights (copy
      `engine_selection.py:208-220`); `weighted`; loop over at most two loops:
      `decision = loop_selector.choose(weighted, excluded=excluded)`; None → `CapacityDeferred`
      (backoff, "no loop can take this job: <exclusions>"); publish `RouteRequest(route_id=route_ids(), loop_id, project_id=job.project_id, candidates=tuple(RouteCandidate(c.engine_id.value, c.effective_weight) for c in decision.candidates), pin=None, model_pin=None, min_context=None, requested_at=clock.now(), caller=owner)`;
      `routed = await routing.route(req, wait=route_wait)`; None or DEAD_LETTERED →
      `EngineQueueSaturated(clock.now() + route_wait, f"no {loop} router answered within {n}s")`
      (D7); UNROUTABLE → `excluded[loop] = routed.reason`, continue; ROUTED → engine must be
      in adapters (else CapacityDeferred "routed engine X has no configured adapter");
      `health.record_selection`, metrics, `jobs.assign_engine`; append `LoopRouted`
      (`LoopRoutedRecord(...).to_payload()`), and `PaidFallbackDeclared`
      (`PaidFallbackDeclaration(engine, "service", decision.sovereign_exclusions)`) when loop is
      PAIDLOOP; return `binder.bind(routed, job=job)`.
    - Registry: none new (uses fakes from loops-routing-ports).
    - deps: `loops-routing-ports`, `loops-queue-saturated`, `loops-subprocess-fallback-declared`, `orm-job-settle`.

27. `loops-claudeloop-local-paid` — L17a — `src/vibey/infrastructure/engines/descriptors.py`
    (ClaudeloopLocalDescriptors.build: `tier=EngineTier.PAID`; `LOCAL_DESCRIPTORS` keeps it only
    as a profile-built descriptor list → rename not needed; update the comment),
    `src/vibey/domain/config.py` (drop `"claudeloop-local"` from `LOCAL_ENGINE_FEATURES`; delete
    the "must be true before claudeloop-local can be requested" validation; a legacy
    `[features] claudeloop_local` is recorded as `LegacySpelling("features.claudeloop_local", "claudeloop_local", "[engines].enabled = [\"claudeloop-local\"]")`),
    `src/vibey/infrastructure/engines/local_engines.py` (`LocalEngineSettings.enabled(EngineId.CLAUDELOOP_LOCAL)`
    is True iff the config declares it: `engines` table `enabled` list or CR list names it;
    `VIBEY_FEATURE_CLAUDELOOP_LOCAL` is ignored with one warning per instance
    `"claudeloop-local is declared-only now (ADR-0046 §9, sub-doctrine 8.b): name it in [engines].enabled; ignoring VIBEY_FEATURE_CLAUDELOOP_LOCAL"`);
    also the worker's "matches none" message (`cli/main.py`, the `--engines ... matches none` block)
    no longer mentions any switch. Test `tests/infrastructure/engines/test_claudeloop_local_paid.py`.
    - BREAKING CHANGE footer: claudeloop-local is paid-side and declared-only.
    - deps: `loops-config-engine-names`, `engines-pool`.

28. `loops-paidloop-keyword` — L17b — `src/vibey/domain/engine_names.py` (resolver gains
    `LOOP_KEYWORDS = {"paidloop": "claudeloop"}`: resolve expands it, no LegacySpelling),
    `src/vibey/cli/main.py` (`--engines` parse at `:1472-1474` goes through
    `EngineNameResolver().resolve_all(..., where="--engines")`, printing each LegacySpelling to
    stderr), test `tests/domain/test_paidloop_keyword.py`.
    - `[engines] enabled = ["paidloop"]` → `("sovereignloop", "claudeloop")`; `--engines paidloop`
      narrows to claudeloop (D12).
    - deps: `loops-claudeloop-local-paid`, `loops-domain-loop-id`.

29. `loops-runid-common` — L19 — `src/vibey_runners/common/src/vibey_runners/common/domain/__init__.py`,
    `.../domain/run_id.py`, `.../domain/interfaces/__init__.py`, `.../domain/interfaces/run_id_interface.py`,
    `src/vibey_runners/common/tests/test_run_id.py` (NEW tests dir), CI rows for
    vibey-runners-common gain `test: 'python -m pytest -q'` (ci.yml :321-335; fix the "ships no
    suite" comment). `RunId.parse(raw) -> RunId` exactly as `opencodeloop/domain/model.py:14-33`
    (pattern `\A[A-Za-z0-9][A-Za-z0-9._-]{0,127}\Z`, same message). Pure; `dependencies = []` kept.
    - deps: none.

### Family AMQP (10.e: taught to vibey_bootstrap.amqp)

30. `loops-amqp-queue-depth` — L21a — tenant `src/vibey_tools/bootstrap/vibey_bootstrap/amqp/client.py`,
    `memory.py`, `interfaces/client_interface.py`; tests appended to `test/amqp/test_memory_client.py`,
    `test_client_unit.py`, `test_client_integration.py` (the T21 layout).
    - `queue_depth(queue: str) -> int | None`: temporary channel, `declare_queue(queue, passive=True)`,
      `declaration_result.message_count`; missing queue → None; always closes the channel (T21 pattern).
      In memory: ready (unsettled excluded) messages; undeclared → None. V-AMQP2 integration test on a quorum queue.
    - deps: `rmq-r04-bootstrap-amqp`, `harness-T21-amqp-consumer-count`.

31. `loops-amqp-exclusive-consume` — L21b — same three files; `errors.py` gains
    `AmqpExclusiveConsumerRefused(AmqpError)` (attribute `queue`).
    - `consume(queue, *, prefetch, handler, exclusive: bool = False) -> str`; a refusal
      (aiormq `ChannelAccessRefused`/`ChannelLockedResource`, reply 403/405) → `AmqpExclusiveConsumerRefused(queue)`.
      In memory: an exclusive consumer refuses any second consumer; exclusive is refused when one exists.
      V-AMQP1 integration test (quorum queue, pinned `rabbitmq:4-management-alpine`).
    - deps: `loops-amqp-queue-depth`.

### Loop service (infrastructure/loop_service/, database-free)

32. `loops-result-store` — L22 — creates `src/vibey/infrastructure/loop_service/__init__.py`,
    `interfaces/__init__.py`, `result_store.py`, `measurement_log.py`, their interfaces
    (`interfaces/result_store_interface.py`, `interfaces/measurement_log_interface.py`),
    `.importlinter` (add `vibey.infrastructure.loop_service.interfaces` to
    `infrastructure-interfaces-declare-only`); fakes `InMemoryRunResultStore`,
    `InMemoryLoopMeasurementLog` appended to `tests/fakes/loops.py` + DRIVER_SEAMS; test
    `tests/infrastructure/loop_service/test_result_store.py`.
    - `RunResultStore`: R21 behaviour 1 (path `<cwd>/.vibey/diagnostics/<run_id>.result.json`,
      atomic temp+`os.replace`, missing → None, malformed → None + warning) using RunProtocolCodec.
    - `LoopMeasurementLog(path: Path, logger)`: `record(m: LoopMeasurement) -> None` appends one
      JSON line (`sort_keys`) to `path` (parents created, append-only, never truncates) and logs
      `loop_measured` with the same fields.
    - deps: `loops-run-codec`, `loops-ledger-kinds`, `loops-routing-ports`.

33. `loops-local-run-executor` — L24 — `local_run_executor.py` + interface; fake
    `FakeLocalRunExecutor` (scripted exits/outputs, records starts/stops/controls); test
    `tests/infrastructure/loop_service/test_local_run_executor.py`.
    - `LocalRunExecutor(*, binaries: Mapping[str, str] (engine id → binary), root: Path, policy: RunArgsPolicyInterface, spawner: ProcessSpawnerInterface, resolver: ExecutableResolverInterface, reaper: ProcessReaperInterface, base_environ: Mapping[str, str])`.
      `reason_to_reject(request) -> str | None`: engine not in binaries (`"engine <id> is not an adapter of this loop"`),
      policy reason, cwd absolute and under `root.resolve()`, run_dir (when set) under cwd.
      `async start(request, *, env_overlay: Mapping[str, str]) -> LocalRunInterface`: argv =
      `(resolver.resolve(binary), *request.args)`; env = `isolate_python_env(base_environ)` + overlay;
      RUN without capture → `<cwd>/.vibey/diagnostics/<run_id>.stdout|.stderr`, else pipes capped
      64 KiB; `cwd=request.cwd`, `start_new_session=True`.
      `LocalRun`: `pid`, `wait(timeout)`, `stop(grace_seconds)` (RunInbox stop, grace, reaper),
      `control(command, text)` (STOP/WIND_DOWN → write_command; prompts → write_prompt),
      `output()`, `meta_status()` — R21 behaviour 3.
    - deps: `loops-result-store`, `loops-run-args-policy`, `rmq-r20-run-dir-extraction`, `rmq-r20-process-launcher`.

34. `loops-worktree-fence` — L25 — `worktree_lock.py` + interface; fake `InMemoryWorktreeFence`;
    test `tests/infrastructure/loop_service/test_worktree_lock.py`.
    - `FenceOutcome(StrEnum)`: ACQUIRED, SUPERSEDED, BUSY, BUSY_SUPERSEDING;
      `FenceHolder(run_id: UUID, key: str | None, attempt: int, loop_id: str, instance: str, run_dir: str | None, started_at: datetime, deadline_at: datetime)`;
      `FenceDecision(outcome, holder_run_id: UUID | None = None, broke_stale: bool = False)`.
    - `WorktreeFence(*, stale_after: timedelta, clock: Clock, inbox_factory: Callable[[Path], RunInboxInterface] = RunInbox, logger)`:
      `acquire(cwd: Path, holder) -> FenceDecision`: under `fcntl.flock` of `<cwd>/.vibey/supersede.lock`
      read/update `<cwd>/.vibey/supersede.json` (`{key: high_water}`; attempt below → SUPERSEDED;
      raise high water with max). Then `os.open(<cwd>/.vibey/run.lock, O_CREAT|O_EXCL|O_WRONLY, 0o600)`
      and write the holder JSON → ACQUIRED. On FileExistsError read the holder: same run_id →
      ACQUIRED (redelivery); `now > deadline_at + stale_after` or unreadable → rename to
      `run.lock.stale-<utc ts>` (never delete), log `worktree_lock_stale_broken`, retry once →
      ACQUIRED(broke_stale=True); same key and lower attempt → `inbox_factory(Path(holder.run_dir)).write_stop()`
      (when run_dir) → BUSY_SUPERSEDING(holder.run_id); else BUSY(holder.run_id).
      `release(cwd, run_id) -> bool` unlinks only when the holder's run_id matches.
      `high_water(cwd, key) -> int | None`.
    - Writes only inside `<cwd>/.vibey/` (Security impact). V-FS1 local case tested
      (two threads racing `acquire` → exactly one ACQUIRED).
    - deps: `loops-result-store`, `rmq-r20-run-dir-extraction`.

35. `loops-model-runtime` — L26 — `src/vibey/infrastructure/engines/ollama_chat.py` (+
    `interfaces/ollama_chat_interface.py`: `get_json(url, *, timeout) -> dict[str, object]` on
    `UrllibOllamaTransport`, same scheme check) and `loop_service/model_runtime.py` + interface;
    fake `FakeModelRuntime(loaded: tuple[str, ...] | None)` (records unloads); test
    `tests/infrastructure/loop_service/test_model_runtime.py`.
    - `OllamaModelRuntime(*, base_url: str, transport: OllamaTransportInterface | None = None, timeout: int = 10)`:
      `loaded() -> tuple[str, ...] | None` (GET `/api/ps` → `models[].name`; any error → None =
      unreachable); `unload(model) -> bool` (POST `/api/generate` `{"model": M, "keep_alive": 0}`);
      `base_url` property. V-OLL1 integration test with `VIBEY_TEST_OLLAMA_URL`.
    - deps: `loops-result-store`.

36. `loops-state-stores` — L27 — `route_store.py` + interface; fakes `InMemoryRouteStore`,
    `InMemoryLoopCursorStore`; test `tests/infrastructure/loop_service/test_route_store.py`.
    - `RouteStore(root: Path, codec)`: `create_once(routed: RunRouted) -> RunRouted` (O_EXCL create
      `<root>/routes/<route_id>.json`; exists → the stored one), `get(route_id) -> RunRouted | None`,
      `prune(older_than: datetime) -> int`.
    - `LoopCursorStore(root: Path)`: `load(project_id: UUID | None) -> tuple[SeatCursor, ...]`,
      `save(project_id, cursors)` atomic replace at `<root>/cursors/<project_id or "_">.json`.
    - deps: `loops-result-store`, `loops-seat-chooser`.

37. `loops-seat-host-core` — L28a — `seat_host.py` + interface; `src/vibey/domain/errors.py`
    (`LoopInstanceRefused(VibeyError)`, message "another instance already consumes <queue>:
    sub-doctrine 8.c runs a single instance per model"); fake `FakeSeatHost`; test
    `tests/infrastructure/loop_service/test_seat_host_core.py`.
    - `SeatHost(*, loop_id, seat: str (slug), model: str | None, amqp, names, codec, executor, results, config: LoopConfigInterface, environ: Mapping[str, str], clock, instance: str, measurements, logger, prefetch: int)`.
      `declare()` (seat queue + its dead queue via `names.queue_arguments`), `consume()`
      (exclusive; refusal → `LoopInstanceRefused`), `cancel()`, `start()` = declare + consume.
      `_on_request`: a (malformed / not a RunRequest / other loop → `dead_letter()`), c (persisted
      result → republish, complete), e (late → REJECTED "not started before start_by"), f
      (`executor.reason_to_reject`), h (RunAccepted with queued_seconds = started−requested;
      wait bounded by deadline_seconds; past it stop with `supersede_grace_seconds` → DEADLINE_EXCEEDED;
      else EXITED with exit_code/meta_status; persist (RUN only) → publish (confirm) → `complete()`),
      replies to `reply_to` on the default exchange with `correlation_id=str(run_id)`.
      Env overlay per run: `{**LocalEndpointEnvironment(environ, model=model).overlay_for(engine), <model env var>: model}`
      for sovereign engines (the seat's model always wins, D6), `{}` for paid.
      D1 at start: `runtime` is not this lane's (the process logs it); this lane never checks it.
      8.g: RUN measurement per run.
    - deps: `loops-local-run-executor`, `loops-amqp-exclusive-consume`, `loops-config-loop-services`, `loops-vibey-local-engine-names`.

38. `loops-seat-host-fence` — L28b — `seat_host.py` (append/edit); test `tests/infrastructure/loop_service/test_seat_host_fence.py`.
    - rules b (run_id active here → rebind delivery, start nothing), d (run_dir exists with
      non-terminal meta.json → ABANDONED "run directory left non-terminal by a previous service
      instance"), g (WorktreeFence.acquire before start: SUPERSEDED → reply SUPERSEDED;
      BUSY_SUPERSEDING → REJECTED "worktree busy: superseding <run_id>"; BUSY → REJECTED
      "worktree busy"; release after the result is persisted); REJECT measurement.
    - deps: `loops-seat-host-core`, `loops-worktree-fence`.

39. `loops-seat-host-drain` — L28c — `seat_host.py`; test `tests/infrastructure/loop_service/test_seat_host_drain.py`.
    - progress (`RunProgress` per new events.jsonl line when `publish_progress` and run_dir;
      0.5 s poll; seq from 1), `busy` property, `active_run_ids()`, `control(run_id, command, text) -> bool`,
      `stop_lower_attempts(key, attempt) -> tuple[UUID, ...]`, `on_run_finished` callback
      (`Callable[[str], Awaitable[None]] | None`), `stop(grace_seconds)` drain (cancel consumer,
      wait, then stop remaining → ABANDONED written/published/completed).
    - deps: `loops-seat-host-fence`.

40. `loops-resident-schedule` — L29 — `resident_schedule.py` + interface; fakes `InMemorySeatBacklog`?
    (no: SeatBacklog is pure in-memory — register the real class with note "production in-memory"),
    `FakeResidentScheduler`; test `tests/infrastructure/loop_service/test_resident_schedule.py`.
    - `SeatBacklog`: `forwarded(seat, run_id, at)`, `started(seat, run_id)`,
      `oldest_wait_seconds(seat, now) -> float | None`, `pending(seat) -> int` (restart ⇒ empty: age from restart, ADR §4).
    - `ResidentSeatScheduler(*, loop_id, hosts: Mapping[str, SeatHostInterface], models: Mapping[str, str] (slug→model), default_seat: str, amqp, names, runtime: ModelRuntimeInterface, schedule: ResidencyScheduleInterface, backlog, config, clock, measurements, logger)`:
      `resident_seat`, `resident_model`; `start()` (initial resident = a declared model among
      `runtime.loaded()`, preferring the default; else default; consume that host only);
      `on_run_finished(seat)` (count; call `tick`); `tick()` (depth via `amqp.queue_depth`,
      waits via backlog, `schedule.next_seat(...)`; on switch: wait until not busy → `cancel()`
      old → `runtime.unload(old model)` when `unload_on_switch` → `consume()` new → SWITCH
      measurement); `run_forever()` ticking every `schedule_interval_seconds`; `stop()`.
    - deps: `loops-seat-host-drain`, `loops-residency-schedule`, `loops-model-runtime`.

41. `loops-router-routing` — L30a — `router.py` + interface; fake `FakeLoopRouter`; test
    `tests/infrastructure/loop_service/test_router_routing.py`.
    - `LoopRouter(*, loop_id, amqp, names, codec, config, seats: Mapping[str, str] (slug→declared name), adapters: frozenset[str], default_adapter: str, routes: RouteStoreInterface, cursors: LoopCursorStoreInterface, chooser: SeatChooserInterface, residency: ResidencyPolicyInterface, declarations: tuple[ModelDeclaration, ...], default_model: str | None, resident_model: Callable[[], str | None], backlog: SeatBacklogInterface, measurements, clock, logger)`.
      `start()`: declare runs (direct), dlx (direct), control (topic) exchanges; intake queue +
      intake dead; every seat queue + seat dead (all with `queue_arguments`); probe queue
      (classic); consume intake exclusively (prefetch `router_prefetch`; refusal →
      LoopInstanceRefused). `route(request) -> RunRouted` (candidates ⊆ adapters else
      UNROUTABLE "engine X is not an adapter of <loop>"; sovereign: ResidencyPolicy → model or
      UNROUTABLE UNROUTABLE_NO_MODEL; SeatChooser; depth via `amqp.queue_depth`, oldest wait via
      backlog; `routes.create_once` BEFORE `cursors.save` (a redelivery never advances SWRR
      twice; a crash between them only misses an advance)); `_on_intake` for RouteRequest:
      stored route → re-send it; else route, reply to reply_to (correlation_id = route_id), complete.
      ROUTE measurement. Anything else not a RouteRequest/RunRequest → dead_letter.
    - deps: `loops-state-stores`, `loops-resident-schedule`, `loops-amqp-exclusive-consume`, `loops-config-loop-services`.

42. `loops-router-forwarding` — L30b — `router.py`; test `tests/infrastructure/loop_service/test_router_forwarding.py`.
    - RunRequest on intake: `route_id` set → stored route → publish the body unchanged to
      `seat_key(loop, seat)` with `message_id = str(run_id)`, reply_to/correlation kept;
      `backlog.forwarded`; complete. Missing route → reply `RunResult(UNROUTABLE, detail="no route <id>")`.
      No route_id (pinned run) → `route(RouteRequest(route_id=run_id, …, candidates=(), pin=engine_id, model_pin=request.model_pin, …))`
      then forward; unroutable → `RunResult(UNROUTABLE, detail=reason)`. PROBE purpose on intake →
      forward to the probe key. FORWARD measurement. A redelivered forward lands in the same seat (stored route).
    - deps: `loops-router-routing`.

43. `loops-control-and-dead-letters` — L31a — `control.py` + interface; fakes
    `FakeRunControlConsumer`, `FakeDeadLetterReplier`; test `tests/infrastructure/loop_service/test_control.py`.
    - `RunControlConsumer(*, loop_id, amqp, names, codec, hosts: Sequence[SeatHostInterface], logger)`:
      server-named exclusive auto-delete queue bound to the control exchange with both
      `control_keys(loop)`; STOP/WIND_DOWN/PROMPT_* → the host holding run_id; SUPERSEDE →
      `stop_lower_attempts` on every host; unknown run ignored; malformed completed + logged.
    - `RunDeadLetterReplier(*, loop_id, amqp, names, codec, seats: Sequence[str], measurements, clock, logger)`:
      consumes intake dead + each seat dead queue; RunRequest with reply_to → `RunResult(DEAD_LETTERED, detail="the request crashed its <loop> seat <n> times")`;
      RouteRequest → `RunRouted(status=DEAD_LETTERED, reason="route request dead-lettered after <n> deliveries")`; complete; DEAD_LETTER measurement.
    - deps: `loops-seat-host-drain`, `loops-router-forwarding`.

44. `loops-probe-consumer` — L31b — `control.py` (append); test `tests/infrastructure/loop_service/test_probe_consumer.py`.
    - `RunProbeConsumer(*, loop_id, amqp, names, codec, executor, environment: Callable[[str, str | None], Mapping[str, str]], resident_model: Callable[[], str | None], default_model: str | None, clock, measurements, logger)`:
      consumes the probe queue (prefetch 4); executor.reason_to_reject → REJECTED; a model-loading
      probe (sovereignloop and args[0] == "doctor") whose model (resident, else default) is not
      resident and has a cached answer → reply the cached RunResult with `cached_at` = its time;
      otherwise run (first probe for a model always runs), cache it by (engine, args, model),
      reply with stdout/stderr. PROBE measurement (outcome ran|cached).
    - deps: `loops-control-and-dead-letters`, `loops-resident-schedule`.

45. `loops-client` — L32 — `client.py` + `interfaces/client_interface.py` (`LoopClientInterface`,
    `RunTicketInterface`); fake `FakeLoopClient` (scripted routed/accepted/progress/result per
    request; records publishes; implements LoopRoutingPort); test `tests/infrastructure/loop_service/test_client.py`.
    - `LoopClient(amqp, names, codec, clock, caller: str)`: R24 carried (updates/371.md) with:
      `route(request, *, wait) -> RunRouted | None` (publish to runs exchange key `intake_key(loop)`,
      `message_id = correlation_id = str(route_id)`, await by route_id); `submit(request) -> RunTicket`
      (RUN → intake key, PROBE → probe key; `type="run.request"`, no expiration);
      `probe(loop_id, engine_id, args, *, cwd, timeout, model_pin=None) -> RunResult | None`;
      `control(loop_id: LoopId | None, message: RunControl)` (key = loop or "all"); `close()`.
      `RunTicket.accepted/progress/result/latest_result/latest_accepted`. Satisfies `LoopRoutingPort`.
    - deps: `loops-amqp-exclusive-consume`, `loops-routing-ports`, `loops-result-store`.

46. `loops-service-adapter-run` — L33a — `adapter.py` + interface; test `tests/infrastructure/loop_service/test_adapter_run.py`.
    - `LoopServiceAdapter(descriptor, client: LoopClientInterface, loop_id: LoopId, *, clock, run_queue_wait: timedelta, deadline: timedelta, route_id: UUID | None = None, model_pin: str | None = None, decisions: PhaseLedger | None = None, job: JobRecord | None = None)`:
      `start(spec)` (R25 start carried: plan file, `args = build_argv(descriptor, spec)[1:]`,
      run_dir; when `spec.supersede_key` and `spec.attempt > 0` first publish
      `RunControl(None, SUPERSEDE, None, RunSupersede(key, attempt))` with loop None ("all");
      submit RunRequest(loop_id, engine_id, route_id, model_pin, …); no RunAccepted within
      `run_queue_wait + 5 s`, or REJECTED "worktree busy…"/"not started before start_by", or
      UNROUTABLE → `EngineQueueSaturated`); `tail` (RunDirTailer; after the tailer ends and a
      result exists, when `decisions` and `job` are set, append `LoopRunMeasured` via
      `decisions.append_event(job.project_id, job.cycle, job.id, EventKind.LOOP_RUN_MEASURED, LoopRunMeasurement(...).to_payload())`, once);
      `run_exit_code`, `diagnostic_tail`, `release_diagnostics` (R25 carried).
      `RoutedAdapterBinder(*, client, descriptors: Mapping[EngineId, EngineDescriptor], clock, run_queue_wait, deadline, decisions: PhaseLedger | None)`
      implements `RoutedAdapterBinderInterface` (`bind(routed, job=job)` → adapter with
      route_id/model and the job).
    - deps: `loops-client`, `loops-queue-saturated`, `rmq-r20-run-dir-extraction`, `fakes-ledger`.

47. `loops-service-adapter-control` — L33b — `adapter.py`; test `tests/infrastructure/loop_service/test_adapter_control.py`.
    - `send_prompt`, `stop` (control STOP then StopSummaryReader + snapshot, no process
      handling), `snapshot`, `preflight()` (probes `("--version",)`, `("doctor", *descriptor.doctor_args)`,
      caches `("run","--help")` for `help_text`, timeouts from config probe keys; no answer →
      `PreflightResult(installed=False, …, detail="no <loop> router answered for <engine>")`),
      `help_text`, `classify`/`attribute` from `classify.py` unchanged — R25 carried.
    - deps: `loops-service-adapter-run`.

48. `loops-command-executor` — L34 — `command_executor.py` + interface; test `tests/infrastructure/loop_service/test_command_executor.py`.
    - `LoopServiceCommandExecutor(loop_id, engine_id, binary, client, *, clock, run_queue_wait, deadline)`
      implements `vibey.infrastructure.interfaces.CommandExecutor` (R26 carried, updates/373.md);
      pinned run (route_id None); no opencode test (8.b repealed it).
    - deps: `loops-client`, `loops-queue-saturated`, `fakes-process-executor`.

49. `loops-adapter-factory` — L35a — `src/vibey/infrastructure/engines/adapter_factory.py` +
    `interfaces/adapter_factory_interface.py`, `local_engines.py` (`adapter(..., *, factory=None)`,
    `adapters(endpoint, *, factory=None)`); fake `FakeAdapterFactory`; test `tests/infrastructure/engines/test_adapter_factory.py`.
    - `EngineAdapterFactoryInterface.build(descriptor, *, env_overlay: Mapping[str, str]) -> EngineAdapter`;
      `SubprocessAdapterFactory` (today's `LoopProcessAdapter(descriptor=…, env_overlay=…)`);
      `ServiceAdapterFactory(client, *, clock, run_queue_wait, deadline)` (unbound
      LoopServiceAdapter with `LoopMembership().loop_of(descriptor)`; env comes from the loop,
      the overlay is ignored — documented); `EngineInvocationSettings.resolve(config, environ) -> str`
      (`VIBEY_ENGINE_INVOCATION`, then `config.engines.invocation`, then "subprocess"; any other
      value → ConfigError("engines.invocation", ...)).
    - deps: `loops-service-adapter-control`, `rmq-r01-queue-config`, `engines-pool`.

50. `loops-invocation-composition` — L35b — `src/vibey/bootstrap.py`, `src/vibey/bootstrap_interface.py`;
    test `tests/test_bootstrap_invocation.py`.
    - `build_loop_client(config, environ, *, amqp_factory=None) -> LoopClient` (R17
      `QueueBackendSettings.from_sources` for URL/prefix; no URL → `QueueBackendNotConfigured`);
      `AppResources.engine_factory`, `AppResources.loop_client: LoopClientInterface | None = None`,
      `AppResources.command_executor_for(engine_id, binary) -> CommandExecutor` (subprocess →
      `AsyncSubprocessExecutor()`; service → `LoopServiceCommandExecutor`); `build_app` in
      service mode builds the client (closed in `finally`) and the adapters through
      `ServiceAdapterFactory`; `build_full_worker` in service mode builds `SelectingLoopProvider`
      with `RoutedAdapterBinder` and `decisions=PostgresReviewLedger(resources.ledger, phase=Phase.BUILD)`.
      Defaults (subprocess) change nothing observable.
    - deps: `loops-adapter-factory`, `loops-selecting-loop-provider`, `loops-command-executor`,
      `rmq-r17-queue-backend-selection`, `orm-bootstrap-engine`, `loops-config-loop-services`.

51. `loops-invocation-cli` — L35c — `src/vibey/cli/main.py`; test `tests/cli/test_invocation_cli.py`.
    - The four `AsyncSubprocessExecutor()` sites (`:430`, `:457`, `:1578`, `:1617` at d3b4a388)
      use `resources.command_executor_for(engine_id, binary)`; `vibey doctor --conformance` in
      service mode defaults its trivial worktree to `<loop_services.root>/.vibey-conformance-<id>`
      (the `unique_worktree = str(` block in `doctor`) — R28 behaviour 5, carried explicitly (ADR-0046 does not mention it).
    - deps: `loops-invocation-composition`, `loops-cli-provider-name`.

52. `loops-service-process` — L36a — `loop_service/process.py` + interface; fake
    `FakeLoopServiceProcess`; test `tests/infrastructure/loop_service/test_process.py`.
    - `LoopRole(StrEnum)`: ALL="all", ROUTER="router", SEAT="seat".
      `LoopServiceProcess(*, loop_id, role, router, hosts: Mapping[str, SeatHostInterface], scheduler, control, probes, dead_letters, runtime: ModelRuntimeInterface | None, logger)`:
      `start() -> str` (order: router → dead letters → probes → hosts (sovereign ALL: scheduler.start;
      else every host.start) → control; returns the runtime line: `attached <url>` /
      `unreachable (<url>)` / `n/a` — D1: unreachable never stops the start);
      `stop(grace_seconds)` (reverse order; hosts drain); `summary` property.
    - deps: `loops-router-forwarding`, `loops-probe-consumer`, `loops-control-and-dead-letters`, `loops-resident-schedule`.

53. `loops-bootstrap-loop-service` — L36b — `src/vibey/bootstrap.py`; test `tests/test_bootstrap_loop_service.py`.
    - `build_loop_service(loop_id: LoopId, *, role: LoopRole, seats: tuple[str, ...], capacity: int | None, config: VibeyConfig | None, environ: Mapping[str, str], amqp_factory=None) -> LoopServiceProcess`.
      Resolves: AMQP (R17); `LoopConfig`; seats (flag, else effective models; paid default
      `("claudeloop",)`); binaries from descriptors of the loop (`LoopMembership`; claudeloop-local
      uses the claudeloop binary); state dir (`[loop_services] state_dir`, else
      `<root>/.vibey/loops/<loop>` when root != "/", else `platformdirs.user_state_path("vibey")/"loops"/<loop>`);
      runtime (sovereign: `OllamaModelRuntime(base_url=VIBEY_OLLAMA_URL or DEFAULT_OLLAMA_URL)`).
      No database. No AMQP URL → `QueueBackendNotConfigured`.
    - deps: `loops-service-process`, `loops-invocation-composition`.

54. `loops-cli-loop-service` — L36c — `src/vibey/cli/loop_service.py` (NEW),
    `src/vibey/cli/interfaces/loop_service_interface.py` (`LoopCliSeamsInterface`), `src/vibey/cli/main.py`
    (register like `ledger_search`, `:38`, `:87-88`); test `tests/cli/test_loop_service_cli.py`.
    - D2/D3 flags and exits; startup line
      `loop-service started: loop=<loop> role=<role> seats=<slug,...> capacity=<n> runtime=<line>`;
      SIGTERM handling copied from `cli/main.py` worker (`:1519-1540`: `add_signal_handler`,
      `SIGTERM_LATCH.release()`, `fired`); `LoopCliSeams(build_service=bootstrap.build_loop_service, build_client=bootstrap.build_loop_client)`
      passed via `CliRunner.invoke(obj=...)` in tests.
    - deps: `loops-bootstrap-loop-service`.

55. `loops-cli-loop-submit` — L36d — `src/vibey/cli/loop_service.py` (append `loop submit`);
    test `tests/cli/test_loop_submit_cli.py`.
    - D4. Builds an unbound `LoopServiceAdapter` for the engine descriptor with `model_pin`, calls
      `start(RunSpec(...))`; `--follow` prints progress lines; awaits the result up to `--timeout`;
      prints the RunResult JSON (codec) on one line; exits per D4 (75 on `EngineQueueSaturated`).
    - deps: `loops-cli-loop-service`.

### VS Code (ADR §8) — every lane after the spike is gated (D15)

56. `loops-vscode-spike` — L20a — research, not code. Implementer: the operator or a large
    model (not the 20B). Deliverable: appended section `## Verification recorded (V-VS1..V-VS5, V-CC1)`
    in `STORM/specs/ADR-two-loops.md` + raw evidence under `STORM/evidence/vscode/`
    (transcripts, `product.json` excerpts, proxy/capture summaries, licence texts), with the
    exact command lines, the extension (id, version, licence SPDX, Open VSX URL, no account),
    the settings JSON that pins a local OpenAI-compatible provider, the observed hosts contacted,
    the event stream sample and its mapping to `events.jsonl`, the OSS-vs-Microsoft
    `product.json` fields, OS/arch/versions (macOS and, where available, Arch Linux), and a
    final line `V-VS VERDICT: FEASIBLE` or `V-VS VERDICT: INFEASIBLE — <reason>`. Timebox: 1 day.
    Candidates to evaluate (unverified; verify, never assume): Continue, Cline, Roo Code on Open VSX;
    invocation routes: an extension CLI, `codium --extensionDevelopmentPath/--extensionTestsPath`
    under a virtual display (xvfb on Arch). INFEASIBLE ⇒ vscode stays off, opencode stays, the
    operator decides (ADR §8).
    - deps: none.

57. `loops-vscode-engine-ids` — L20b — `domain/engine.py` (`VSCODE = "vscode"`,
    `VSCODE_PAID = "vscode-paid"`), `infrastructure/engines/descriptors.py` (VSCODE LOCAL:
    binary `vscodeloop`, state `.vscodeloop`, marker `VSCODELOOP_TASK_FULLY_COMPLETE`, cost 0,
    context 32768 (per spike); VSCODE_PAID PAID, same binary; neither in DEFAULT_DESCRIPTORS),
    `infrastructure/engines/classify.py` (`_classify_vscodeloop` on the family `capacity.state`
    shape, both ids; CREDITS_FIXTURES), `infrastructure/engines/loop_events.py` (map = the
    family vocabulary; copy qwenloop's), CRD enum (+`vscode`, `vscode-paid`); test
    `tests/infrastructure/engines/test_vscode_descriptors.py`. Gated.
    - deps: `loops-vscode-spike`, `loops-claudeloop-local-paid`, `loops-drop-qwenloop-alias`.

58. `loops-vscode-paid-config` — L20c — `domain/config.py` (`[engines.vscode_paid] provider`,
    `model` → `VscodePaidConfig`; declaring `vscode-paid` without both → ConfigError naming the
    missing key); test `tests/domain/test_vscode_paid_config.py`. Gated.
    - deps: `loops-vscode-engine-ids`, `loops-config-engine-names`.

59. `loops-vscodeloop-scaffold` — L20d — new tenant `src/vibey_runners/vscode` (pyproject
    `vscodeloop`, Python >=3.12, deps typer; `[tool.importlinter]`, mypy strict, coverage 100,
    addopts like qwen's), `src/vscodeloop/__init__.py`, `domain/model.py` (DONE_MARKER,
    `RunStatus` active/finished/failed/stopped, `StopReason`, `RunBounds(max_turns=40,
    max_seconds=3600.0, stall_timeout_seconds=900.0)`, `CompletionMarker`, `TerminalRule.decide`
    — capacity first → FAILED; carried from `specs/opencodeloop-parity-p1.md` behaviours 3–5, 9),
    `domain/interfaces/…`; root packaging: `pyproject.toml` scripts (`vscodeloop = "vscodeloop.cli.app:main"`),
    packages, sources; Dockerfile COPY; CI rows ×3 (install `pip install -e ../common && pip install -e ".[dev]"`);
    console-script contract list; common's forbidden list (+`vscodeloop`); `uv lock`. Uses
    `vibey_runners.common.domain.RunId`. Test `src/vibey_runners/vscode/tests/test_domain.py`. Gated.
    - deps: `loops-vscode-spike`, `loops-runid-common`, `loops-tenant-rename`.

60. `loops-vscodeloop-run-store` — L20e — `infrastructure/run_store.py` (+ interface):
    `.vscodeloop/runs/<run_id>/` with events.jsonl (append), meta.json (atomic), `inbox/`,
    snapshots/latest.json, stop-summary.md (every terminal state; the marker line only when
    finished); `wind_down_requested` (files new since `begin()`, `type`/`command` in
    stop|wind_down|wind-down); test `tests/test_run_store.py`. Gated.
    - deps: `loops-vscodeloop-scaffold`.

61. `loops-vscodeloop-runner` — L20f — `application/runner.py` +
    `application/interfaces/editor_driver.py` (`EditorDriverInterface`: `async start(workdir: Path, prompt: str, settings: DriverSettings) -> DriverSession`,
    `events(session) -> AsyncIterator[DriverEvent]`, `async send(session, text)`, `async stop(session)`),
    `tests/fakes.py` (`FakeEditorDriver` scripted events); the prompt wrapped with
    `vibey_runners.common.application.usecases.with_done_marker_instruction`; bounds + watchdog
    (turns, seconds, stall, wind-down first); exit 0/1/75/78 (78 when the driver reports a
    backend misconfiguration). Test `tests/test_runner.py`. Gated.
    - deps: `loops-vscodeloop-run-store`.

62. `loops-vscodeloop-cli` — L20g — `cli/app.py`: `run PLAN [--cwd] [--run-id] [--max-turns]
    [--max-seconds] [--stall-timeout]`, `resume RUN_ID`, `doctor`, `prompt RUN_ID TEXT [--now]`,
    `stop RUN_ID`, `wind-down RUN_ID`, `--version`; env `VSCODELOOP_MAX_TURNS`,
    `VSCODELOOP_MAX_SECONDS`, `VSCODELOOP_STALL_TIMEOUT_SECONDS`; invalid run id or bounds → 2.
    The driver is injected (a `CliSeams` obj), default = the not-yet-landed OSS driver slot that
    exits 78 "no editor driver configured". Test `tests/test_cli.py`. Gated.
    - deps: `loops-vscodeloop-runner`.

63. `loops-vscodeloop-oss-driver` — L20h (the ADR's L20) — `infrastructure/codeoss_driver.py`
    (+ interface binding) implementing `EditorDriverInterface` exactly as the spike recorded
    (command, extension, settings file, event mapping); per-run settings pin ONE local
    OpenAI-compatible provider at `VSCODELOOP_BASE_URL` (derived from `VIBEY_OLLAMA_URL`) with
    `VSCODELOOP_MODEL`; editor binary `VSCODELOOP_EDITOR` (default `codium`); the process is
    injected (spawner seam); test `tests/test_codeoss_driver.py` with a scripted fake editor on
    PATH + an `integration` test that runs the real editor when `VSCODELOOP_TEST_EDITOR` is set. Gated.
    - deps: `loops-vscodeloop-cli`.

64. `loops-vscodeloop-doctor` — L20i — `infrastructure/doctor.py` (+ interface): refuses a
    provider host that is not loopback/private/cluster-local (`ipaddress` + `.svc`/`.cluster.local`
    suffixes) for engine `vscode`; refuses an editor build that is not Code - OSS by the
    spike's `product.json` fields; `--provider` paid mode (engine `vscode-paid`) requires
    `VSCODELOOP_PROVIDER` and `VSCODELOOP_MODEL`; wires into `doctor`. Test `tests/test_doctor.py`. Gated.
    - deps: `loops-vscodeloop-oss-driver`.

65. `loops-vscode-vibey-wiring` — L20j — `src/vibey/infrastructure/engines/local_engines.py`
    (`overlay_for(VSCODE)` → `VSCODELOOP_BASE_URL=<ollama>/v1`, `VSCODELOOP_MODEL`; `VSCODE_PAID` →
    `VSCODELOOP_PROVIDER`/`VSCODELOOP_MODEL` from `[engines.vscode_paid]`), `domain/config.py`
    (`DEFAULT_ENGINES = ("sovereignloop", "vscode")`: always on, 8.b "VS Code when its provider
    is local"), `engine_pool.py` (vscode always in the pool; vscode-paid declared-only); test
    `tests/infrastructure/engines/test_vscode_wiring.py`. Gated.
    - deps: `loops-vscodeloop-doctor`, `loops-vscode-paid-config`, `loops-vibey-local-engine-names`.

### OpenCode retirement (ADR §9) — gated on `V-VS CONFORMANCE: PASS`

66. `loops-retire-opencode-refusals` — L38a — `domain/config.py` (`opencode` in any engine list →
    `ConfigError(<key>, "opencode was retired (sub-doctrine 8.b, ADR-0046 §9); use vscode")`; drop
    from KNOWN_ENGINES), `infrastructure/engines/engine_pool.py` (delete the transitional
    branch + warning), `cli/main.py` (`--provider opencode` refused: "provider 'opencode' was
    retired (sub-doctrine 8.b); use --provider sovereignloop"; `_PROVIDERS` drops it; its two
    provider branches deleted), `infrastructure/cluster_preflight.py` (PROVIDER_ENGINES drops it);
    test `tests/cli/test_opencode_refused.py`. BREAKING CHANGE footer.
    - deps: `loops-vscode-vibey-wiring`, `loops-invocation-cli`, `loops-paidloop-keyword`.

67. `loops-retire-opencode-infra` — L38b — delete `infrastructure/engines/opencodeloop_{design,decompose,process}.py`,
    their interfaces, their tests and `tests/infrastructure/engines/golden/opencode_*.txt`;
    `infrastructure/interfaces/__init__.py` references; descriptors (OPENCODE out of
    DEFAULT_DESCRIPTORS/BY_ENGINE_ID), classify (`_classify_opencode`, fixture), loop_events
    (map); `infrastructure/operator/handlers.py` drops `opencode` from a CR `spec.engines` with a
    warning (`"opencode was retired (ADR-0046 §9); dropped from spec.engines"`). Test
    `tests/infrastructure/test_opencode_retired.py`.
    - deps: `loops-retire-opencode-refusals`.

68. `loops-retire-opencode-id` — L38c — `domain/engine.py` (remove `OPENCODE`;
    `RETIRED_ENGINE_IDS: Final = frozenset({"opencode"})`; `known("opencode") is None`,
    `parse("opencode")` = `UnrecognizedEngineId("opencode")`), `ledger_query.py` (actor
    resolves retired texts verbatim), `tests/meta/test_crd_engine_enum.py` (members ∪ aliases ∪
    retired; CRD keeps `opencode`); test `tests/domain/test_retired_engine_ids.py`.
    - deps: `loops-retire-opencode-infra`.

69. `loops-remove-opencode-tenant` — L39 — `git rm -r src/vibey_runners/opencode`; root
    `pyproject.toml` (packages/sources; `opencodeloop = "vibey.cli.retired:opencodeloop_main"`),
    new `src/vibey/cli/retired.py` (+ `cli/interfaces/retired_interface.py`) printing
    `opencodeloop was retired (sub-doctrine 8.b, ADR-0046 §9); use vscodeloop` to stderr and
    exiting 64; Dockerfile COPY line; CI rows; console-script contract; common forbidden list;
    `uv lock`; test `tests/cli/test_retired_opencodeloop.py`. BREAKING CHANGE footer.
    - deps: `loops-retire-opencode-id`, `loops-vscodeloop-scaffold`.

70. `loops-gh-failover-seats` — L39b — `src/vibey_tools/gh/vibey_gh/failover.py` default
    seats `Seat(name="sovereignloop", launch="sovereignloop run")`,
    `Seat(name="vscodeloop", launch="vscodeloop run")` (docstring updated); tenant test
    `src/vibey_tools/gh/test/test_failover.py` (append); vibey-gh gates (black/isort/mypy/pytest).
    - deps: `loops-remove-opencode-tenant`, `loops-tenant-rename`.

## Filed issues whose rewritten bodies reference these lanes (for the coordinator)
- updates/377.md: depends on `loops-config-loop-services` for `VIBEY_LOOP_SERVICES_ROOT` (not
  #348) and on `loops-cli-loop-service` for the flags; its `QWENLOOP_*` names are renamed later
  by `loops-chart-sovereignloop-names`. Flags match D2 — no body change needed beyond the deps.
- updates/379.md: `loops-cli-loop-service` (flags, exit 78 names 8.c), `loops-seat-host-core`,
  `loops-router-routing`.
- updates/380.md child 1: `loops-run-protocol-messages` (RunQueueNames), `loops-residency-policy`
  (SeatSlug), `loops-client` (`probe(loop_id, engine_id, args, *, cwd, timeout)`; the default
  adapter per loop is `DEFAULT_ADAPTER` in `domain/loop.py`; `RunResult.cached_at`),
  `loops-amqp-queue-depth`; child 2: `loops-adapter-factory` (invocation) and `loops-config-loop-services`.
- updates/381.md: every loops lane through `loops-invocation-cli`, plus `loops-cli-loop-service`.
- updates/348.md: "ADR-0046's loop-configuration lane" = `loops-config-loop-services`.
- updates/367.md: child 2 slug `rmq-r20-process-launcher` (D13).
- updates/321.md: behaviour 1's claudeloop-local switch is superseded by `loops-claudeloop-local-paid`.

## Amendments made while writing (coordinator)
- NEW lane `loops-vscodeloop-editor-settings` (L20h1) split out of the OSS driver lane:
  `EditorSettingsWriter` (per-run `<run_dir>/editor/user-data/User/settings.json` from the
  recorded template) + `EditorProcessLauncherInterface`/`PopenEditorLauncher`. Deps:
  `loops-vscodeloop-cli`; `loops-vscodeloop-oss-driver` now depends on it.
- The vscodeloop editor-driver port is SYNCHRONOUS (threads + watchdog, like opencodeloop),
  not async: `start/events/send/stop`, `events()` a blocking iterator.
- `VSCODELOOP_EDITOR` default: the first of `codium`, `code` on PATH (Arch's Code - OSS ships
  `code`, macOS VSCodium ships `codium`); the doctor's product.json rule refuses Microsoft's build.
- `vscode-paid` argv carries `--paid` (effort projection prefix) and `doctor_args=("--paid",)`.
- `LocalEndpointEnvironment.model_env_for(engine_id)` (lane loops-vscode-vibey-wiring) is the
  seat host's forced-model key once vscode lands.
- OpenCode retirement: refusals (L38a, config/pool/CLI/preflight + `cli/retired_providers.py`),
  provider-module deletion + operator drop (L38b), then enum member + descriptor + classifier +
  fixtures + event map + goldens together (L38c), because the suite requires every EngineId member
  to have all of them.
- test_argv goldens are named by engine id value: L06 renames qwenloop_*.txt → sovereignloop_*.txt;
  L18d changes their first token when the binary becomes `sovereignloop`; L20b adds vscode*/vscode-paid*;
  L38c deletes opencode_*.txt. test_loop_events `_EXPECTED_MAPS`/`_TURN_BOUNDARIES` must gain/lose
  entries in the same lanes.
