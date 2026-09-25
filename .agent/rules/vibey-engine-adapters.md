# vibey-engine-adapters (Antigravity mirror of `.claude/skills/vibey-engine-adapters/SKILL.md`)

# vibey engine adapters

Vibey drives six autonomous session runners through seven engine ids:
`claudeloop`, `codexloop`, `cursorloop`, `agyloop` (tier PAID) and `opencode`
(the opencodeloop adapter; its descriptor says tier LOCAL, and canon 8.b repeals
it from both loops) make up the default pool, `DEFAULT_DESCRIPTORS`; two opt-in
local engines (tier LOCAL, `LOCAL_DESCRIPTORS`) join them: `qwenloop`
(`VIBEY_FEATURE_QWENLOOP` / `[features]
qwenloop`, ADR-0015) and `claudeloop-local` — the claudeloop binary run with a
local backend profile (`--profile NAME`), switched on by
`VIBEY_FEATURE_CLAUDELOOP_LOCAL` / `[features] claudeloop_local` (ADR-0038).
Under sub-doctrine 8.a local engines are **preferred first**: selection runs
SWRR within the LOCAL tier and falls back to PAID only when no local engine is
eligible. qwenloop's model is also the sovereign DESIGN/DECOMPOSE provider
(`qwenloop_design.py`, `qwenloop_decompose.py`, ADR-0027), the default
`--provider` whenever a local engine is switched on (ADR-0038). The runners' source lives in this
repository under `src/vibey_runners/{claude,codex,cursor,agy,qwen,common}`
(ADR-0021); vibey drives the installed binaries, not those packages' Python
APIs. Each has its own CLI surface, effort vocabulary,
state directory, and done marker. Vibey abstracts these differences via
`EngineAdapter`, a `Protocol` defined in `application/interfaces/engines.py`
and re-exported from `application/ports.py`.

## The adapter pattern

`EngineAdapter` (read the real definition before relying on this summary —
it's short):
- `descriptor: EngineDescriptor` — a property, the engine's static facts
- `async def preflight() -> PreflightResult` — runs `<engine> doctor`;
  classifies auth + availability
- `async def start(spec: RunSpec) -> RunHandle` — builds argv from
  `descriptor.effort_projection` + isolation flags, spawns the runner,
  returns a handle over its run directory
- `def tail(handle: RunHandle) -> AsyncIterator[EngineEvent]` — streams the
  runner's `events.jsonl`, translated into vibey's own event vocabulary
  through `loop_events.py::LOOP_EVENT_MAP`. Only the runner's own turn
  boundary maps to `TurnCompleted`, one per real turn, because the budget
  brake counts it; chatter and stream deltas that echo a turn's text map
  to `TranscriptRecorded`
- `async def send_prompt(handle, text, *, now: bool) -> None` — writes the
  runner's control-plane inbox
- `async def stop(handle: RunHandle) -> StopSummary` — soft-stops the run;
  collects `stop-summary.md` and the final snapshot
- `async def snapshot(handle: RunHandle) -> SnapshotRef | None`
- `def classify(raw: Mapping[str, object]) -> CapacityState` — maps a raw vendor
  error shape to `Available | WindowExhausted | CreditsExhausted | AuthenticationFailed`
- `def attribute(exit_code: int, tail: str) -> FailureClass` — attributes a dead
  process to a `FailureClass` (`capacity`, `engine`, `work`, `vibey`)

An engine session never inherits the worker's environment: every spawn (the run,
`--version`, `doctor`, `--help`) builds it through
`LoopProcessAdapter.environment`, an `EngineEnvironmentPolicy`
(`infrastructure/engines/engine_environment.py`) over the one builder,
`infrastructure/process/child_environment.py::ChildEnvironment`. It is an
allow-list: the system basics, the descriptor's `env_passthrough` and `auth_env`,
and the project's `engine_environment` additions, declared in vibey.toml's
`[engine_environment]` (copied into the record by `vibey new`) or the
`VibeyProject` spec's `engineEnvironment` — never hand-edited into the record.
`VIBEY_*`, `PG*` and anything DSN- or password-shaped can never be on it, so
`VIBEY_PG_URL` never reaches a model-driven process; a descriptor or overlay that
tries is refused when the adapter is built. The worker's startup preflight and
`vibey doctor --record` probe with the project's policy, so a declared credential
reaches the auth check too. A new engine declares what its runner and vendor CLI
read in `env_passthrough`; do not add a spawn path that passes `env=` itself.
vibey's own git calls (`infrastructure/git/clean_env.py`) and the `az` adapter
build their environments the same way, never from a copy.
`LoopProcessAdapter.env_overlay` is laid over that last (run and preflight alike) —
how qwenloop gets `QWENLOOP_BASE_URL`/`QWENLOOP_MODEL` from the one setting
`VIBEY_OLLAMA_URL` (`local_engines.py::LocalEndpointEnvironment`).
Preflight runs `<binary> doctor` plus `descriptor.doctor_args`
(claudeloop-local: `--profile NAME`).

Preflight's `--version` and `doctor` probes each lead a process group of their own.
On a timeout or a cancellation, `infrastructure/process/reaper.py::ProcessReaper`
kills the whole group and reaps it within `LoopProcessAdapter.kill_grace_seconds`,
logging `engine_process_not_reaped` if a descendant that left the group still holds
the pipes. The gate runner and the skills-context compiler use the same reaper.
Never hand-roll a kill followed by an unbounded `process.wait()` (#283, ADR-0017).
The run's environment strips the interpreter's prefix only when it is a venv
(`infrastructure/process/python_env.py::OrchestratorPythonEnv`, shared with the gate
runner), so a system-Python install keeps `/usr/bin`.

`start()` internally calls `infrastructure/engines/argv.py::build_argv()` —
that's a plain function, not an adapter method; it takes both the descriptor
and the `RunSpec` (`build_argv(descriptor, spec)`), not just the spec.

See `application/interfaces/engines.py::EngineAdapter` and
`infrastructure/engines/scripted.py::ScriptedEngine` (the fake runner used in
tests). `infrastructure/engines/loop_process_adapter.py::LoopProcessAdapter`
is the production adapter (it supersedes `ClaudeLoopProcess`): it spawns the
loop process, streams `events.jsonl`, detects `done_marker`, treats exit code 75
as wind-down, and classifies capacity through `classify.py` — one class driven
by descriptors, not one class per engine.

Engine choice for engine-driven BUILD jobs goes through
`SelectingEngineProvider → application/engine_selector.py::EngineSelector`
(SWRR over `domain/rotation.py`), wired in `bootstrap.py`. The selector builds a
candidate per eligible engine and `domain/rotation.py::preferred_tier` offers SWRR
only the first tier in `TIER_PREFERENCE` (LOCAL, PAID) holding a candidate that
can win. The provider passes its pool (adapters ∩ `--engines`) as the allow-list,
and refreshes every enabled local engine's health from its `doctor` before each
selection. Selection requires populated `engine_health` rows, so an engine with
no recorded conformance is never selected.

Before `build.implement` seeds a fresh run, it can ask the `vibey-skills` CLI for
a skills-context packet (`infrastructure/skills_context.py::VibeySkillsContextCompiler`,
modes `off`/`shadow`/`inject`, budget 1,000–32,000 with a 6,000 default;
ADR-0031). The packet is recorded as a `vibey_skills_context_packet` artifact.

## Engine descriptors

`infrastructure/engines/descriptors.py` defines `CLAUDELOOP`, `CODEXLOOP`,
`CURSORLOOP`, `AGYLOOP`, `OPENCODE`, `QWENLOOP`, `CLAUDELOOP_LOCAL` — one
`EngineDescriptor` per engine. claudeloop-local's is *built* from `[engines.claudeloop_local]`
(`profile`, `context_window`, `structured_verdict`) by
`ClaudeloopLocalDescriptors.build()`; the constant is the default profile `local`.
`DEFAULT_DESCRIPTORS` is the default pool of five, `LOCAL_DESCRIPTORS` the two
opt-in local ones, `ALL_DESCRIPTORS` all seven, and `BY_ENGINE_ID` maps every
`EngineId`. The worker
adds adapters for the local engines that are switched on through
`local_engines.py::LocalEngineSettings` — the one resolver bootstrap, `worker`,
`work` and `doctor` share.

Each descriptor (`domain/engine.py::EngineDescriptor`) declares:
- `engine_id`, `binary` — the executable name (e.g., `"claudeloop"`), `min_version`
- `state_dir` — where runs are stored (e.g., `".claudeloop/"`)
- `done_marker` — the text signaling completion (e.g., `"CLAUDELOOP_TASK_FULLY_COMPLETE"`)
- `capabilities` — which features it supports (`savepoints`, `unwind`, etc.). A
  claim must agree with the facts below (`test_descriptors.py`): `mid_run_prompt`
  exactly where `controls.prompt` is declared, `attachments` only where `images`
  or `paste_images` is proven `True`, `web_search` only where the runner's `run`
  takes `--web-search`
- `effort_projection` — how vibey's 5-level ladder (`TRIVIAL, LOW, STANDARD, HIGH, MAX`)
  maps to the engine's native flags
- `auth_env` — environment variables that must be set (empty for qwenloop)
- `env_passthrough` — the variables the engine's runner and vendor CLI read, passed
  to its sessions (a trailing `*` names a prefix); nothing else reaches a session
  unless the project declares it
- `session_verb`, `isolation_flags` (per `IsolationLevel`)
- `cost_per_mtok_in`/`cost_per_mtok_out`, `context_window`, `base_weight` (rotation weight)
- `tier` (`EngineTier.PAID` default, `LOCAL` for qwenloop and claudeloop-local) and
  `doctor_args` (extra `doctor` arguments; claudeloop-local: `--profile NAME`)
- `supports_cwd_flag` (default `True`; codexloop: `False`) and `plan_flag`
  (default `None` = positional plan path; cursorloop: `"--plan"`)
- `affordances` — `EngineAffordances`: `images`, `files`, `paste_text`,
  `paste_images`, `plugins` (`PluginSystem`) and `mcp`, each `True`, `False` or
  `None` (unknown, the default). `evidence` names, for every value that is set,
  where the runner's own code shows it; a set value without evidence fails a
  test. Never set one from memory or a vendor's marketing
- `controls` — `EngineControls`: `stop`, `wind_down` and `prompt` as argv
  templates after the binary (`{run_id}`, `{cwd}`, `{text}`), `None` where the
  runner has no such verb or does not act on it (cursorloop takes no mid-run
  prompt, though its CLI writes one). Tests read every template against
  the runner's own Typer app the way click parses it
- `events` — `EventLog`: the `path` template of its `events.jsonl` and its
  `envelope` (`EventEnvelope`: `type`, `event_type+payload`, or `event_type`)

**Effort projection example** (claudeloop, as in `descriptors.py`):

```python
effort_projection={
    Effort.TRIVIAL: EngineInvocation(("--preset", "low", "--effort", "low"), achieved=Effort.TRIVIAL),
    Effort.LOW: EngineInvocation(("--preset", "low", "--effort", "medium"), achieved=Effort.LOW),
    Effort.STANDARD: EngineInvocation(("--preset", "medium", "--effort", "high"), achieved=Effort.STANDARD),
    Effort.HIGH: EngineInvocation(("--preset", "high", "--effort", "high"), achieved=Effort.HIGH),
    Effort.MAX: EngineInvocation(("--preset", "high", "--effort", "max"), achieved=Effort.MAX),
}
```

qwenloop projects effort onto `--max-turns` (8, 16, 40, 64, 96).
claudeloop-local passes `--profile NAME --preset low|low|medium|high|high` and
never `--effort`; HIGH and MAX report `achieved=STANDARD`, its honest ceiling.

If an engine **saturates**, the descriptor sets `achieved` to the tier it
actually delivers. codexloop is the extreme case: its `run` has no effort flag,
so every level projects to empty argv with `achieved=Effort.STANDARD`.
`domain/rotation.py::fidelity_factor(descriptor, requested)` computes the
`Candidate.fidelity_factor` that scales the effective weight of engines that
saturate below the requested effort; `application/engine_selector.py` applies
it.

See ADR-0006 (normalized effort ladder).

## argv building

`infrastructure/engines/argv.py::build_argv(descriptor, spec)` takes an
`EngineDescriptor` and a `RunSpec` (fields: `run_id`, `worktree_path`,
`prompt`, `effort`, `isolation`, optional `session_id` to resume) and
produces the command line — read the real function, it is short. As of
2026-09-15 it emits, in order:

1. `<binary> run`, or `<binary> resume <session_id>` when `spec.session_id` is set.
2. For `run` only: the plan path `<worktree>/.vibey/plans/<run_id>.md`, prefixed
   by `descriptor.plan_flag` when the engine wants a flag (cursorloop: `--plan`),
   then `--run-id <run_id>` (so the adapter finds the run directory the process
   writes to).
3. `descriptor.invoke(effort).argv`.
4. `descriptor.isolation_flags.get(isolation, ())`.
5. `--cwd <worktree_path>`, only when `descriptor.supports_cwd_flag` (codexloop:
   `False`).

35 golden files under `tests/infrastructure/engines/golden/` (7 engines × 5
efforts; `test_argv.py` parametrizes over `ALL_DESCRIPTORS`) capture the
expected argv for each combination — the source of truth for the exact current
shape.

`argv.py::RUN_ARGV_TEMPLATE` (`RunArgvTemplate`) is `build_argv`'s `run` line with
its per-run values as placeholders: `{binary}`, `run`, `{plan_flag?}` (only with a
`plan_flag`), `{plan}`, `--run-id`, `{run_id}`, `{effort_argv...}`, and `--cwd
{cwd}` when `supports_cwd_flag`. It is what `vibey loops` publishes for a caller
that starts a runner itself, such as the VS Code extension. Tests compare it with
`build_argv` for every engine and effort, and read it, filled in at every effort
and isolation level, against the runner's own `run` definition.

## What `vibey loops` reports

`vibey loops [--json]` (`application/loops.py::LoopCatalog`, `cli/loops.py`) lists
the two loops of sub-doctrine 8.c, each engine under the loop its tier puts it in,
with every effort's argv, achieved effort and model, and the descriptor's run
template, `affordances`, `controls`, `events` and env names (names only). It reads
the local switches and qwenloop's model through `local_engines.py`, the resolvers
`vibey doctor` reads. An engine canon 8.b repeals (`REPEALED_FROM_LOOPS`) is listed
with `repealed: true` and left out of every by-effort view. The document for one
fixed environment is committed as `tests/cli/golden/vibey-loops.json`: after
changing a descriptor, regenerate it with
`VIBEY_UPDATE_GOLDENS=1 uv run pytest tests/cli/test_loops_cli.py -k golden` and
commit it with the change.

## Capacity classification

`infrastructure/engines/classify.py::classify_capacity(engine_id, raw)` dispatches
to one private classifier per engine (claudeloop-local shares claudeloop's) and
maps vendor-specific error shapes to vibey's `CapacityState`. claudeloop writes
its capacity as the class *name* (`"capacity": "CreditsExhausted"`); both that and
the `{"state": ...}` mapping are read, and `BackendMisconfigured` maps to
`AuthenticationFailed` (terminal, never credits). Exit 78 (EX_CONFIG,
`EXIT_CODE_BACKEND_MISCONFIGURED`) is attributed to ENGINE, and an incomplete run
that exited 78 parks its BUILD job on an `engine_misconfigured` gate
(`RunOutcome.misconfiguration_gate`) instead of retrying:

```python
Available | WindowExhausted | CreditsExhausted | AuthenticationFailed
```

**The critical distinction:** `WindowExhausted` has a `resets_at` deadline;
`CreditsExhausted` does not. A window exhaustion is waitable; credits
exhaustion requires a human top-up.

Each engine's classifier pattern is versioned in `CREDITS_FIXTURES`,
`WINDOW_FIXTURES`, `AUTH_FIXTURES`, and `AVAILABLE_FIXTURES` — shared between
the classifier's own tests and the conformance suite.

**Note:** these are synthesized fixture payloads, not captured real vendor
errors. If you get access to real `*loop` binaries or real captured error
payloads, this is the first thing to replace.

## The conformance suite

`application/conformance.py::run_conformance()` runs 9 named checks per
engine (grep the file for the check-name strings if this list drifts):
`binary` (installed + version), `flags` (`run --help` exposes what the
descriptor claims), `state_dir`, `run_dir_shape` (a real run produces
`meta.json`/`events.jsonl`/`snapshots/latest.json` — this one races a real
subprocess's own startup time, not just an instant file check; read the
function if you're touching it), `snapshot_schema`, `capacity_map`,
`done_marker`, `control_plane`, `structured_verdict`.

A failing conformance check marks that engine **ineligible** rather than
letting it fail mid-cycle.

```bash
vibey doctor --conformance --record
```

`--record` persists the preflight and conformance result to `engine_health`.
Without a recorded pass the worker warns and never selects the engine for
engine-driven jobs.

Live runs of the suite are split in two modes (ADR-0030): `tests/live/` with
`@pytest.mark.live` runs conformance and rotation against `ScriptedEngine`
and scripted stand-in binaries, with no model calls; `@pytest.mark.paid` spawns real binaries
against real models and is excluded by default.

See ADR-0001 (orchestrate, do not reimplement).

## When to read this skill

Before:
- Adding a new engine.
- Changing effort mappings.
- Changing what an engine declares it can take, control or emit (`affordances`,
  `controls`, `events`), or anything `vibey loops` reports.
- Debugging why rotation is skipping an engine.
- Updating capacity classification patterns after a vendor API change.
