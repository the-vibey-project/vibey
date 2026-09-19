# 0038 — Local engines are preferred first (8.a): claudeloop-local, tiered selection, and sovereign DESIGN/DECOMPOSE by default when enabled

**Status:** accepted · **Date:** 2026-09-18 · **Amends:** ADR-0015 (standby becomes preferred), ADR-0027 ("Not yet" becomes yes) · **Cites:** sub-doctrine 8.a · **Issues:** #236, #115 (slice B5)

**Owes:** nothing — mechanism (ADR-0020). The rule this applies is already law:
sub-doctrine 8.a, *the sovereign path is the preference, not the fallback*. This
record is how selection and the providers obey it; it states no new conduct.

## Context

ADR-0015 admitted `qwenloop` as a **standby**: `EngineSelector` kept only paid
runtimes among the eligible set and let qwenloop into rotation only when that set
was empty (`engine_selector.py`, a hard-coded `EngineId.QWENLOOP` filter). It
recorded that rule, one week before 8.a was ratified, as an *open tension*: under
8.a a paid engine is the move that must be justified, and the code preferred paid
silently. ADR-0027 then gave DESIGN a sovereign provider but kept it explicit —
"Make qwenloop the default DESIGN provider. Not yet."

Issue #236 asks for the rest: run the storm and BUILD on Ollama, for free. Two
runtime pieces landed beside this one and are its dependencies, not its code:

- **#258** — claudeloop *backend profiles*: `--profile NAME` points Claude Code at
  any Anthropic-Messages server (Ollama among them), scrubs the paid key, records
  every local turn at $0, refuses to fake completion on a model that cannot make
  tool calls, and exits **78** (EX_CONFIG) for `BackendMisconfigured` — an
  unreachable server, a model not pulled or failing to load, a context too small.
- **#243** — qwenloop's `openai-compat` backend, attaching to an existing server
  through `QWENLOOP_BASE_URL` and `QWENLOOP_MODEL` instead of starting its own.

And #255 gave DESIGN and DECOMPOSE one Ollama client, `VIBEY_OLLAMA_URL` /
`VIBEY_OLLAMA_MODEL`, with `QwenloopWorkPlanProducer` beside the design provider.

## Decision

**1. A new engine, `claudeloop-local` — not a flag on claudeloop.** Same binary,
same `.claudeloop` run layout, same done marker; its own `EngineId`, health row,
circuit, cost and tier. Its descriptor is *built*, not constant
(`descriptors.py::ClaudeloopLocalDescriptors`), from `[engines.claudeloop_local]`:
`profile` (default `local`, overridden by `VIBEY_CLAUDELOOP_LOCAL_PROFILE`),
`context_window` (default 32 768) and `structured_verdict` (default false). Every
effort level passes `--profile <name> --preset low|medium|high` and never
`--effort`, because a local profile does not forward it; `auth_env=()`; cost 0/0.
Preflight runs `claudeloop doctor --profile <name>` (`EngineDescriptor.doctor_args`),
so the health check probes the backend the run will use.

**2. Tiers, and the local tier first.** `EngineDescriptor.tier` is `LOCAL` or `PAID`
(`domain/engine.py`); qwenloop and claudeloop-local are LOCAL. `TIER_PREFERENCE =
(LOCAL, PAID)`. `EngineSelector` builds every eligible candidate, then
`domain/rotation.py::preferred_tier` offers SWRR only the candidates of the first
tier holding one that can win a round (positive effective weight). Within a tier
it is ordinary smooth weighted round-robin, so qwenloop and claudeloop-local rotate
with each other. A paid engine is chosen only when no local engine is eligible —
switched off, uninstalled, failing its doctor, circuit open, excluded by the job.
The hard-coded qwenloop filter is gone.

**3. Verify independence is unchanged, and still holds across tiers.**
`selection_inputs_for_job` still excludes the implementer when the pool has anyone
else. qwenloop implements → claudeloop-local reviews; with no second local engine
the review falls to a paid engine; a qwenloop-only pool still reviews its own work
under ADR-0035's waiver (#179).

**4. One resolver for "which local engines are on".**
`infrastructure/engines/local_engines.py::LocalEngineSettings` replaces the three
copies of the qwenloop precedence rule (`bootstrap.qwenloop_enabled`,
`cli/main.py::_qwenloop_feature_enabled`, `config_loader`). Per engine:
`VIBEY_FEATURE_<KEY>` whenever it is set at all, else `[features] <key>` —
`qwenloop` and `claudeloop_local`. The composition root, `vibey worker`, `vibey work`
and `vibey doctor` all ask it.

**5. The selector is confined to the worker's pool.** `SelectingEngineProvider` now
passes its pool (adapters ∩ `--engines`) as the allow-list on every selection, and
the wind-down handoff does the same. A health row outlives the switch that wrote
it; before tiers that only mattered when nothing paid was eligible, but with local
engines *preferred* a stale local row would have been chosen and the job deferred
forever for want of an adapter.

**6. Every enabled local engine is refreshed before each selection.** No cron
records a local engine's health, so — as ADR-0015 did for qwenloop — the provider
preflights each enabled local engine in the pool and records `conformance_ok =
installed and auth_ok`. Its `doctor` is the readiness check that matters: the
server answers, the model is present, and (claudeloop-local) the model answers a
tool call.

**7. One endpoint setting.** `VIBEY_OLLAMA_URL` (root form) is the operator's one
setting. `LocalEndpointEnvironment` reads it and `VIBEY_OLLAMA_MODEL` (or
`--ollama-model`) through the same `OllamaChatClient` the providers use — the same
validation, the same defaults — and derives `QWENLOOP_BASE_URL=<root>/v1` and
`QWENLOOP_MODEL` for qwenloop's process, each only when the operator has not set it.
It reaches the process through a new `LoopProcessAdapter.env_overlay`, layered after
the orchestrator's Python environment is stripped, on the run and on its preflight.
claudeloop-local takes its endpoint from its profile's `base_url`.

**8. Exit 78 parks for a human.** `RunOutcome.misconfiguration_gate` turns an
incomplete run that exited 78 into a `Park` with an `engine_misconfigured` gate
naming the engine's own `doctor` command — in `build.implement` and in
`build.verify` alike. Retrying a configuration fault burns a bounded ladder on the
same fault. `_classify_claudeloop` reads `BackendMisconfigured` as
`AuthenticationFailed` (terminal, not waitable, never credits), and now also reads
the class-name string claudeloop actually writes (`"capacity": "CreditsExhausted"`)
— before, every real claudeloop capacity payload classified as `Available`.

**9. Sovereign DESIGN and DECOMPOSE by default once a local engine is on (#115 B5).**
With no `--provider`, `vibey work` and `vibey worker` choose `qwenloop` —
`QwenloopDesignProvider` and `QwenloopWorkPlanProducer` — when any local engine is
switched on, and `scripted` otherwise. An explicit `--provider` always wins; paid
`claudeloop` is never a default. VISUAL_DESIGN keeps `scripted`: there is no
sovereign visual producer.

### Defaults taken while the operator was away (override welcome)

- **The honest ceiling is STANDARD, even at MAX.** HIGH and MAX run the profile's
  top tier and report `achieved=STANDARD`, so fidelity scoring sees a local model
  for what it is.
- **Local cost is 0/0** per million tokens.
- **STRUCTURED_VERDICT is claimed only when configured** (`structured_verdict =
  true`), and conformance must then prove it for the configured model; claimed and
  unproven, conformance fails and the engine is ineligible.
- **qwenloop and claudeloop-local rotate with each other** — one tier, SWRR, equal
  base weight 1.

## Consequences

**Good.** A project with a local engine switched on runs every phase that has a
sovereign implementation on hardware nobody else controls, and reaches for a paid
engine only when no local one can take the job. The standby tension ADR-0015
recorded is closed the way its option (a) proposed. One resolver, one endpoint
setting, one classifier for one binary.

**Bad.**

- **The paid fallback is not yet *declared*.** 8.a wants the floor "declared loudly
  to a human". When selection falls to a paid engine, the reason is visible
  (`vibey engines`, `vibey doctor`, the local engine's health row) but nothing is
  written to the ledger at that moment. That is the next step, not this one.
- **A local engine can be slower and weaker than the paid one it displaces.** The
  measured ceiling on a 24 GB machine is one agent at a time, and
  `qwen2.5-coder:14b` does not make real tool calls through Claude Code at all
  (#258's live smoke: it once wrote the call as text and typed the done marker).
  The profile's `doctor` refuses such a model, which keeps it ineligible — correct,
  and also why a laptop pool may fall back to paid more often than it hopes.
- **Each BUILD selection runs every enabled local engine's `doctor`.** For
  claudeloop-local that includes one tool-call probe per tier. That is the price
  ADR-0015 accepted for one engine, now paid for two.
- **The selector's descriptors are static.** `EngineSelector` reads `BY_ENGINE_ID`,
  whose claudeloop-local is the default profile; tier, weight and effort ceiling do
  not depend on the profile, so selection is unaffected, but capabilities are the
  defaults there.
- **The TOML switch still does not reach the worker** unless the project record
  carries `[features]` (ADR-0015's consequence, unchanged): the environment
  variables are the switches that work everywhere.

## Alternatives rejected

- **`claudeloop --profile` as a flag on the existing engine.** One circuit for two
  backends: a local OOM would open the paid engine's circuit and vice versa, and
  cost and tier could not differ. Operator decision: a new engine id.
- **Keep local engines a standby, or weight them.** A standby is the posture 8.a
  inverted; a weight still hands a share of jobs to paid engines while a local one
  is idle. Operator decision: preferred first.
- **Model tiers inside the paid tier by cost factor.** The cost factor is disabled
  and continuous; a tier is a rule, deterministic and testable.
- **Derive `QWENLOOP_BASE_URL` from the default URL even when `VIBEY_OLLAMA_URL` is
  unset.** That would silently move every qwenloop user off the backend qwenloop
  selects for itself. The operator opts in by setting the one variable.
