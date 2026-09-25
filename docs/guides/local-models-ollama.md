# Local models on Ollama

Sub-doctrine 8.a makes the sovereign path the preferred way to run vibey, not the
fallback. This guide is the operator recipe for doing that on one machine with
[Ollama](https://ollama.com): the server, the claudeloop profile, the switches,
and — just as important — what a local model can and cannot carry today.

There are three local engines. `gptossloop` — the local runner on GPT-OSS 20B, the
sovereign default — is on without any switch. `qwenloop` is the same runner on a
Qwen model (`qwen3:14b`), and `claudeloop-local` is the claudeloop binary on a local
backend profile; both are opt-in
([ADR-0060](../architecture/decisions/0060-gptossloop-is-the-sovereign-engine.md)).
With its local engines on, vibey:

- **prefers local engines first for BUILD.** Selection runs smooth weighted
  round-robin within the LOCAL tier (`gptossloop`, plus `qwenloop` and
  `claudeloop-local` when switched on) and falls back to the paid engines only when
  no local engine is eligible
  ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md));
- **runs DESIGN and DECOMPOSE on the local model** when no `--provider` is given
  (`GptossloopDesignProvider`, `GptossloopWorkPlanProducer`, recorded in the ledger
  as `gptossloop`);
- **costs nothing per token**: every local engine is priced 0/0, and claudeloop
  records every local turn at $0.

## 1. The Ollama server

Start the server with settings sized for agent work. On a 24 GB machine:

```bash
export OLLAMA_CONTEXT_LENGTH=32768     # the window every request gets; match it below
export OLLAMA_FLASH_ATTENTION=1        # needed for a quantized KV cache
export OLLAMA_KV_CACHE_TYPE=q8_0       # roughly halves KV-cache memory at 32K
export OLLAMA_MAX_LOADED_MODELS=1      # one model resident; a second one evicts it
ollama serve
```

With the macOS app, set them with `launchctl setenv NAME value` and restart the app.
Ollama's default context is far smaller than an agent needs: Claude Code's own system
prompt and tool definitions are about 14,000 tokens before your plan, so a window
left at the default fails on the first request.

Pull the model you mean to run (see [the honest ceiling](#the-honest-ceiling) before
you choose):

```bash
ollama pull your-model:tag
```

## 2. The one endpoint setting

`VIBEY_OLLAMA_URL` is the single setting, in root form. Everything local reads it:

```bash
export VIBEY_OLLAMA_URL=http://127.0.0.1:11434
export VIBEY_OLLAMA_MODEL=your-model:tag     # or --ollama-model on work/worker; default gpt-oss:20b
```

For the qwenloop storm profile used while developing this repository, see the
copyable [qwenloop-local.toml](../examples/qwenloop-local.toml) and
[qwenloop-storm.env.example](../examples/qwenloop-storm.env.example) examples.
The checked-in storm profile uses `qwen3:14b`, a 32K context window, a 40-turn local budget,
Ollama's OpenAI-compatible endpoint, and the single-model cache settings used
for local agent work. Qwen lifecycle desktop notifications stay enabled and
use macOS's `Ping` sound; `--desktop-notifications` is explicit in the example
commands even though it is the default.

- The DESIGN and DECOMPOSE providers talk to `<VIBEY_OLLAMA_URL>/api/chat`.
- gptossloop's process gets `GPTOSSLOOP_BASE_URL=<VIBEY_OLLAMA_URL>/v1` and
  `GPTOSSLOOP_MODEL=<the model>` (`--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else
  `gpt-oss:20b`), so it attaches to this server and runs the providers' model.
- qwenloop's process gets `QWENLOOP_BASE_URL=<VIBEY_OLLAMA_URL>/v1` only — never a
  model: it asks for `qwen3:14b` unless `QWENLOOP_MODEL` or its own config names
  another, so pull that model too.
- Each variable is set only when you have not set it yourself. Without
  `VIBEY_OLLAMA_URL`, each runner keeps its own backend selection. gptossloop reads
  only `GPTOSSLOOP_*` and qwenloop only `QWENLOOP_*`, so naming a model for one never
  changes the other's.
- claudeloop-local reads its endpoint from its **profile** (next step), so keep the
  profile's `base_url` equal to `VIBEY_OLLAMA_URL`.

## 3. The claudeloop profile

`claudeloop-local` is the claudeloop binary run with `--profile <name>`: Claude Code
still runs the agent loop, the tools and the edits, but talks to the local server,
with the paid key scrubbed. Describe the profile in `claudeloop.toml` in the project
(or `~/.config/claudeloop/config.toml`):

```toml
[profiles.local]
base_url = "http://127.0.0.1:11434"      # = VIBEY_OLLAMA_URL
model_low = "your-model:tag"             # --preset low     (TRIVIAL, LOW)
model_medium = "your-model:tag"          # --preset medium  (STANDARD)
model_high = "your-model:tag"            # --preset high    (HIGH, MAX)
small_fast_model = "your-model:tag"
context_window = 32768                   # = OLLAMA_CONTEXT_LENGTH
max_output_tokens = 8192                 # Claude Code reserves this out of the window
```

Every key, and what a local profile changes (a blanked `ANTHROPIC_API_KEY`, $0 turns,
no `--effort`, web search refused, completion only by a structured verdict), is in
claudeloop's own
[local backend guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/local-backend.md).
Check the profile with claudeloop directly first:

```bash
claudeloop doctor --profile local
```

Trust its `backend-tools` check above all: it asks each tier to make one real tool
call. A model that fails it cannot do agent work under Claude Code at all.

## 4. Switch the local engines on

Each local engine has its own switch. The environment variable wins whenever it is
set; otherwise `[features]` in the project's config decides; otherwise the engine's
default applies.

| Engine | Default | Environment | `vibey.toml` |
|---|---|---|---|
| `gptossloop` | on | `VIBEY_FEATURE_GPTOSSLOOP=0` switches it off | `[features] gptossloop = false` |
| `qwenloop` | off | `VIBEY_FEATURE_QWENLOOP=1` | `[features] qwenloop = true` |
| `claudeloop-local` | off | `VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` | `[features] claudeloop_local = true` |

Before ADR-0060 the qwenloop switch turned on the engine that ran `gpt-oss:20b`; that
engine is now `gptossloop`, on by default. With the qwenloop switch on, `vibey
worker` and `vibey doctor` print a `note:` saying so — drop the switch unless you
want Qwen as well.

claudeloop-local's own settings:

```toml
[engines.claudeloop_local]
profile = "local"             # the [profiles.NAME] above; VIBEY_CLAUDELOOP_LOCAL_PROFILE overrides
context_window = 32768        # keep equal to the profile's and the server's
structured_verdict = false    # claim it only once conformance proves it (below)
```

The worker reads `[features]` from the project's stored config, which no `vibey new`
flag writes yet, and `vibey doctor` reads `./vibey.toml`. The environment variables
are the switches that reach both — set them for `vibey doctor` and `vibey worker`
alike.

## 5. Check, then record

```bash
vibey doctor                                   # lists every switched-on local engine
vibey doctor --conformance --record --engine claudeloop-local
vibey doctor --conformance --record --engine gptossloop
vibey doctor --conformance --record --engine qwenloop   # when switched on
```

`vibey doctor` runs `claudeloop doctor --profile <name>` for claudeloop-local, so the
health check probes the backend the run will use. The worker also re-runs each
enabled local engine's `doctor` before every BUILD selection; a local engine whose
doctor fails is simply not eligible, and the job goes to the next engine.

**STRUCTURED_VERDICT.** claudeloop-local does not claim a structured verdict by
default. Set `structured_verdict = true` only for a model you intend to hold to it:
conformance then requires a `VerdictRendered` event from the configured model, and a
claim it cannot prove fails conformance and makes the engine ineligible.

## 6. Run

```bash
vibey worker                                   # sovereign DESIGN/DECOMPOSE, local-first BUILD
vibey worker --engines gptossloop,claudeloop-local   # never fall back to a paid engine
```

- An explicit `--provider` always wins; `claudeloop` (paid) is never a default.
- Verification still rotates: gptossloop's work is reviewed by claudeloop-local (or
  qwenloop) and the other way round. With one local engine in the pool, the review goes to a paid
  engine if one is configured, or the engine reviews its own diff and the ledger says
  so ([ADR-0035](../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
- A run whose backend cannot serve it — the server down, a model not pulled or out of
  memory, a window too small — makes claudeloop exit **78**. The job parks with an
  `engine_misconfigured` gate naming the `doctor` command that shows the cause. Fix
  it, then answer the gate to retry: `vibey answer <gate-id> --raw '{}'`.

## Running Claude Code itself on Ollama (a storm)

The same server can carry the interactive Claude Code that drives a storm of lanes.
These are the variables a local claudeloop profile sets for Claude Code; export them
in the shell that starts `claude`:

```bash
export ANTHROPIC_BASE_URL=http://127.0.0.1:11434
export ANTHROPIC_AUTH_TOKEN=ollama
export ANTHROPIC_API_KEY=""                         # a paid key must not travel along
export ANTHROPIC_DEFAULT_OPUS_MODEL=your-model:tag
export ANTHROPIC_DEFAULT_SONNET_MODEL=your-model:tag
export ANTHROPIC_DEFAULT_HAIKU_MODEL=your-model:tag
export CLAUDE_CODE_SUBAGENT_MODEL=your-model:tag
export CLAUDE_CODE_MAX_CONTEXT_TOKENS=32768          # = OLLAMA_CONTEXT_LENGTH
export CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1    # no telemetry or update checks
claude
```

Every model id must be one the server serves: an unset tier falls back to a
`claude-*` id the local server does not have.

## The honest ceiling

A local model is not the paid one it displaces, and the defaults say so:

- **One agent at a time on a 24 GB machine.** A 14–20B model at a 32K window fills
  it; a second concurrent agent evicts the first model (`OLLAMA_MAX_LOADED_MODELS=1`)
  or does not fit. Run `vibey worker -j 1` and one storm lane at a time.
- **Effort tops out at STANDARD.** claudeloop-local's HIGH and MAX run the profile's
  top tier and report `achieved=STANDARD`, so rotation sees a local model for what it
  is.
- **Use the endpoint-specific tool smoke before a storm.** `qwen2.5-coder:14b` can
  write tool calls as text or misclassify the `qwenloop-verdict` fence when served
  locally. On this machine, `qwen3:14b` produced a native `read_file` call through
  Ollama's OpenAI-compatible endpoint, so it is the checked-in storm example. This is
  a compatibility observation, not a guarantee for every serving template; keep the
  runner's tool smoke and bounded completion guard enabled.
- **Research needs you.** A local model has no web access; DESIGN's research stage
  parks a `research_evidence` gate asking for `<topic>.md` in `VIBEY_EVIDENCE_DIR`
  rather than inventing a source
  ([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)).
- **A paid fallback is visible, not yet announced.** When no local engine is eligible
  the job goes to a paid engine; `vibey engines` and the local engine's health show
  why, but nothing is written to the ledger at that moment yet. Pin the pool with
  `--engines` if a paid run is never acceptable.
