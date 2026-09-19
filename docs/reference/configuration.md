# Configuration reference: `vibey.toml`

**Mostly not an active runtime input.** The schema below is fully implemented
and unit-tested in
[`src/vibey/domain/config.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/domain/config.py)
(`VibeyConfig`, `parse_config`, `parse_toml_string`) and
[`src/vibey/infrastructure/config_loader.py`](https://github.com/the-vibey-project/vibey/blob/main/src/vibey/infrastructure/config_loader.py)
(`load_config_from_path`), but `load_config_from_path` has no caller outside
its own unit test, so the full schema is never loaded at runtime — not by
`cli/`, `bootstrap.py`, the worker, or the Kubernetes operator. Treat this page
as a designed-and-tested schema, the same "implemented and tested, not yet an
active runtime path" status the README gives `infrastructure/notify/` and
`infrastructure/otel.py`.

## What is read at runtime today

| Input | Read by | What it controls |
|---|---|---|
| `./vibey.toml`, keys `[features].qwenloop`, `[features].claudeloop_local` and `[engines.claudeloop_local]` only | `vibey doctor` (`infrastructure/engines/local_engines.py` `LocalEngineSettings.from_toml`) | Which local engines are added to the health sweep, and the profile claudeloop-local is probed with. The file is read from the current directory with `parse_toml_string`, never validated by `parse_config`; a missing or malformed file counts as every switch off. Every other table on this page is ignored. |
| The project's stored record (the `project` row: `max_cycles` column and `config` JSON) | `vibey worker`, `vibey work` and every job handler | Cycle cap, per-cycle spend and turn caps, skills-context policy, REVIEW's [automated checks](#review), the [gate-command](#gates) timeout and environment isolation, and (in principle) the local-engine keys above — see below. |
| Environment variables | See [Environment variables](#environment-variables) | Database DSN, the local-engine switches and claudeloop-local's profile, the one local Ollama endpoint and model, the sovereign providers' timeout, and the sovereign DESIGN provider's evidence directory. |

The project record is written once, at creation, by one of two paths:

- **`vibey new`** (see the [CLI reference](cli.md)): `--max-cycles` is stored
  in the `project.max_cycles` column; `--max-cycle-dollars`,
  `--max-cycle-turns`, `--skills-context-mode` and `--skills-context-budget`
  are stored in the `config` JSON as `max_cycle_dollars`, `max_cycle_turns`
  and `skills_context` (the last only when the mode is not `off`).
- **The Kubernetes operator** ([ADR-0025](../architecture/decisions/0025-kubernetes-operator-crd-keda.md)):
  a `VibeyProject` spec's `maxCycles` sets the column (default `10`);
  `repo`, `maxCycleDollars`, `maxCycleTurns` and `skillsContext` are stored in
  the `config` JSON. `spec.engines` is stored as a flat `engines` list that
  nothing reads back yet.

Neither path passes through `parse_config`, and neither writes or reads a
`vibey.toml`. No command updates these values on an existing project.

Neither path writes a `features` key either, so the worker's check of the
stored `features.qwenloop` / `features.claudeloop_local` is always false for
projects created today: **`VIBEY_FEATURE_QWENLOOP` and
`VIBEY_FEATURE_CLAUDELOOP_LOCAL` are the switches that reach the worker.** All
three commands ask one resolver, `LocalEngineSettings`, so they cannot disagree
about which local engines exist ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md)).

## Environment variables

| Variable | Read by | Effect |
|---|---|---|
| `VIBEY_PG_URL` | `bootstrap.database_url()` (every command that opens the queue) | PostgreSQL DSN. Required; there is no default — `vibey` exits with `DatabaseNotConfigured` if it is unset. |
| `VIBEY_FEATURE_QWENLOOP` | `vibey worker`, `vibey work`, `vibey doctor` (all through `LocalEngineSettings`), and `load_config_from_path` | Overrides `features.qwenloop`. `1`, `true`, `yes`, `on` (case-insensitive, surrounding whitespace ignored) enable; any other value disables. When set it wins over both the stored project record and `./vibey.toml`. Only `load_config_from_path` rejects a non-boolean value. For the worker, enabling it adds a qwenloop adapter to the LOCAL tier, which BUILD selection prefers before any paid engine; for `work` and `worker`, any local engine switched on makes `qwenloop` the default `--provider`. |
| `VIBEY_FEATURE_CLAUDELOOP_LOCAL` | same | The same switch for `claudeloop-local` (`features.claudeloop_local`): the claudeloop binary on a local backend profile, in the LOCAL tier beside qwenloop. |
| `VIBEY_CLAUDELOOP_LOCAL_PROFILE` | `LocalEngineSettings` | Overrides `[engines.claudeloop_local].profile` when set and non-empty: the claudeloop `[profiles.NAME]` every claudeloop-local run and its `doctor` pass as `--profile NAME`. |
| `VIBEY_EVIDENCE_DIR` | `vibey work --provider qwenloop`, `vibey worker --provider qwenloop` (`QwenloopDesignProvider.from_environment`) | Directory of reading that the sovereign DESIGN provider's research stage draws from ([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)): `<topic>.md` or `<topic>.txt`, first line `source: <where it came from>`. Unset or empty, research refuses rather than inventing a source, and the research job parks a `research_evidence` human gate on its first attempt naming the file it wants; supply it and answer the gate to retry. |
| `VIBEY_OLLAMA_URL` | `vibey work` / `vibey worker` on the qwenloop provider (`OllamaChatClient.from_environment`), and the qwenloop engine (`LocalEndpointEnvironment`) | The one local endpoint setting, in root form. The sovereign DESIGN and DECOMPOSE providers talk to it; default `http://127.0.0.1:11434`; empty counts as unset. Anything but an `http`/`https` URL with a host is a `ConfigError` (exit 3). When set, the qwenloop engine's process also gets `QWENLOOP_BASE_URL=<url>/v1` unless that is already set, attaching qwenloop to this server; unset, qwenloop keeps its own backend selection. claudeloop-local reads its endpoint from its claudeloop profile's `base_url`. vibey-gh's local-review fallback reads the same variable. |
| `VIBEY_OLLAMA_MODEL` | same | The local model both sovereign providers use, and — with `VIBEY_OLLAMA_URL` set — qwenloop's `QWENLOOP_MODEL` unless that is already set. Default `qwen2.5-coder:14b`; `--ollama-model` on either command takes precedence. |
| `VIBEY_OLLAMA_TIMEOUT` | same | Seconds one local generation may take. Default `900`; anything but a positive whole number is a `ConfigError` (exit 3). |

## Schema semantics

`domain/config.py` is a pure, stdlib-only module with no filesystem access
of its own (reading the file is an infrastructure concern). Every table
below is optional; omit any of them and the listed defaults apply.

Validation is partial. The Type column is the intended shape. `parse_config`
type-checks every key except `[budget].*`, `[phases.*].engines` (not even
checked to be a list — a bare string is split into single-character engine
ids), `[phases.*].parallelism`, the elements of `[isolation].egress` and
`[provision].plugins`, and the values of `[engines].weights`; those are stored
as written. No numeric range is checked outside `[qwenloop]`
(`idle_timeout_seconds ≥ 0`, `startup_timeout_seconds > 0`,
`context_window > 0`), booleans pass integer checks (`max_cycles = true` is
accepted), and `[deploy].target` / `[deploy].iac` accept any string.

Engine names: an unknown engine name in `[engines].enabled` or as a key of
`[engines].weights` fails validation with a `ConfigError` naming the offending
path, as does `qwenloop` (or `claudeloop-local`) in `[engines].enabled` or any
`[phases.*].engines` list before `features.qwenloop` (or
`features.claudeloop_local`) is `true`. `[phases.*].engines` entries are
otherwise not validated — unknown names and engines outside
`[engines].enabled` are accepted as written — and `[engines].weights` may name
`qwenloop` without the feature flag. Unknown tables (for example
`[skills_context]`) are silently ignored. All of this applies only when
something calls `load_config_from_path`/`parse_config`, which nothing in this
codebase does outside tests.

## `[project]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | *required* | Project name. |
| `repo` | string | `"."` | Path to the repository this project builds against. |
| `max_cycles` | integer | `10` | Cap on delivery cycles. Not range-checked. The live value is the `project.max_cycles` column set by `vibey new --max-cycles` or `spec.maxCycles`. |
| `strict_loopback` | boolean | `false` | When true, tightens review-loopback routing ([ADR-0010](../architecture/decisions/0010-review-loopback-routing.md)). |

## `[isolation]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `level` | string | `"worktree"` | One of `worktree`, `container`, `vm`. |
| `allow_push` | boolean | `false` | Whether a worktree may push to a remote. |
| `egress` | array of strings | `[]` | Allowed egress destinations when network isolation is otherwise closed. Element types are not validated. |

`worktree` isolation is the one active runtime behavior today: every job
and phase runs in an isolated ephemeral git worktree. `container` and `vm`
are schema-valid values, and the container hardening path
(`infrastructure/container/config.py`'s `ContainerConfig`,
`infrastructure/container/runtime.py`'s `OciContainerExecutor`) is
implemented and unit-tested, but it is never constructed by `bootstrap.py`
or anything else outside `infrastructure/container/` and its tests, and
`[isolation]` itself is never read from a real `vibey.toml`. Setting
`level = "container"` has no effect today; see
[SECURITY.md](https://github.com/the-vibey-project/vibey/blob/main/SECURITY.md#1-worktree--container-isolation-runtime-adr-0008-task-91)
for the same disclosure.

## `[budget]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `max_dollars_per_cycle` | float or unset | unset (no cap) | Intended per-cycle spend cap. Not validated. |
| `max_dollars_total` | float or unset | unset (no cap) | Intended total spend cap across the project's lifetime. Not validated. |
| `max_turns_per_item` | integer or unset | unset (no cap) | Intended per-work-item turn cap; the implemented cap (`max_cycle_turns`) is per cycle. Not validated. |

None of these keys is read at runtime. The live brake is the project's stored
`max_cycle_dollars` / `max_cycle_turns` (set by `vibey new --max-cycle-dollars`
/ `--max-cycle-turns`, or the operator's `spec.maxCycleDollars` /
`spec.maxCycleTurns`). `LedgerBudgetSource` sums them live from the current
cycle's `TurnCompleted` and `BudgetSpent` ledger events — never estimated
ahead of time — and tripping either parks a `budget_exhausted` gate. With
neither set, spend is uncapped.

`vibey cost` prints caps from a `budget` key in the stored project config
(`max_dollars_per_cycle`, `max_dollars_total`) that nothing writes, so it
currently shows the fallbacks $40.00 (cycle) and $250.00 (total) rather than
the real cap.

## `[verify]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `require_independent_review` | bool | `false` | When `true`, `build.verify` always fails as `VIBEY` if the reviewing engine is the implementer, even when the configured pool has nobody else. When `false` (the default) a pool that cannot supply a second reviewer gets a self-review, recorded as a `DecisionRecorded` in the ledger so the weakened independence is visible. See [ADR-0035](../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md). |

Unlike `[budget]` above, this key **is** read at runtime, by
`bootstrap.build_full_worker`.

## `[engines]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | array of strings | `["claudeloop", "codexloop", "cursorloop", "agyloop"]` | Must be a subset of the known engines below. If omitted, every local engine whose feature is `true` (`qwenloop`, then `claudeloop-local`) is appended to the default automatically; an explicit list is never extended. |
| `weights` | table of string→int | `{}` | Per-engine weight for smooth weighted round robin ([ADR-0005](../architecture/decisions/0005-smooth-weighted-round-robin.md)). Keys must be known engines; values are not validated. |

Known engine ids: `claudeloop`, `codexloop`, `cursorloop`, `agyloop` (tier
PAID), and the local engines `qwenloop` and `claudeloop-local` (tier LOCAL; each
valid in `enabled` and `[phases.*].engines` only once its feature is `true`).
BUILD selection prefers the LOCAL tier and falls back to PAID only when no local
engine is eligible ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md)).

### `[engines.claudeloop_local]`

claudeloop-local's own settings. Read at runtime by `LocalEngineSettings` — from
`./vibey.toml` for `vibey doctor`, from the stored project record for the worker —
and validated there and by `parse_config` alike.

| Field | Type | Default | Notes |
|---|---|---|---|
| `profile` | string | `"local"` | The claudeloop `[profiles.NAME]` table (in `claudeloop.toml` or `~/.config/claudeloop/config.toml`) every run and `doctor` passes as `--profile NAME`. The profile, not vibey, carries the local server's `base_url` and model tiers. Must not be blank. `VIBEY_CLAUDELOOP_LOCAL_PROFILE` overrides it. |
| `context_window` | integer | `32768` | The descriptor's context window; keep it equal to the profile's `context_window` and the server's `OLLAMA_CONTEXT_LENGTH`. Must be a positive integer. |
| `structured_verdict` | boolean | `false` | Claim the STRUCTURED_VERDICT capability. Off by default; turned on, `vibey doctor --conformance` must see a `VerdictRendered` event from the configured model or the engine fails conformance and is not selected. |

Effort: every level passes `--profile NAME --preset low|medium|high` (never
`--effort`, which a local profile does not forward); HIGH and MAX run the `high`
preset and report `achieved = STANDARD`, the honest ceiling. Cost is 0/0. The
recipe is in the [local models guide](../guides/local-models-ollama.md).

## `[phases.design]`, `[phases.build]`, `[phases.review]`

Each phase table accepts the same three fields:

| Field | Type | Default (per phase) | Notes |
|---|---|---|---|
| `effort` | string | `design` = `high`, `build` = `low`, `review` = `high` | One of `trivial`, `low`, `standard`, `high`, `max`. |
| `engines` | array of strings or unset | unset (falls back to `[engines].enabled`) | Engine ids this phase may use. Not validated against known engines or `[engines].enabled`, and not checked to be a list. |
| `parallelism` | integer or unset | unset | Per-phase worker concurrency override. Not validated. |

```toml
[phases.build]
effort = "standard"
engines = ["claudeloop", "agyloop"]
parallelism = 4
```

## `[provision]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `plugins` | array of strings | `[]` | Reserved for agent-surface provisioning plugins ([ADR-0011](../architecture/decisions/0011-agent-surface-provisioning.md)). Parsed and stored only; `infrastructure/provision/agent_surface.py` does not read it today. |

## `[deploy]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `enabled` | boolean | `false` | Opts the project into the DEPLOY_DESIGN / DEPLOY_EXECUTE / DEPLOY_REVIEW stage set. |
| `target` | string | `"azure"` | Deployment target. Azure is the only implemented target today; other strings are accepted by `parse_config`. |
| `iac` | string | `"bicep"` | Infrastructure-as-code format used by the deploy adapters; other strings are accepted by `parse_config`. |

## `[features]`

| Field | Type | Default | Notes |
|---|---|---|---|
| `qwenloop` | boolean | `false` | Must be `true` before `qwenloop` can appear in `[engines].enabled` or any `[phases.*].engines` list. |
| `claudeloop_local` | boolean | `false` | The same for `claudeloop-local`. |

Runtime: `vibey doctor` reads these keys from `./vibey.toml`. `vibey worker` and
`vibey work` read them from the project's stored config record, which `vibey new`
and the operator never write, so for those two `VIBEY_FEATURE_QWENLOOP=1` /
`VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` are currently the way to switch them on. Each
environment variable overrides its key. With either local engine on, `vibey work`
and `vibey worker` default `--provider` to `qwenloop` (the sovereign DESIGN and
DECOMPOSE providers); an explicit `--provider` still wins.

## `[qwenloop]`

Only meaningful when `features.qwenloop = true`. In engine-driven BUILD
rotation qwenloop is in the LOCAL tier, preferred before any paid engine
([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md),
amending [ADR-0015](../architecture/decisions/0015-qwenloop-standby.md)'s
standby). It is also the sovereign DESIGN provider — the default `--provider`
once a local engine is switched on
([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)).
These keys mirror the runner's own `QwenConfig`
(`src/vibey_runners/qwen/src/qwenloop/domain/config.py`, which additionally
has `max_turns`, default `40`, must be positive); `parse_config` validates
them into `VibeyConfig`, but nothing passes them to the runner.

| Field | Type | Default | Notes |
|---|---|---|---|
| `backend` | string | `"auto"` | One of `auto`, `llama.cpp`, `vllm`. |
| `portable_profile` | string | `"qwen2.5-coder-14b-q5-k-m"` | Model profile used on the portable (CPU/quantized) backend path. |
| `nvidia_profile` | string | `"qwen2.5-coder-14b-bf16"` | Model profile used when an NVIDIA GPU backend is selected. |
| `idle_timeout_seconds` | integer | `900` | Must be non-negative; how long an idle local model stays warm. |
| `startup_timeout_seconds` | integer | `180` | Must be positive. |
| `context_window` | integer | `32768` | Must be positive. |

## Skills context (project config record — not a `vibey.toml` table) { #skills_context }

`VibeyConfig` has no `skills_context` field; a `[skills_context]` table in
`vibey.toml` is silently ignored by `parse_config`. The values live in the
project's stored config record and are written by
`vibey new --skills-context-mode` / `--skills-context-budget` (only when the
mode is not `off`; see the [CLI reference](cli.md#vibey-new-name)) or by the
operator's `spec.skillsContext` object (copied verbatim).
`compiler_from_config` (`infrastructure/skills_context.py`) reads them when
`bootstrap.build_full_worker` builds the worker ([ADR-0031](../architecture/decisions/0031-skills-context-packets-over-a-process-boundary.md)).

| Field | Type | Default | Notes |
|---|---|---|---|
| `mode` | string | `"off"` | `off`, `shadow` (measure only, never changes prompts), or `inject` (append successful packets to BUILD prompts). Any other value raises when the worker is built. |
| `budget` | integer | `6000` | Token budget for retrieval, 1,000–32,000 (enforced by the `vibey new` flag, the operator CRD, and `VibeySkillsContextCompiler`). |
| `timeout_seconds` | number | `120.0` | Skills compile timeout; must be positive. Settable only through `spec.skillsContext`. |
| `kill_grace_seconds` | number | `5` | How long to wait for a `vibey-skills` process that overran `timeout_seconds` (or whose compile was cancelled) to be reaped after its process group is killed with `SIGKILL`. It only runs out when a process that left the group still holds its output open; the worker then logs `skills_context_process_not_reaped` and moves on rather than wait on it, and a timed-out compile still falls back to the existing prompt ([#283](https://github.com/the-vibey-project/vibey/issues/283)). Must be a finite number greater than zero. Settable only through `spec.skillsContext`. |
| `command` | array of non-empty strings | unset (`<python> -m vibey_skills.cli`) | Override for the `vibey-skills` command. Read by `compiler_from_config` but not declared in the `VibeyProject` CRD schema, so neither creation path sets it today. |
| `index_path` | string | `.vibey/skills-context/index` under the repo | Path to the skills index; relative paths resolve under the repo. Read by `compiler_from_config` but not declared in the CRD schema, so neither creation path sets it today. |

## Automated review checks (project config record — not a `vibey.toml` table) { #review }

`VibeyConfig` has no `review` field; a `[review]` table in `vibey.toml` is
silently ignored by `parse_config`, and `vibey.toml` is never loaded by the
worker anyway. The values live in the project's stored config record under a
`review` object, and `SubprocessAutomatedReviewRunner.from_config`
(`infrastructure/build/automated_review_runner.py`) reads them when
`bootstrap.build_full_worker` builds the worker. They are the commands
`review.demo` shells out to: a non-zero exit becomes a `Severity.HIGH`
`security` finding or a `Severity.MEDIUM` `code_review` finding, which sends
REVIEW back to BUILD.

Neither `vibey new` nor the operator's `VibeyProject` spec writes this object
today, the same way `skills_context.command` and `skills_context.index_path`
are read but never written; the record is written directly. Until one of them
does, an unconfigured project runs REVIEW's code-review check and no security
check at all — which is what the empty `security_commands` default states
plainly, rather than running a scan that inspects nothing and reports success.
vibey's own `bandit -q -r src/vibey` is enforced for real as gate 6 of
`ci.yml`, on every pull request, independently of this.

| Field | Type | Default | Notes |
|---|---|---|---|
| `security_commands` | array of arrays of non-empty strings | `[]` (no security check runs) | Security checks. There is deliberately no default: any baked-in command names both a tool and a layout, and `bandit -q -r <path that does not exist>` exits 0 — a wrong default reports a passing security check that examined zero files. Configure this to get one. |
| `code_review_commands` | array of arrays of non-empty strings | `[["ruff", "check", ".", "--exclude", ".vibey", "--exclude", ".claudeloop", "--exclude", ".codexloop", "--exclude", ".cursorloop", "--exclude", ".agyloop"]]` | Code-review checks. The default excludes vibey's own machinery inside the repo — worktrees under `.vibey/` and the engines' state dirs — which are not the product. An explicit `[]` disables the check. |

A malformed `review` object (not an object, a command list that is not a list
of non-empty string arrays) raises when the worker is built, rather than
silently running nothing.

These commands run through the same gate runner as BUILD's, so they see the
environment described under [Gate commands](#gates): the default `ruff` has to
be installed where the project can reach it, not only inside vibey's venv.

## Gate commands (project config record — not a `vibey.toml` table) { #gates }

`VibeyConfig` has no `gates` field; a `[gates]` table in `vibey.toml` is
silently ignored by `parse_config`, and the worker never loads `vibey.toml`
anyway. The values live in the project's stored config record under a `gates`
object, and `SubprocessGateRunner.from_config`
(`infrastructure/build/gate_runner.py`) reads them when
`bootstrap.build_full_worker` builds the worker. That one runner executes every
gate command the worker runs: `build.verify`'s verification commands and its
`git diff`, `build.integrate`'s integration gates, and REVIEW's
[automated checks](#review).

Every gate command:

- runs with every `GIT_*` variable removed, always;
- runs, by default, with vibey's own Python environment removed —
  `VIRTUAL_ENV`, `VIRTUAL_ENV_PROMPT`, `PYTHONHOME`, `PYTHONPATH`, and the
  `PATH` entries under the active venv and under the running interpreter's
  prefix when that interpreter is a venv. It is the same isolation engine
  sessions get, so a gate's bare `pip install -e .` cannot land inside vibey's
  venv and its bare `python` or `pytest` never resolves to vibey's
  interpreter;
- reads `/dev/null` as stdin, so a command that prompts gets end-of-file
  instead of waiting;
- leads a process group of its own. When it overruns `timeout_seconds`, the
  whole group is killed with `SIGKILL` and the gate **fails with exit code
  124** and the message `gate command timed out after <N>s and was killed:
  <command>` — a failing gate for the repair loop, the way a command that
  cannot start fails with 127, not an error and not a wait. When the task
  running it is cancelled (Ctrl-C on the worker, event-loop shutdown), the
  group is killed the same way before the cancellation propagates;
- has output that is not valid UTF-8 decoded with replacement characters
  rather than raising.

Neither `vibey new` nor the operator's `VibeyProject` spec writes this object
today; like `review`, the record is written directly.

| Field | Type | Default | Notes |
|---|---|---|---|
| `timeout_seconds` | number | `1800` (30 minutes) | Per command, not per job; a project's whole test suite is usually one command. Must be a finite number greater than zero. |
| `kill_grace_seconds` | number | `5` | How long to wait for a killed command to be reaped. `SIGKILL` cannot be caught, so this only runs out when a process that left the command's group (a daemon in a session of its own) still holds its output open; the worker logs `gate_process_not_reaped` and moves on rather than wait on it. Must be a finite number greater than zero. The same kill-and-reap (`infrastructure/process/reaper.py`) bounds [`skills_context.kill_grace_seconds`](#skills_context) and the engines' preflight probes ([#283](https://github.com/the-vibey-project/vibey/issues/283)). |
| `isolate_python_env` | bool | `true` | `false` passes vibey's Python environment through to gate commands, as before [#212](https://github.com/the-vibey-project/vibey/issues/212) — for a project whose gates rely on tools installed beside vibey, such as the `ruff` and `bandit` of a development checkout's venv. `GIT_*` is stripped either way. |

`true` and `false` are rejected as timeouts rather than read as `1` and `0`.
A malformed `gates` object — not an object, a non-boolean
`isolate_python_env`, a timeout that is not a positive finite number — raises
when the worker is built.

## Full example

This is a valid file exercising most of the schema that `parse_config`
validates — not a file any command reads from disk (apart from `vibey doctor`
honouring its `[features].qwenloop`; see the top of this page).

```toml
[project]
name = "my-app"
repo = "."
max_cycles = 15

[isolation]
level = "container"
allow_push = false

[budget]
max_dollars_per_cycle = 15.0
max_dollars_total = 250.0

[engines]
enabled = ["claudeloop", "agyloop"]
weights = { claudeloop = 3, agyloop = 1 }

[phases.design]
effort = "high"

[phases.build]
effort = "low"
parallelism = 2

[phases.review]
effort = "high"

[deploy]
enabled = true
target = "azure"
iac = "bicep"

[features]
qwenloop = true

[qwenloop]
backend = "auto"
idle_timeout_seconds = 600
```
