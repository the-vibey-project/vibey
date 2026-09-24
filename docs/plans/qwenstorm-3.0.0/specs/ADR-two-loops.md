# 0046 — Two loops: sovereignloop and paidloop, each holding adapters, rotated in two layers that both run on queues

**Status:** proposed · **Date:** 2026-09-22 · **Amends:** ADR-0005 (where the round robin runs and where its cursor lives in service mode), ADR-0015 (the name `qwenloop`), ADR-0038 (the two tiers become the two loops, and a paid fallback is declared), ADR-0042 (its engines row: OpenCode is repealed and VS Code joins both loops), ADR-0044 (§2's run topology, §13's one service per engine, its supersede design, and §15's loop-service chart) · **Cites:** sub-doctrines 8.a, 8.b, 8.c, 8.d, 12.c, 10.e; also 9.b, 9.c, 10.f · **Related:** ADR-0003, ADR-0004, ADR-0007, ADR-0016, ADR-0020, ADR-0022, ADR-0024, ADR-0027, ADR-0035, ADR-0037, ADR-0045 · **Evidence:** the storm integration tree `STORM/integration` at `391673c2` (`develop` plus the verified storm lanes), read 2026-09-22. Every `file:line` is at that commit unless it names a storm spec (`specs/…`). A storm spec is a specification, not code: lanes R01–R34 of `specs/rabbitmq-lanes.md` are unmerged at this cutoff.

**Owes:**

1. **Two canon amendments, drafted below under *Canon amendments owed*.** They amend 8.b's engines bullet and 8.c's census of loops. Under Article II.3 and ADR-0020 they are ratified only by the operator's merge. Until that merge, 8.c's ratified text lists six loops, so the lanes that build exactly two must not merge before it.
2. **The VS Code verification** (V-VS1 to V-VS5 under *Verification owed*). It must be recorded before lane L20 starts.
3. **The docs wave:**
   - ADR-0015, ADR-0038, ADR-0042 and ADR-0044 each get a status note;
   - `docs/plans/rotation-and-engines.md`, `docs/plans/architecture-and-roadmap.md` §4 and §7, `docs/reference/configuration.md` and `docs/reference/cli.md`;
   - `docs/guides/local-models-ollama.md`, and the example files `docs/examples/qwenloop-local.toml` and `qwenloop-storm.env.example`, which get new names;
   - the paper's rotation and validation sections;
   - the "Engines" and "Rotation" facts and the tenant list in CLAUDE.md, AGENTS.md and GEMINI.md;
   - the four agent-surface trees;
   - the advertised ADR count (`tests/meta/test_adr_counts.py`).

## Context

### The operator's decisions (2026-09-22)

The coordinator relayed these decisions on the operator's channel. They are design inputs. They become law only through the ratifying merge (SD-01 §4, Article II.3).

1. **There are exactly two loops.** `qwenloop` is renamed **sovereignloop**. The paid loops `claudeloop`, `codexloop`, `cursorloop` and `agyloop` are combined into **paidloop**. Each loop holds **adapters** for the models and tools it drives.
2. **Rotation has two layers.**
   - The outer layer chooses between sovereign and paid, and prefers sovereignloop by default (8.a). Paid is never prioritized. It is used only when sovereign cannot carry the work, or where a human has declared a paid relay (8.b).
   - The inner layer is each loop's own smooth weighted round robin (ADR-0005) across its adapters and models.
3. **Both layers run on RabbitMQ queue logic.** That means the bus, dead-letter queues and idempotency, both from vibey to the chosen loop's queue and from the loop to its adapter or model queues. 8.c (one instance per loop, fed by a queue) applies to each loop.
4. **The default model is GPT-OSS 20B served by Ollama.** This is the 8.d designation (PR #390, `specs/default-model-p1.md`). Where that model does not fit the machine, the RAM-tier default applies.
5. **Mid-design change: OpenCode is replaced by VS Code.**
   - OpenCode is repealed as a named engine in both loops.
   - sovereignloop drives VS Code's open-source build (Code - OSS, as VSCodium ships it) with a local model.
   - paidloop's adapters are `claudeloop` (the default), `codexloop`, `cursorloop`, `agyloop`, and VS Code on a paid provider.
   - The opencodeloop runner (#314, `src/vibey_runners/opencode`) is retired. A VS Code adapter replaces it, and a migration lane removes it once that adapter lands.
   - The opencodeloop parity lanes are **dropped**: #328 (`specs/opencodeloop-parity-p1.md`) and #329 (`specs/opencodeloop-parity-p2.md`). Their runner rules carry into the VS Code runner (§8).

### Rotation already has two layers, inside one process

`EngineSelector.select_engine` (`src/vibey/application/engine_selector.py:102-226`) gathers every eligible engine for the project. It then calls `select(preferred_tier(candidates))` (`:212`).

- `preferred_tier` (`src/vibey/domain/rotation.py:89-110`) returns the candidates of the first tier in `TIER_PREFERENCE = (LOCAL, PAID)` (`src/vibey/domain/engine.py:51`) that holds a candidate of positive weight.
- `select` (`rotation.py:161-185`) is nginx's smooth weighted round robin.

So the outer layer (a sovereign-first preference) and the inner layer (SWRR within a tier) already exist as policy. Four things are missing:

- a loop as a unit that owns its inner rotation;
- queues at either layer;
- any notion of which model is loaded;
- a declaration when paid is chosen. ADR-0038 records this last gap as its first *Bad* consequence.

### ADR-0044 runs one service per engine

ADR-0044 §13 and its §2 topology give each of the seven engine ids its own queue `vibey.runs.<engine_id>` and its own `vibey loop-service --engine <id>`. That is seven loops. Lanes R19–R28 of `specs/rabbitmq-lanes.md` specify them, and R30 charts them. None of them is merged.

Designing two loops turned up two defects in §13, recorded here so that the replacement closes them (10.f).

- **Supersede cannot fire at the default prefetch.** R22 rule 3g (`specs/rabbitmq-lanes.md:2606-2611`) stops an orphaned lower attempt only when the successor is *delivered* while the orphan runs. R01's default prefetch is 1 (`:172`), and the host holds the running request's delivery unacknowledged (`:2588-2589`). So the successor is not delivered until the orphan finishes. "Worktree busy" and supersede fire only after a channel blip. In steady state an orphan runs to its own deadline while its successor waits.
- **The worktree guard is per service instance.** §13's rule "no two runs ever share one worktree" is checked against "an active run on the same `cwd`" in the same instance (ADR-0044:448-457). Suppose attempt *n* ran on engine A and the worker died, and attempt *n*+1 then rotated to engine B. B's service does not know about A's run, so the two can edit one worktree together. Two loops keep this hole open, because a job can move from one loop to the other.

### Residency is a hard constraint on a laptop

8.c was learned by measurement (`src/vibey_tools/gh/docs/doctrines.md:188-194`): three qwenloop sessions sharing one model server overflowed its context, and all three timed out. The model sizes behind the default decision:

| model | memory | context | source |
|---|---|---|---|
| GPT-OSS 20B on Ollama | 13.1 GB | 131k | `specs/default-model-p1.md` |
| qwenloop's managed llama.cpp server | 16 GB, started beside a running Ollama | — | `specs/default-model-p2.md` |

A 24 GB machine therefore holds one model at a time. An inner rotation that changed model on every job would thrash: each switch unloads and reloads 13–16 GB.

### The names the rename touches

| surface | where today |
|---|---|
| tenant | `src/vibey_runners/qwen` (`pyproject.toml:6`, script `:38`) |
| root console scripts | `pyproject.toml:69-76` |
| root packages | `pyproject.toml:200-207`, `:227-232` |
| container image | `deploy/docker/Dockerfile:142` |
| CI | tenant matrix `.github/workflows/ci.yml:531-543`; console-script contract `:827` |
| engine id | `EngineId.QWENLOOP = "qwenloop"` (`src/vibey/domain/engine.py:32`) |
| descriptor | binary, `.qwenloop` state directory, `QWENLOOP_TASK_FULLY_COMPLETE` marker (`src/vibey/infrastructure/engines/descriptors.py:290-316`) |
| config | `DEFAULT_ENGINES`, `LOCAL_ENGINE_FEATURES`, `KNOWN_ENGINES` (`src/vibey/domain/config.py:21-33`); `[features] qwenloop` (`:174-181`); the `[qwenloop]` table (`:184-191`, `:505-530`) |
| engine switch | `VIBEY_FEATURE_QWENLOOP`, built by `LocalEngineSwitch.env_var` (`src/vibey/infrastructure/engines/local_engines.py:48-57`) |
| endpoint overlay | `QWENLOOP_BASE_URL` / `QWENLOOP_MODEL` (`local_engines.py:43-45`, `:180-188`) |
| tenant settings | its own environment names (`src/vibey_runners/qwen/src/qwenloop/infrastructure/settings.py:15-22`); config path (`:44`); model cache (`model_cache.py:25`, `inference.py:48`); run directory (`run_store.py:11`; `cli/app.py:548`, `:557`, `:575`); done marker (`domain/model.py:9`) |
| CLI | `--provider qwenloop` (`src/vibey/cli/main.py:365`, `:389`) |
| CRD | engine enum (`deploy/helm/vibey/templates/crd-vibeyproject.yaml:78`), bound to `EngineId` by `tests/meta/test_crd_engine_enum.py:21-24` |
| chart | `ollama.qwenloopFeature` (`values.yaml:186-190`); the `QWENLOOP_*` worker environment (`templates/worker.yaml:105-114`); the golden profile `ollama-gpu-qwenloop` (`golden/render.sh:82-85`) |

### Stored engine ids are forward-compatible, and the ledger chain hashes their text

Readers are forward-compatible and writers are strict (`src/vibey/domain/stored_value.py:10-24`, vibey#275 and #287). An unknown stored id reads as `UnrecognizedEngineId` with its text kept verbatim (`engine.py:54-76`).

Each ledger chain link covers the event's engine text (`src/vibey/domain/ledger_chain.py:5-6`), and `event` is append-only by rule (`migrations/0002_event.sql:27-28`). So a stored `qwenloop` must read back as `qwenloop` byte for byte, forever. Any alias may act only where a consumer *acts* on an id. It may never apply where the text is *preserved*.

No ADR records the #275/#287 rule. It lives only in the code cited above (flagged under *Evidence flags*).

### OpenCode's tier was a claim about the binary's location, not the model's

ADR-0042 put the `opencode` descriptor in the LOCAL tier (`descriptors.py:287`). Yet its doctor proves only that "at least one provider credential" is saved (`src/vibey_runners/opencode/src/opencodeloop/infrastructure/opencode_process.py:43-96`), and its run passes no model at all (`:99-125`). A LOCAL `opencode` could therefore run a paid model. The operator's repeal makes this moot going forward. The general lesson is kept as a rule in §1.

## Decision

### 1. Exactly two loops; every runner is an adapter of one of them

| loop (`LoopId`) | adapters (engine ids) | posture | a *seat* (inner queue) is | capacity |
|---|---|---|---|---|
| `sovereignloop` | `sovereignloop` (the native agent, the former qwenloop); `vscode` (Code - OSS, as VSCodium ships it, on a local model); `opencode` (transitional and **declared-only** until L38, §9 — never always-on: 8.b repealed it) | always on, never needs declaration (8.b) | a **model** | one run at a time by default (8.c) |
| `paidloop` | `claudeloop` (**the default adapter**); `codexloop`, `cursorloop`, `agyloop`, `vscode-paid`, `claudeloop-local` (Claude Code on a local model: the tool is not free, §9) | declared only (8.b) | an **adapter** | a per-seat prefetch, default 1 |

- **The engine id stays the adapter's identity.** The health row, circuit, cost, rotation cursor and ledger attribution are all keyed by `EngineId`, exactly as today. No column changes.
- **A new `LoopId` vocabulary** holds `sovereignloop` and `paidloop`, with a forward-compatible parser.
- **Loop membership is derived, not declared a second time.** It comes from the descriptor's tier (`LOCAL → sovereignloop`, `PAID → paidloop`), so there is only one classification to keep true.
- **Sovereignty follows the model and the tool (rule).** A sovereignloop adapter is a free, open-source harness that drives a model on the operator's own hardware, with no account and no subscription. The same harness pointed at a paid provider is a different adapter, in paidloop, and must be declared. VS Code is the first harness split this way (`vscode` and `vscode-paid`, §8).
- **A runner the family adds joins one of the two loops as an adapter. It is never a third loop.** This is part of the 8.c amendment.
- **claudeloop is paidloop's default adapter.** Writing `paidloop` in `[engines].enabled` or `--engines` declares paidloop with `claudeloop` alone. The other paid adapters join only when they are named. In paidloop's round robin, `claudeloop` has order 0, so it wins ties. All base weights stay 1, as ADR-0038 set them.

### 2. Two rotation layers

**Outer layer: vibey, at job boundaries (ADR-0007).**

- `LOOP_PREFERENCE = (sovereignloop, paidloop)`. This is a deterministic preference, not a round robin.
- `LoopSelector` reads the same health rows and applies the same eligibility and weights as today. Those come from `EngineSelector.weighted_candidates`, which is extracted from `select_engine` unchanged. It chooses the first loop that holds a candidate of positive weight.
- paidloop is considered only when the worker's pool contains a declared paid adapter.
- Whenever the choice is paidloop, vibey writes a `PaidFallbackDeclared` ledger event. It names every sovereign adapter in the pool and why that adapter could not take the job. The possible reasons are: no health row, not installed, conformance failed, authentication stale, circuit open (with its capacity state), excluded by the job, missing capability, or unroutable (§4).
- The event is written in both invocation modes. This closes ADR-0038's *Bad* point "the paid fallback is not yet declared" (8.a: "declared loudly to a human").
- **There is no affinity across loops.** If the sovereign loop has recovered, it wins the next boundary even when a paid adapter holds a warm session. 8.a outranks ADR-0005's affinity factor, which now applies only inside a loop.

**Inner layer: the loop.**

- SWRR (ADR-0005's `select`) runs over the candidates vibey sends. Each candidate is an engine id with its effective weight. The loop keeps its own cursors.
- For sovereignloop, the residency choice comes first (§4).
- **The loop never reads `engine_health` and never classifies capacity.** The caller does both, as ADR-0044 §13 already requires ("the service never classifies capacity").
- The inner "circuit break" is therefore *written* by the caller that classified the signal and *enforced* by the loop, which offers the adapter no rounds. Capacity never crosses the wire.
- The loop needs only the broker and the shared volume, which keeps R27's property.
- The loop's cursors persist, per project, in its own state directory (§10). In service mode, `rotation_cursor` no longer holds the inner state.

**Subprocess invocation (kept, 12.c).** The same two layers run in process: `preferred_tier` then `select`, unchanged, plus the fallback declaration. There are no queues and no residency. The "both layers on queues" rule binds service mode, and service mode becomes the default when R34 flips it.

### 3. Both layers on RabbitMQ

Every name takes the `[bus] prefix` (default `vibey`) and lives in the `[bus] vhost` (ADR-0044 §2). This table replaces ADR-0044 §2's per-engine run rows.

| object | type | arguments and bindings | layer |
|---|---|---|---|
| `vibey.runs` | direct exchange | keys `<loop>`, `<loop>.<seat>`, `<loop>.probe` | both |
| `vibey.runs.<loop>` | quorum queue | key `<loop>`; `x-delivery-limit` 3; DLX `vibey.runs.dlx` with key `<loop>`; `x-dead-letter-strategy=at-least-once`; `x-overflow=reject-publish`; `x-consumer-timeout`; **consumed exclusively** | outer: the loop's intake |
| `vibey.runs.<loop>.<seat>` | quorum queue | key `<loop>.<seat>`; the same arguments; DLX key `<loop>.<seat>` | inner: one per seat |
| `vibey.runs.<loop>.probe` | classic queue | key `<loop>.probe` | preflight probes |
| `vibey.runs.dlx` | direct exchange | — | poison routing |
| `vibey.runs.<loop>.dead`, `vibey.runs.<loop>.<seat>.dead` | quorum queues | bound on the DLX | dead letters, each answered `DEAD_LETTERED` |
| `vibey.runs.control` | topic exchange | each loop binds `<loop>` and `all` | stop, wind-down, prompts; `SUPERSEDE` broadcast |

- **Seat names.** A paid seat is the engine id. A sovereign seat is the model's slug: lower case, and every character outside `[a-z0-9-]` becomes `-`, so `gpt-oss:20b` becomes `gpt-oss-20b`. `probe` and `dead` are reserved. Two models that map to one slug are a configuration error.
- **8.c is enforced by the broker, per model.** 8.c as amended in #392 makes the unit "a single instance per model", and a seat is a model: for sovereignloop the local model's slug; for paidloop the adapter's model, named `<engine-id>` while an adapter drives one model and `<engine-id>.<model-slug>` once it drives several. Every seat queue is consumed by exactly one **seat host** with an *exclusive* consumer, so a second instance for the same model is refused at the broker and exits with an 8.c message. Each loop's **router** consumes its intake queue exclusively too; it only routes and forwards, so one router per loop is not a second instance of any model. Each loop declares its intake queue and the queues of its seats.
- **Throughput per model is capacity, never a copy.** A seat's prefetch (`[loop_services.<loop>] capacity`) is how one model takes more work at once; nothing runs a second host for the same model. On a laptop the router and the resident seat's host share one process (§4 keeps one model resident); in a cluster each model's seat host may run on its own (§11).

**Messages.** These are pure dataclasses with a strict codec (`domain/run_protocol.py`). The codec refuses any extra key. In particular it refuses `resets_at`, `capacity`, `capacity_state`, `credits`, `complete` and `success`.

| schema | direction | purpose |
|---|---|---|
| `vibey.run.route/1` | caller → `<loop>` | a route request: `route_id`, `loop_id`, `project_id?`, `candidates [{engine_id, weight}]`, `pin?`, `model_pin?`, `min_context?`, `requested_at`, `caller` |
| `vibey.run.routed/1` | loop → `reply_to` | `route_id`, `loop_id`, `engine_id`, `seat`, `model?`, `switched`, `reason` |
| `vibey.run.request/1` | caller → `<loop>`; the loop forwards it → `<loop>.<seat>` | ADR-0044's run request plus `loop_id`, `engine_id` and `route_id?` |
| `vibey.run.accepted/1` | loop → `reply_to` | adds `engine_id` and `model` |
| `vibey.run.progress/1`, `vibey.run.result/1` | loop → `reply_to` | as in ADR-0044. `RunStatus` gains `UNROUTABLE` |
| `vibey.run.control/1` | caller → control exchange | adds the `SUPERSEDE` command, carrying `supersedes {key, attempt}` |

**Flow for a BUILD job.**

1. `select_for` makes the outer decision.
2. It publishes a route request to `<loop>` and awaits `RunRouted`, bounded by `route_wait_seconds`.
3. It records the selection, assigns the routed engine to the job, and writes `LoopRouted`.
4. It returns an adapter bound to that engine.
5. The handler's `start` publishes the run request to `<loop>`.
6. The loop's router looks up the stored route and forwards the request, unchanged, to `<loop>.<seat>`.
7. The seat host runs it.

Because of this order, `EngineAdapter.descriptor` is known before `start`, exactly as `build_implement_handler.py:185` needs today.

**Pinned runs send one message.** These are DESIGN and DECOMPOSE through the command executor, and `vibey loop submit --engine`. The router routes the run request itself, with the pin, and forwards it.

**Idempotency at both layers.**

| what | key | enforced by |
|---|---|---|
| a route (outer layer) | `route_id` = AMQP `message_id` | `RouteStore` creates the record once. A redelivered route re-sends the stored `RunRouted` and never advances SWRR twice |
| a forward (inner layer) | `run_id` = `message_id` | The router forwards a run only to the seat of its stored route, so a redelivered intake message lands in the same seat queue |
| a run | `run_id` | The seat host's ADR-0044 rules: an active run is rebound, a persisted result is re-sent, a non-terminal run directory is abandoned |
| run ownership | `supersedes {key: job_id, attempt}` | The worktree fence (§6), across both loops |
| dead letters | `x-delivery-limit` at each layer | Dead queues are answered `DEAD_LETTERED`; the caller fails the attempt, and ADR-0024 parks |

### 4. sovereignloop's inner layer is residency-aware

**Seats are models.** At routing time, `ResidencyPolicy` chooses the model and then SWRR chooses the adapter. The model is chosen in this order:

1. the **resident** model, if it can carry the job (a pin that matches, and at least `min_context`);
2. otherwise the machine's **default** model, if it can: the 8.d designation `gpt-oss:20b` on Ollama, or the catalogue's RAM-tier default where that does not fit;
3. otherwise the first declared model that can;
4. otherwise the route is `UNROUTABLE` with "no local model can carry this job", and the outer layer tries paidloop, if one is declared, with that reason.

Then SWRR runs over the adapters that can drive the chosen model:

- `sovereignloop` (native) and `vscode` can drive any declared model the runtime serves;
- `claudeloop-local` is no longer here: it is a paidloop adapter (§9).

**Execution consumes only the resident seat**, with prefetch equal to `[loop_services.sovereignloop] capacity`, which defaults to 1. `ResidencySchedule` decides a switch, and only between runs. It switches when:

- the resident seat is empty and another seat has work; or
- another seat's oldest request has waited at least `residency_max_wait_seconds` (default 900), and at least `residency_min_hold_runs` runs (default 1) have finished since the last switch. This is the starvation bound: a request waits at most that long plus one run's deadline.

**On a switch** the loop cancels its consumer on the old seat. If `unload_on_switch` is set (the default), it unloads the old model through the runtime: Ollama `keep_alive: 0`. It then consumes the new seat. The first run on the new seat loads the new model. vibey never has two models loaded at once.

**Backlog.** The depth of each seat comes from a passive queue declare, added to the family client (10.e, lane L21). The age of a seat's oldest request comes from the router's in-memory first-seen times. After a restart, age is counted from the restart.

**Probes never thrash.**

- A probe that would load a model runs only when that model is resident. An example is `claudeloop doctor --profile`'s tool-call check.
- Otherwise the probe is answered from its last real result, marked cached with its time. It is never a fabricated pass.
- The first probe ever for a model always runs.

**Flag.** The DESIGN and DECOMPOSE providers call Ollama directly (ADR-0027). They share the resident model only when they use the default model. An explicit different `VIBEY_OLLAMA_MODEL` makes them contend with it. Routing them through sovereignloop is a follow-up and is not in this set.

### 5. Capacity signals in the two-layer model

| signal | classified by | recorded in | inner effect | outer effect |
|---|---|---|---|---|
| `CreditsExhausted` | the caller: `classify.py` for the routed engine | `engine_health` OPEN, with `probe_next_at` backoff; **never** `resets_at` (the CHECK constraint) | the engine gets no candidate weight, so its loop rotates to another adapter | a loop with no candidate is passed over. On a sovereign adapter it cannot happen: a local backend has no credits (`_classify_qwenloop`, `classify.py:150`). With paidloop exhausted too, the next decision starts at sovereignloop again, else `CapacityDeferred` at the probe interval |
| `WindowExhausted` (including a local `busy`) | the caller | OPEN, with the window's own `resets_at` | as above | as above |
| `AuthenticationFailed` | the caller | OPEN with no time, until a preflight whose authentication succeeds | as above | as above |
| `UNROUTABLE` (the loop has no model, or no pinned adapter) | the loop, as a routing fact, not a capacity state | nothing | — | the outer layer decides again with that loop excluded, for this selection only |
| queue saturation (no `RunAccepted` by `start_by`) | the adapter | nothing | — | `EngineQueueSaturated` becomes `Defer(capacity=False)`. No circuit opens, no attempt is spent, and it **never** triggers a paid fallback: busy is not "cannot carry" (8.a) |
| `DEAD_LETTERED` | the loop | — | — | a failed attempt; ADR-0024 parks it when the ladder ends |
| exit 75 (wind-down) | the caller | handoff (ADR-0004), unchanged | the next engine comes through both layers, with the wound-down adapter excluded | — |

**There is no fallback from paid to sovereign.** Sovereign is re-tried *first* at every decision. That is 8.a's default, not a fallback. The only fallback there is runs from sovereign to paid. It happens only to a declared paid adapter, only when sovereign provably cannot take the job, and always with the reason written in the ledger.

### 6. The worktree fence closes §13's supersede holes, across both loops

Each worktree holds two files on the shared volume.

- **`<cwd>/.vibey/run.lock`** is created with `O_EXCL`. It records the holder: `run_id`, `key`, `attempt`, `loop_id`, `instance`, `run_dir`, `started_at` and `deadline_at`.
- **`<cwd>/.vibey/supersede.json`** records a high-water attempt for each supersede key.

The seat host acquires the lock before it starts a run, and releases it after the result is persisted. The outcomes:

- **The request's attempt is below the key's high-water mark.** Reply `SUPERSEDED` and do not run.
- **The same key is held with a lower attempt.** Write `stop` into the holder's own inbox. The inbox is a file on the shared volume, so this works from either loop. Then reply `REJECTED` with "worktree busy: superseding <run_id>". The caller defers (`capacity=False`) and retries after the holder releases.
- **Another key is held.** Reply `REJECTED` with "worktree busy".
- **The lock is past `deadline_at + stale_after_seconds`.** It is stale: rename it aside, log it, and acquire.
- **The same `run_id` holds it.** This is a redelivery: acquire again.

The router also honours a `SUPERSEDE` control broadcast by stopping any lower attempt it holds. The fence is what makes supersede correct whatever the delivery timing.

### 7. The rename, with aliases that never touch stored text

- **In code, `EngineId.SOVEREIGNLOOP = "sovereignloop"` replaces `QWENLOOP`.** During the rename wave, `QWENLOOP` stays a Python enum alias of the same member, and L09 removes it. `EngineId("qwenloop")` resolves to `SOVEREIGNLOOP` through `_missing_`.
- **`ENGINE_ID_ALIASES = {"qwenloop": EngineId.SOVEREIGNLOOP}`.** `StoredValueParser.known()`, which *acting* consumers use, resolves aliases. This keeps an in-flight verify job's `implementer_engine_id: "qwenloop"` excluding its successor. `parse()`, which *preserving* readers use, never resolves them: a stored `qwenloop` reads as `UnrecognizedEngineId("qwenloop")` with its text intact, so the ledger chain verifies.
- **Health and cursor rows are not migrated.** The selector skips a legacy `qwenloop` row (it has no descriptor), and the first preflight writes the `sovereignloop` row. Writers write only canonical ids.
- **The CRD engine enum** holds every member plus every alias key, and the binding test is changed to say so.
- The rest of the aliases, and how long each lasts, are listed under *Migration*.

### 8. VS Code in both loops

**A new runner tenant, `vscodeloop`** (`src/vibey_runners/vscode`, own gates per ADR-0022), follows the family contract:

- the verbs `run`, `resume`, `doctor`, `prompt` and `stop`;
- run directories at `.vscodeloop/runs/<run_id>/`, each with `events.jsonl`, `meta.json`, a control inbox and `stop-summary.md`;
- the done marker `VSCODELOOP_TASK_FULLY_COMPLETE`, added through the family's `with_done_marker_instruction`;
- exit codes 0, 1, 75 (wind-down) and 78 (misconfigured).

Its bounds (turns, seconds, stall) and its one pure terminal-status rule are the ones the dropped `specs/opencodeloop-parity-p1.md` specified. The first check of that rule is "a capacity rejection gives `FAILED`", ahead of any completion claim.

**Two engine ids share the one runner:**

- **`vscode`** (LOCAL, so sovereignloop). The runner writes per-run editor settings that pin one local OpenAI-compatible provider at `VIBEY_OLLAMA_URL`, serving the routed model. Its doctor refuses a provider host that is not loopback, private or cluster-local. It also refuses an editor build that is not Code - OSS, judged by the editor's `product.json` (verification owed). The editor binary is `VSCODELOOP_EDITOR`, default `codium`.
- **`vscode-paid`** (PAID, so paidloop). It is declared-only, and needs `[engines.vscode_paid] provider` and `model`.

**The editor driver sits behind a port.** Lane L20, the Code - OSS driver, is **gated** on the recorded verification V-VS1 to V-VS5. At this cutoff no evidence exists of a headless, account-free way to drive an agent session in Code - OSS. If the verification diverges, the divergence stays bounded (CDD, 9.c):

- `vscode` stays off;
- opencodeloop is not removed;
- the operator decides.

**No VS Code DESIGN provider is planned.** `--provider opencode` is refused once L38 lands, with a message that names `sovereignloop`.

### 9. OpenCode is retired; claudeloop-local moves to paidloop

- **Until L38, `opencode` stays a sovereignloop adapter only when a project declares it,** with a warning that 8.b repealed it (#392). It is never always-on and never in a default pool; the runner keeps working only so a declared project is not stranded before `vscode` carries its work. The parity lanes #328 and #329 are closed.
- **L38 runs only after `vscode` passes the live conformance suite.** It then:
  - retires the engine id: a stored `opencode` reads verbatim, is never written, and `known("opencode")` is `None`, which is a correct no-op exclusion because nothing can run it;
  - takes `opencode` out of the defaults, the providers and the descriptors;
  - makes config and the CLI refuse it by name. The CRD keeps the value, so that stored custom resources stay valid, and the operator handler drops it with a warning.
- **L39 then removes the tenant** and its packaging. The console script `opencodeloop` remains through 3.x as a stub that exits 64, naming `vscodeloop`.
- **`claudeloop-local` is a paidloop adapter, declared-only** — the operator's ruling of 2026-09-22. Claude Code is not FOSS, so by 8.b's rule (an adapter is sovereign only when both its tool and its model are free) it is paid-side even when its model is local. Its descriptor's tier becomes PAID, it leaves sovereignloop's pool and its feature switch, and it runs only when `[engines].enabled` or `--engines` names it. Verify independence (ADR-0038 §3) therefore has one sovereign harness (native) until `vscode` passes conformance; that cost is recorded, not hidden (10.f).
- **Ruled:** the operator decided on 2026-09-22 that claudeloop-local moves to paidloop now, rather than waiting for `vscode` (see above).

### 10. Where the code lives

| layer | new or changed |
|---|---|
| `domain/` (pure) | `loop.py` (`LoopId`, `LOOP_PREFERENCE`, `LOOP_OF_TIER`, `LoopMembership`); `residency.py` (`ResidencyPolicy`, `ResidencySchedule`, `SeatSlug`); `seat_choice.py` (`SeatChooser`); `run_protocol.py` (replaces R19); `engine.py` (the new ids and `ENGINE_ID_ALIASES`); `stored_value.py` (`known()` resolves aliases); `ledger.py` (`PaidFallbackDeclared`, `LoopRouted`) |
| `application/` | `loop_selector.py`; `loop_provider.py` (`SelectingLoopProvider`); `interfaces/loop_routing.py` (`LoopRoutingPort`, `RoutedAdapterBinderInterface`); `worker.py` (`EngineQueueSaturated`); `engine_selector.py` (`weighted_candidates` extracted) |
| `infrastructure/loop_service/` | `local_run_executor.py`, `result_store.py`, `route_store.py`, `worktree_lock.py`, `model_runtime.py`, `router.py`, `seat_host.py`, `resident_schedule.py`, `control.py`, `client.py`, `adapter.py`, `command_executor.py` |
| `infrastructure/engines/` | `adapter_factory.py`; descriptors for `vscode` and `vscode-paid` |
| `vibey_bootstrap.amqp` (10.e) | `queue_depth()` and exclusive consume |
| `vibey_runners.common` (10.e) | `RunId`, the run-id validator every runner copies today |
| tenants | `sovereign/` (renamed); `vscode/` (new); `opencode/` (removed by L39) |
| `cli/` | `vibey loop-service --loop`, `vibey loop submit` |
| chart | two loop-service Deployments |

Every new class has an interface beside it (9.b, ADR-0016). Each new `interfaces/` package joins `.importlinter`'s `infrastructure-interfaces-declare-only` contract.

### 11. Chart

`loopServices` has exactly two keys:

- `sovereignloop`: enabled; carries the Ollama wiring.
- `paidloop`: disabled by default (8.b); carries `engineAuth`.

Each loop renders one **router** Deployment, and one **seat-host** Deployment per model it declares (`loopServices.<loop>.models`; for sovereignloop the default is the 8.d designation alone, so a default install renders one seat host). Every one of them has `replicas` fixed at 1, with **no value** to change it: 8.c allows a single instance per model, so a knob that can legally only be 1 configures nothing. Every one uses `strategy: Recreate`, because a `RollingUpdate` would briefly run two instances of the same model. A sovereign seat host is scheduled where its model's runtime is (the Ollama Service it names); two sovereign models on one node still obey §4's residency schedule through the node's single runtime.

Both Deployments mount the worktrees PVC at `/work`, with ADR-0044 §13's co-location rules. Neither needs PostgreSQL. paidloop has an `extraEnv` for each seat, applied only to that adapter's subprocess.

## How each non-negotiable still holds

1. **Never block a worker on a human.** Every new wait is on a machine and is bounded: `route_wait_seconds`, `run_queue_wait_seconds`, and the residency starvation bound. A human gate is still a parked job (ADR-0044 §6).
2. **Credits ≠ rate limit.** All three layers are untouched:
   - the type (`src/vibey/domain/capacity.py:20-24`);
   - the property tests;
   - the `engine_health` CHECK (`migrations/0007_engine_health_rotation.sql:21`).

   Capacity never crosses the wire: the codec refuses `resets_at`, `capacity`, `capacity_state` and `credits`, and a property test proves no such key survives encoding. The loop never reads or writes health. `PaidFallbackDeclared` names a credits refusal by state only, and a property test proves it carries no time. Residency waits are machine scheduling and are never derived from a capacity event.
3. **A capacity rejection outranks a completion claim.** `RunRouted` and `RunResult` carry no completion. The caller still reads `events.jsonl` in order, and `build_implement_handler.py:241-263` still checks capacity first. vscodeloop's terminal-status rule puts capacity rejection first.
4. **`domain/` stays pure.** `loop.py`, `residency.py`, `seat_choice.py` and `run_protocol.py` take `now` and ages as arguments. `tests/domain/test_domain_purity.py` walks them.
5. **Dogfood the family (10.e).**
   - AMQP goes through `vibey_bootstrap.amqp`, and the two capabilities it lacked (queue depth, exclusive consume) are taught to it.
   - The run-id validator moves into `vibey_runners.common`, not into a sixth copy.
   - The inbox and tailer are R20's extracted classes.
   - The Ollama HTTP transport is the one `ollama_chat.py` already has, extended with `get_json`.
6. **Everything-as-code, never less configurable (12.c).**
   - Both invocation modes remain.
   - Every tunable is a key: capacity, per-seat prefetch, the models, the default model, the residency bounds, unload-on-switch, the route wait, the queue wait, the supersede grace, the stale-lock bound, the editor binary, and the VS Code provider and model.
   - Every old name keeps working through the alias window (*Migration*).
   - **Flags, stated plainly:**
     - Retiring opencodeloop removes a configurable engine. That is a move to a less configurable state, and needs the operator's explicit acceptance in the ratifying merge.
     - Per-adapter pod `resources` cannot exist inside one paidloop pod. R30's per-engine blocks were never merged, so nothing shipped is lost.
     - The `replicas` knob is dropped because of 8.c (§11).
7. **A governing rule is a ratified sub-doctrine.** "Exactly two loops", "a new runner joins a loop as an adapter", "sovereignty follows the model and the tool" and "the inner layer runs on queues" are conduct. They are drafted as amendments of 8.b and 8.c below, for ratification by the merge that carries this record.
8. **CDD (9.c, 9.d).** Every lane lands behind today's defaults (`invocation = subprocess`). The VS Code driver is gated on recorded evidence. opencodeloop's removal waits for its replacement to pass conformance. Each divergence therefore has a bounded path back.
9. **Status is evidence-bounded (10.f).** Every claim names its file and the `391673c2` cutoff. Unverified upstream behaviour is listed under *Verification owed*, and each item has a lane test that fails if reality disagrees.
10. **Classes with interfaces beside them (9.b).** Every new class gets an interface, and no lane adds a module-level function without a written reason.
11. **The handoff no-loss gate** is untouched (`domain/noloss.py`, `handoff_orchestration.py`, `wind_down.py`). Exit 75 still reaches `build_implement_handler.py:249`. A lost `RunResult` falls back to the persisted result file. If that is missing too, the exit code is `None`, which is a retry, never a partial handoff.
12. **Every job is idempotent under replay.** Routes are created once, forwards follow the stored route, and runs are deduplicated. Supersede is fenced on the shared volume across both loops (§6). This is still the **riskiest invariant**, now with a cross-loop dimension.
13. **The ledger is append-only.** No row is rewritten. Legacy ids read verbatim, so the chain verifies. The two new event kinds are forward-compatible for older readers (#275).
14. **Conventional Commits; never implement on `main`.** Every lane is a Conventional Commit on a storm branch, merged into `develop` by the merge train.

## Canon amendments owed (carried by #392, for ratification by the operator's merge)

The operator's own wording is what #392 carries, and it supersedes the drafts below where they differ: 8.b names "**VS Code** when its provider is local" in sovereignloop and "VS Code on a paid provider" in paidloop, repeals OpenCode in both, and adds the paid defaults (Claude, VS Code, AWS, GitHub); 8.c makes the unit "**a single instance per model**", not "per deployment". The drafts are kept as the record of what this ADR first proposed.

**8.b, the engines bullet** (replacing `doctrines.md:116-120`):

> **Engines** default to **sovereignloop**, which drives free models on the operator's own hardware through its adapters — its own native agent and VS Code's open-source build (Code - OSS, as VSCodium ships it) — always on, never needing declaration, for every phase. **paidloop** — `claudeloop` by default, and `codexloop`, `cursorloop`, `agyloop` and VS Code on a paid provider — is declared-only. An adapter is sovereign only when both its model and its tool are free and run on the operator's own hardware; the same tool on a paid provider is a paidloop adapter.

**8.c, first paragraph** (replacing `doctrines.md:173-180`):

> **8.c — every loop runs once, fed by a queue**: the family has exactly two loops, `sovereignloop` and `paidloop`, and each runs as **a single instance per deployment** (one machine, or one cluster), taking its work from **a queue** on the bus surface (8.b). A runner the family adds joins one of the two as an adapter; it is never a third loop. Nothing starts a second instance of a loop to go faster, and nothing spawns a loop directly. Each loop's own round robin across its adapters and models also runs on queues — the loop puts every run on the queue of the adapter or model it chose — so waiting is ordered, visible and safe at both layers.

## Evidence flags on the operator's decisions (10.f)

- **"claudeloop (the default, per 8.b paid defaults)".** The ratified 8.b names no paid default. At `391673c2` it says only that "the paid loop engines … are declared-only" (`doctrines.md:116-120`). The 8.b draft above adds the default. paidloop itself stays declared-only.
- **"Exactly two loops".** The ratified 8.c enumerates six loops (`doctrines.md:174-175`). Until the amendment is ratified, building two loops would put the code ahead of the law. That is the one plain conflict with a non-negotiable, and it dissolves in the merge that ratifies #392.
- **"A single instance per model".** #392 changes 8.c's unit from the deployment to the model. §3 and §11 follow it. 8.c's heading ("every loop runs once") still reads per loop; #392 asks the operator whether to align it.
- **"VS Code", unqualified, in the sovereign list.** #392 names "VS Code" where this ADR says Code - OSS. §8 keeps the sovereign adapter on the open-source build, because Microsoft's build carries a proprietary licence and telemetry, and naming it would weaken 8.b (Article IV.2). #392 asks the operator to confirm.
- **"qwenloop is renamed".** The append-only ledger and its hash chain keep `qwenloop` forever (§7). The rename covers every *name*. It never touches stored *text*.
- **"Drives Code - OSS with a local model".** No evidence at the cutoff shows a headless, account-free agent session in Code - OSS or VSCodium. §8 gates the driver on V-VS1 to V-VS5.
- **"opencodeloop is retired".** That is a move to a less configurable state (12.c). See non-negotiable 6.
- **"Both layers run on RabbitMQ".** The subprocess mode, kept under 12.c, has no queues. The rule binds service mode, which R34 makes the default.
- **The forward-compatibility rule (#275, #287) has no ADR.** It lives only in `domain/stored_value.py` and `domain/ledger.py`. The docs wave should record it.
- **ADR-0044 §13 is corrected, not only restructured** (see *Context*: supersede at prefetch 1, and the worktree guard held per instance).
- **The loop is database-free by choice.** "The inner layer circuit-breaks an adapter" is realized as: the caller writes the circuit and the loop enforces it. This keeps capacity off the wire. If the operator wants the loop to own circuits, it needs PostgreSQL and the credits CHECK in its path. That is a larger change, rejected below.

## Security impact

The broker stays an execution capability (ADR-0044's security section), with these changes:

- A loop runs only the binaries of **its own** adapters. `args[0]` is validated as before. `cwd` must lie under `[loop_services] root`.
- **The model is the loop's own decision.** It is persisted in the loop's route store. The environment for it comes only from the loop's configuration. A `model_pin` is honoured only when it names a declared model. No message sets the environment.
- The exclusive intake consumer stops a rogue second instance from draining a loop's queue.
- **The worktree fence writes only inside `<cwd>/.vibey/`.** Breaking a stale lock renames it aside, and never deletes a holder's evidence.
- **vscodeloop's sovereign settings allow only a local provider host.** A paid provider in a sovereign run is refused before any request leaves the machine.

## Migration (renames and aliases)

| old | new | alias kept | until |
|---|---|---|---|
| stored engine id `qwenloop` (ledger, `handoff`, `budget_ledger`, `job.requirement`) | `sovereignloop` for new writes | read verbatim; `known()` resolves it | **forever** (append-only history) |
| stored engine id `opencode` | — (retired by L38) | read verbatim; never written | **forever** |
| `EngineId.QWENLOOP` (Python) | `EngineId.SOVEREIGNLOOP` | enum alias | removed by L09, in the same release wave |
| package and tenant `qwenloop`, `src/vibey_runners/qwen` | `sovereignloop`, `src/vibey_runners/sovereign` | none: a clean import rename | — |
| console script `qwenloop` | `sovereignloop` | same entry point; a deprecation line on stderr | all of 3.x; removed no earlier than 4.0.0, by a recorded decision after `vibey doctor` reports no use |
| `QWENLOOP_BASE_URL`, `_MODEL`, `_API_KEY`, `_CONFIG`, `_NETWORK` | `SOVEREIGNLOOP_*` | read when the new name is unset | all of 3.x, as above |
| `<config>/qwenloop/config.toml` | `<config>/sovereignloop/config.toml` | read when the new file is absent | all of 3.x |
| model cache `<cache>/qwenloop` | `<cache>/sovereignloop` | read while it exists; **never moved automatically** (ADR-0015 #5) | while it exists; 13–16 GB is not re-downloaded silently |
| `.qwenloop/runs/<id>` | `.sovereignloop/runs/<id>` | read for resume, inbox and sessions | all of 3.x |
| `QWENLOOP_TASK_FULLY_COMPLETE` | `SOVEREIGNLOOP_TASK_FULLY_COMPLETE` | the runner accepts either from the model | all of 3.x |
| `[engines] enabled/weights = ["qwenloop"]`, `[phases.*].engines`, `--engines qwenloop` | `sovereignloop` | normalized with a deprecation warning | all of 3.x |
| `[qwenloop]` table | `[sovereignloop]` | read when `[sovereignloop]` is absent; both present is an error | all of 3.x |
| `[features] qwenloop`, `VIBEY_FEATURE_QWENLOOP` | `[features] sovereignloop`, `VIBEY_FEATURE_SOVEREIGNLOOP` | read when the new one is unset | all of 3.x |
| `--provider qwenloop` | `--provider sovereignloop` | accepted with a warning | all of 3.x |
| CRD `spec.engines: [qwenloop]` | `sovereignloop` | kept in the enum; normalized by the handler | until the CRD's next API version, whose conversion maps it |
| chart `ollama.qwenloopFeature`, `worker.provider=qwenloop`, `worker.engines=qwenloop` | `ollama.sovereignloopFeature`, `sovereignloop` | honoured when the new key is unset | all of 3.x |
| `[loop_services.<engine_id>]` (R01, unreleased) | `[loop_services.<loop_id>]`, `.seats.<engine_id>` | none: never released | — |
| `opencode` as an engine or provider, and `opencodeloop` | `vscode`; `--provider sovereignloop` | refused by name with the replacement; `opencodeloop` stays as an exit-64 stub | the stub through 3.x |

**Removing a spelling is not "less configurable" under 12.c**, because the same key exists under its new name. Removing one *silently* would break adopters, and that is why every removal waits for `vibey doctor` evidence (lane L07 makes it list each legacy spelling in use).

**No SQL migration is needed.** `engine_health` and `rotation_cursor` rows for `qwenloop` go stale and are skipped. A rolling upgrade's older workers read `sovereignloop` as `UnrecognizedEngineId` and never select it (#287).

## Consequences

**Good.**

- There are two services instead of seven. Each is single-instance and fed by queues at both layers, with 8.c enforced by the broker.
- One local model stays resident, and switches are bounded and visible, as `LoopRouted.switched`.
- A paid fallback is always declared, and it always carries its reasons.
- Supersede now works at prefetch 1 and across loops, which closes two latent ADR-0044 holes.
- Capacity never crosses a process boundary.
- The family gains queue depth, exclusive consume, and a shared `RunId`.
- Sovereignty is judged by the model and the tool, not by the binary's location.

**Bad.**

- **Riskiest: a worktree fence on a shared filesystem.** It relies on `O_EXCL` behaving on the worktrees volume. That holds on a local disk (ReadWriteOnce, one node). On NFS it is an assumption (V-FS1).
- **Throughput by design.** While sovereignloop's queue is long, an idle declared paidloop is not used. Saturation is not "cannot carry" (8.a).
- **A switch costs a model load** of 13–16 GB (tens of seconds), and the starvation bound can force one.
- **Two SWRR state stores:** the loop's cursor file in service mode, and `rotation_cursor` in subprocess mode.
- **Recreate means a loop is down during a rollout,** for up to its drain grace.
- **The VS Code adapter may not be feasible** as specified. Until it is, sovereignloop has one FOSS adapter (native), plus `opencode` for a project that still declares it; `claudeloop-local` is on the paid side (§9).
- **The rename touches more than 100 references and 42 test literals.** Lane L09 is mechanical but wide.

## Alternatives rejected

- **Merge the four paid runners' source into one `paidloop` package.** It would put four vendor SDK stacks in one tenant, break ADR-0022's per-tenant gates, and bypass the protected live conformance suite (`tests/live/test_scripted_binary_conformance.py`), which pins each binary. "Combined" is realized at the loop: one service, one queue, one inner rotation.
- **Keep one service per engine (ADR-0044 §13).** That is seven loops, against the operator's decision. It also leaves no place for residency, because seven services would contend for one model.
- **Let the loop own circuits by reading and writing `engine_health`.** It would put PostgreSQL, the credits CHECK path and capacity classification into the loop, and require a project for every storm run. Sending the caller's candidate snapshot keeps capacity off the wire.
- **Rotate models per job inside sovereignloop.** That thrashes 13–16 GB loads (see *Context*).
- **Keep `qwenloop` as the stored id and rename only the binary.** It is cheaper, but every `vibey engines`, `vibey status` and dashboard reader would see an id that names a binary that no longer ships.
- **Rewrite stored `qwenloop` ids to `sovereignloop`.** It is forbidden for `event` (append-only, hashed). For the other tables it is unnecessary, because the rows go stale harmlessly.
- **Alias `opencode` to `vscode`.** It would attribute OpenCode's history to a different tool.
- **Cross-loop affinity.** A warm paid session would then outrank a recovered sovereign loop, against 8.a.
- **Fall back to paid when sovereign is saturated.** Busy is not "cannot carry". 8.a's floor is capability, not latency.
- **A `replicas` value on each loop.** 8.c allows exactly one instance, so the knob could only ever be 1.

## Verification owed at implementation

Each item is asserted by the named lane's test, so a disagreement fails a lane rather than a cluster.

- **V-AMQP1.** A quorum queue refuses a second consumer when the first holds `exclusive=True`. Lane L21; integration test against the pinned `rabbitmq:4-management-alpine`.
- **V-AMQP2.** A passive `queue.declare` returns `message_count` for a quorum queue, via aio-pika's `declaration_result.message_count`. Lane L21.
- **V-OLL1.** `GET /api/ps` lists loaded models, and `POST /api/generate {"model": M, "keep_alive": 0}` unloads M. Lane L26. The integration test is marked `integration` and runs when `VIBEY_TEST_OLLAMA_URL` is set.
- **V-OLL2.** Ollama serves one model at a time on a 24 GB machine for GPT-OSS 20B (13.1 GB) plus any 14B+ second model, meaning it evicts rather than overflows. This is recorded evidence for the operator, not a unit test.
- **V-FS1.** `open(path, "x")` is atomic on the worktrees volume (a local disk, and an NFSv4 ReadWriteMany class, if one is used). Lane L25 tests the local case. The RWX case is a cluster-smoke contract, owed by lane L37's follow-up.
- **V-VS1.** A headless or virtual-display invocation of Code - OSS (`codium`) that runs an agent session to completion in a given folder, with no GUI interaction. Record the exact command.
- **V-VS2.** The agent extension used, with its licence (OSI-approved for `vscode`) and its source (Open VSX), and confirmation that it needs no account.
- **V-VS3.** Settings that register an OpenAI-compatible local provider at a given base URL and model, with the resulting network traffic limited to that host (no call home). Record a packet or proxy capture.
- **V-VS4.** The event stream obtainable from the session (turns, tool calls, text, errors), for the `events.jsonl` mapping.
- **V-VS5.** How to distinguish the OSS build from Microsoft's (`product.json` fields), for doctor.
- **V-CC1.** Claude Code's licence and its default network behaviour with a local profile (for §9's flag).
