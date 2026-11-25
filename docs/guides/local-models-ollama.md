---
description: Run vibey on a model on your own computer with Ollama, from the server settings and the two GPT-OSS builds to the local engines, unattended runs, web research and the honest limits.
---

# Run vibey on local models with Ollama

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** vibey runs on a model on your own computer by default: the
> `gptossloop` engine on Heretic v2 of GPT-OSS 20B, served by Ollama, at no cost per token. Install
> Ollama, run `ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` (about
> 12.1 GB), start `vibey worker`. You need 24 GB of memory (32 GB recommended). Expect one agent at
> a time, effort up to STANDARD, and slow first turns.

## The lesson

It was raining, and Daniel had brought his laptop to the Professor's kitchen table to ask about
money.

**Daniel:** Professor, the paid engines are better. Why does vibey start with a model on my own
computer?

**Professor Feynman:** Think of cooking at home against eating out. At home every meal costs you
the groceries you already bought, nobody else sees your recipe, and you can cook at three in the
morning. A restaurant cooks better food, faster, and sends a bill. vibey's rule, sub-doctrine
8.a, is to cook at home first and go out only when the home kitchen cannot make the dish.

**Daniel:** And what is my kitchen, exactly?

**Professor Feynman:** Ollama is the stove: a program that serves a model on your machine. The
model is GPT-OSS 20B, and vibey's default build of it is called Heretic v2. `gptossloop` is the
cook: the engine that gives the model tools and runs a task. When vibey picks an engine for a
BUILD job, it looks at the local engines first, and only when none is eligible does it fall back
to a paid one.

**Daniel:** So I never pay?

**Professor Feynman:** Not per token, for local work. But find the gap in the picture: a home
cook can always walk to a restaurant, and today vibey does that without writing it in the
ledger at that moment. If a paid run is never acceptable, you lock the door: `--engines` with
local engines only.

**Daniel:** And the food is worse.

**Professor Feynman:** Smaller, slower, and honest about it. A 20B model does one task at a time
on a 24 GB laptop and tops out at STANDARD effort. This page ends with that list, so nobody is
surprised.

## Do it

Checked on macOS with vibey-engine 0.4.0. Step 6's output was run for this page; the others
describe what the code prints.

1. Install vibey ([install guide](install.md)) and Ollama: on a Mac, the app from
   [ollama.com/download](https://ollama.com/download), opened once; on Linux:

   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. Start the server with a window sized for agent work (24 GB machine):

   ```bash
   export OLLAMA_CONTEXT_LENGTH=32768
   export OLLAMA_FLASH_ATTENTION=1
   export OLLAMA_KV_CACHE_TYPE=q8_0
   export OLLAMA_MAX_LOADED_MODELS=1
   ollama serve
   ```

   With the macOS app, set them with `launchctl setenv NAME value` and restart the app instead.

3. In another terminal, pull vibey's default model.

   ```bash
   ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
   ```

   You should see Ollama download the model, about 12.1 GB, and return to the prompt.

4. Optional, for web research: install vibey's local SearXNG (it needs `podman` or `docker`).

   ```bash
   vibey searxng install
   ```

5. Check the setup.

   ```bash
   vibey doctor
   ```

   You should see a `gptossloop` line that no longer says the model is not served, and an
   `ollama` line.

6. See what vibey will run, from any folder. It needs no database and no network.

   ```bash
   vibey loops
   ```

   You should see the two loops. The first block, as it printed on the computer this page was
   checked on:

   ```text
   sovereignloop (tier local): the default loop by canon 8.b; a local engine runs only while its switch is on
                        gptossloop    qwenloop      claudeloop-local
     switched on        yes           no            no
     $ per Mtok in/out  0.00/0.00     0.00/0.00     0.00/0.00
     model              -             -             -
     TRIVIAL            max-turns 8   max-turns 8   profile local preset low
     LOW                max-turns 16  max-turns 16  profile local preset low
     STANDARD           max-turns 40  max-turns 40  profile local preset medium
     HIGH               max-turns 64  max-turns 64  profile local preset high -> STANDARD
     MAX                max-turns 96  max-turns 96  profile local preset high -> STANDARD
     ULTRA              (no flags)    (no flags)    profile local preset high -> STANDARD
   ```

7. Record conformance for the local engine, then run.

   ```bash
   vibey doctor --conformance --record --engine gptossloop
   vibey worker
   ```

   You should see the worker start with `gptossloop` as its DESIGN and DECOMPOSE provider. A
   project must exist first (`vibey new`).

## Daniel's teach-back

**Daniel:** Ollama serves a model on my own machine, and vibey's default is Heretic v2 of GPT-OSS
20B. `gptossloop` is on without a switch, so with no flags vibey runs DESIGN and DECOMPOSE on that
model and tries local engines first for BUILD, paying nothing per token. If no local engine is
eligible, a paid one takes the job, so I pin `--engines` to local ones when that must never
happen. The model is slower and weaker than a paid one: one agent at a time, effort up to
STANDARD.

**Professor Feynman:** All correct. Add one thing you did not ask about: DESIGN research no
longer needs you to hand it files. It searches the web through your local SearXNG first.

## The details

### The local engines

There are three local engines
([ADR-0064](../architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)):
`gptossloop`, the local runner on GPT-OSS 20B and the sovereign default, is on without any
switch; `qwenloop` is the same runner on a Qwen model (`qwen3:14b`); and `claudeloop-local` is the
claudeloop binary on a local backend profile. The last two are opt-in. With its local engines on,
vibey:

- **prefers local engines first for BUILD.** Selection runs smooth weighted round-robin within
  the LOCAL tier (`gptossloop`, plus `qwenloop` and `claudeloop-local` when switched on) and falls
  back to the paid engines only when no local engine is eligible
  ([ADR-0038](../architecture/decisions/0038-local-engines-are-preferred-first.md));
- **runs DESIGN and DECOMPOSE on the local model** when no `--provider` is given
  (`GptossloopDesignProvider`, `GptossloopWorkPlanProducer`, recorded in the ledger as
  `gptossloop`);
- **costs nothing per token**: every local engine is priced 0/0, and claudeloop records every
  local turn at $0.

`vibey loops` shows the two loops (sovereignloop, the LOCAL tier and the default; paidloop, the
PAID tier), each engine's switch, its price, what each effort becomes for it, and what it can do
([`vibey loops`](../reference/cli.md#vibey-loops),
[ADR-0103](../architecture/decisions/0103-the-loop-capability-bundle.md)). On the computer this
page was checked on it also printed:

```text
  gptossloop capabilities: yes files, paste_text, plugins (vibey-bundle), mcp, skills, web_search; no images, paste_images
  claudeloop-local capabilities: yes files, paste_text, plugins (claude-plugins), mcp, skills; no web_search; unknown images, paste_images
```

### 1. The Ollama server

The settings in step 2 of [Do it](#do-it), in order: the window every request gets (match it
below); flash attention, needed for a quantized KV cache; a `q8_0` KV cache, which roughly halves
KV-cache memory at 32K; and one model resident, so a second one evicts it. Ollama's default
context is far smaller than an agent needs: Claude Code's own system prompt and tool definitions
are about 14,000 tokens before your plan, so a window left at the default fails on the first
request.

Pull the model you mean to run; see [the honest ceiling](#the-honest-ceiling) before you choose
one that is not the default.

### 2. The one endpoint setting

`VIBEY_OLLAMA_URL` is the single setting, in root form. Everything local reads it:

```bash
export VIBEY_OLLAMA_URL=http://127.0.0.1:11434
# Default sovereign build: Heretic v2 of GPT-OSS 20B (ADR-0099)
#   hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
# Select the unmodified OpenAI release instead with:
#   export VIBEY_SOVEREIGN_MODEL=stock        (or: --ollama-model stock)
export VIBEY_OLLAMA_MODEL=your-model:tag     # or --ollama-model on work/worker; beats VIBEY_SOVEREIGN_MODEL
```

`your-model:tag` is any tag your Ollama serves; leave `VIBEY_OLLAMA_MODEL` unset to run the
default.

### The two sovereign builds (`heretic` and `stock`)

`gptossloop` and the sovereign DESIGN and DECOMPOSE providers share one two-variant catalogue
(`src/vibey/domain/sovereign_model.py`,
[ADR-0099](../architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md)):

| Variant key | Ollama tag | Source and licence | Notes |
|---|---|---|---|
| `heretic` (default) | `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` | `p-e-w/gpt-oss-20b-heretic-v2` (Apache-2.0 weights; about 12.1 GB download; the Heretic tool itself is AGPL-3.0 and not used at runtime) | Refusal direction removed (49/100 test prompts refused against 98/100 for stock; KL divergence 0.1248). Native `MXFP4_MOE`. |
| `stock` | `gpt-oss:20b` | Ollama library (Apache-2.0; about 14 GB download) | OpenAI's release, unmodified. Select with `VIBEY_SOVEREIGN_MODEL=stock` or `--ollama-model stock`. |

Precedence is `--ollama-model` > `VIBEY_OLLAMA_MODEL` > `VIBEY_SOVEREIGN_MODEL` > `heretic`. Both
`--ollama-model` and `VIBEY_OLLAMA_MODEL` also accept the variant keys `heretic` and `stock` and
resolve them to their full tags.

**Verification note (sub-doctrine 10.f):** the Hugging Face manifest for
`hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` has been verified, but the tag has
**not** yet been pulled with `ollama pull` on the reference host, or run through an end-to-end
tool-calling or `--sovereign-fit` measurement there. Every measured latency, memory and benchmark figure on this page and in
[System requirements](../reference/system-requirements.md) was recorded against stock
`gpt-oss:20b`.

**Not every surface uses this catalogue.** Two surfaces still default to stock `gpt-oss:20b`:

| Surface | Default | Make it match |
|---|---|---|
| The krypton VS Code extension's tasks | `vibey.model`, else `VIBEY_OLLAMA_MODEL`, else `gpt-oss:20b` (`packages/vibey-core/src/local-runner.ts`); it never reads `VIBEY_SOVEREIGN_MODEL` | Set `vibey.model` to the Heretic tag ([VS Code extension](vscode-extension.md)) |
| The Helm chart's in-cluster Ollama | `ollama.model: gpt-oss:20b`, passed to the worker as `VIBEY_OLLAMA_MODEL` | `--set ollama.model=<the Heretic tag>` ([Kubernetes](kubernetes.md)) |

Without that, a reader who follows this page and also uses the extension downloads and runs two
different models.

### How the model reaches each engine

- The DESIGN and DECOMPOSE providers talk to `<VIBEY_OLLAMA_URL>/api/chat`, in JSON mode with the
  answer's schema stated in the prompt and checked on the way back; a malformed answer is
  re-asked once, naming what was wrong. A reply cut short by its output budget
  (`done_reason: length`, the reasoning spent every token) is retried once with double the
  budget, within `VIBEY_OLLAMA_CONTEXT`, and reasoning level `VIBEY_OLLAMA_RETRY_THINK` (`low` by
  default; `none` leaves the model's own). A second cut-short reply fails as a *capacity*
  shortfall naming `VIBEY_OLLAMA_OUTPUT` and `VIBEY_OLLAMA_CONTEXT`. Measured before and after in
  [sovereign-retry-2026-09-29](../architecture/evidence/sovereign-retry-2026-09-29.md).
- gptossloop's process gets `GPTOSSLOOP_BASE_URL=<VIBEY_OLLAMA_URL>/v1` and
  `GPTOSSLOOP_MODEL=<the model>` (`--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else
  `VIBEY_SOVEREIGN_MODEL`, else the `heretic` default tag), so it attaches to this server and runs
  the providers' model.
- qwenloop's process gets `QWENLOOP_BASE_URL=<VIBEY_OLLAMA_URL>/v1` only, never a model: it asks
  for `qwen3:14b` unless `QWENLOOP_MODEL` or its own config names another, so pull that model
  too.
- Each variable is set only when you have not set it yourself. Without `VIBEY_OLLAMA_URL`, each
  runner keeps its own backend selection. gptossloop reads only `GPTOSSLOOP_*` and qwenloop only
  `QWENLOOP_*`, so naming a model for one never changes the other's.
- claudeloop-local reads its endpoint from its **profile** (next section), so keep the profile's
  `base_url` equal to `VIBEY_OLLAMA_URL`.

For the qwenloop storm profile used while developing this repository, see the copyable
[qwenloop-local.toml](../examples/qwenloop-local.toml) and
[qwenloop-storm.env.example](../examples/qwenloop-storm.env.example) examples. The checked-in
storm profile uses `qwen3:14b`, a 32K context window, a 40-turn local budget, Ollama's
OpenAI-compatible endpoint, and the single-model cache settings used for local agent work. Qwen
lifecycle desktop notifications stay enabled and use macOS's `Ping` sound;
`--desktop-notifications` is explicit in the example commands even though it is the default.

### 3. The claudeloop profile

`claudeloop-local` is the claudeloop binary run with `--profile <name>`: Claude Code still runs
the agent loop, the tools and the edits, but talks to the local server, with the paid key
scrubbed. Describe the profile in `claudeloop.toml` in the project (or
`~/.config/claudeloop/config.toml`); `your-model:tag` is a tag your Ollama serves:

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

Every key, and what a local profile changes (a blanked `ANTHROPIC_API_KEY`, $0 turns, no
`--effort`, web search refused, completion only by a structured verdict), is in claudeloop's own
[local backend guide](https://github.com/the-vibey-project/vibey/blob/develop/src/vibey_runners/claude/docs/guides/local-backend.md).
Check the profile with claudeloop directly first:

```bash
claudeloop doctor --profile local
```

Trust its `backend-tools` check above all: it asks each tier to make one real tool call. A model
that fails it cannot do agent work under Claude Code at all.

### 4. Switch the local engines on

Each local engine has its own switch. The environment variable wins whenever it is set;
otherwise `[features]` in the project's config decides; otherwise the engine's default applies.

| Engine | Default | Environment | `vibey.toml` |
|---|---|---|---|
| `gptossloop` | on | `VIBEY_FEATURE_GPTOSSLOOP=0` switches it off | `[features] gptossloop = false` |
| `qwenloop` | off | `VIBEY_FEATURE_QWENLOOP=1` | `[features] qwenloop = true` |
| `claudeloop-local` | off | `VIBEY_FEATURE_CLAUDELOOP_LOCAL=1` | `[features] claudeloop_local = true` |

Before ADR-0064 the qwenloop switch turned on the engine that ran GPT-OSS; that engine is now
`gptossloop`, on by default. With the qwenloop switch on, `vibey worker` and `vibey doctor` print a
`note:` saying so; drop the switch unless you want Qwen as well.

claudeloop-local's own settings:

```toml
[engines.claudeloop_local]
profile = "local"             # the [profiles.NAME] above; VIBEY_CLAUDELOOP_LOCAL_PROFILE overrides
context_window = 32768        # keep equal to the profile's and the server's
structured_verdict = false    # claim it only once conformance proves it (below)
```

The worker reads `[features]` from the project's stored config, which no `vibey new` flag writes
yet, and `vibey doctor` reads `./vibey.toml`. The environment variables are the switches that
reach both: set them for `vibey doctor` and `vibey worker` alike.

### 5. Check, then record

```bash
vibey doctor                                   # lists every switched-on local engine
vibey doctor --conformance --record --engine claudeloop-local
vibey doctor --conformance --record --engine gptossloop
vibey doctor --conformance --record --engine qwenloop   # when switched on
```

**Do not leave a model warmed up at a large window.** Ollama reloads a model whose context
differs from a request's. A warm-up at a very large window, left resident, makes the first real
request pay for a reload with a key-value cache sized for that window, and on a laptop the
request can time out. `vibey doctor` prints an `ollama` line that says so when the loaded model's
context is above `VIBEY_OLLAMA_CONTEXT`, and names the fix: `ollama stop <the loaded model>`, the
Heretic tag with the default.

**A prompt that fills the window cuts the answer off.** GPT-OSS reasons before it answers, and its
reasoning counts against the same window as the prompt. A DESIGN prompt grows with every question
answered, and `response ... stopped: length` in `vibey llm tail` with `prompt N tokens + output M
tokens` adding up to `VIBEY_OLLAMA_CONTEXT` means the window, not the output budget, ran out.
Three settings meet it:

```bash
export VIBEY_OLLAMA_CONTEXT=16384
export VIBEY_OLLAMA_THINK=low
export VIBEY_OLLAMA_OUTPUT=6144
```

A bigger window stops the ledger being trimmed from the middle, `VIBEY_OLLAMA_THINK=low` keeps
the first attempt from spending itself reasoning, and a larger output budget leaves room to write
the design spec. The one retry also opens a larger window by itself, up to
`VIBEY_OLLAMA_RETRY_CONTEXT` (32768 by default), but it costs a model reload, so prefer sizing the
window right.

**A local model is slow to its first turn.** Conformance starts a real run and waits 30 seconds
for its run directory. GPT-OSS 20B on a laptop loads weights and answers a first turn well past
that, so `run_dir_shape`, `snapshot_schema`, `done_marker` and `structured_verdict` fail together
for a reason that is the host's speed, not the engine's. Tell conformance how long this host
needs:

```bash
VIBEY_CONFORMANCE_POLL_SECONDS=420 vibey doctor --conformance --record --engine gptossloop
```

Measure it rather than guessing: a window long enough to pass once is the number to keep, and one
far longer than the check ever uses costs nothing, because the wait ends the moment the files
appear.

`vibey doctor` runs `claudeloop doctor --profile <name>` for claudeloop-local, so the health check
probes the backend the run will use. The worker also re-runs each enabled local engine's `doctor`
before every BUILD selection; a local engine whose doctor fails is simply not eligible, and the
job goes to the next engine.

**STRUCTURED_VERDICT.** claudeloop-local does not claim a structured verdict by default. Set
`structured_verdict = true` only for a model you intend to hold to it: conformance then requires a
`VerdictRendered` event from the configured model, and a claim it cannot prove fails conformance
and makes the engine ineligible.

### Running unattended { #running-unattended }

A local run parks on gates that are not decisions: an interview question whose default is the
answer, an attempt budget you would grant again, a delivery that died with its worker. To let one
worker keep going through those, tell it so, for that run (`PROJECT_ID` is the id `vibey new`
printed or `vibey projects` lists):

```bash
caffeinate -i vibey -ddd worker --project PROJECT_ID --auto-answer
```

`caffeinate -i` keeps a Mac awake; leave it out on Linux.

`--auto-answer` answers the interview with each question's own default, grants ten more attempts
or six more repair rounds when a job runs out, and delivers a dropped job once more. It never
answers a spending gate, an approval or a review, and says which gates it left. It stops after
`--auto-answer-limit` answers (30) and says so. Each answer is on the ledger as `GateAnswered` by
`auto-answer`. Defaults take the `narrowest` scope, so a question that proposes adding something
the intake did not name is answered No: read the spec before `vibey design accept`.

To go on to BUILD without running `vibey design accept` yourself, add `--auto-accept-design`, and
`--accept-spec-json PATH` to import a spec you reviewed first. It accepts once DESIGN has
finished, through the same guards as the manual command, never opts into the visual stage, and
says what it will do at startup. This is your decision that the spec is right, made in advance,
so use it with a spec file you have read, not with whatever the model wrote. The ledger records
`accepted_by: auto-accept-design`.

Every unattended switch the worker has (`vibey worker --help`):

| Flag | What it decides for you | Never |
|---|---|---|
| `--auto-answer` | Interview defaults, more attempts or repair rounds, a dropped delivery | a spending gate, an approval, a review |
| `--auto-answer-limit N` | The most answers `--auto-answer` gives (default 30) | |
| `--auto-accept-design` | Accept the DESIGN spec once DESIGN finishes | VISUAL_DESIGN |
| `--accept-spec-json PATH` | With `--auto-accept-design`: import this reviewed spec first | |
| `--auto-accept-review` | Accept the REVIEW approval gate (`accept`) | `changes` or `cancel` |
| `--auto-finish-local` | Answer the deployment choice with `local_only` | `deploy` |
| `--auto-accept-all` | `--auto-accept-design`, `--auto-accept-review` and `--auto-finish-local` together | a deployment, a spending gate |
| `--auto-record-research-gaps` | Record a research topic that found no evidence as not researched, and go on | |
| `--autonomous` | `--auto-answer`, `--auto-accept-all` and `--auto-record-research-gaps` together | `--auto-publish`, a deployment, a spending gate |
| `--auto-publish` | Answer the publish interview with `accept_defaults`: a draft pull request, or a new private repository for a project with no remote | `custom`; it sends work to GitHub, so it is its own flag |
| `--local-max-turns N` | The turn limit of each local runner session, instead of the per-effort 8, 16, 40, 64 or 96; `unlimited` is allowed (also `VIBEY_LOCAL_MAX_TURNS`) | |

Each is for one worker and one project, not `--all-projects`.

### Research: what a local model can and cannot look up { #research }

Since [ADR-0102](../architecture/decisions/0102-local-first-search-and-a-provisioned-searxng.md),
local work can search the web, through a search engine on your own machine first:

- **DESIGN research** uses your own reading first: a `<topic>.md` in `VIBEY_EVIDENCE_DIR`, whose
  first line is `source: <where it came from>`. Without one, it searches a local SearXNG
  (`VIBEY_SEARXNG_URL`, else `http://127.0.0.1:28180`), and Brave only as a backup when SearXNG
  fails and `VIBEY_BRAVE_API_KEY` (or `BRAVE_SEARCH_API_KEY`) is set. It quotes what it finds,
  with its URLs, never from the model's recollection.
- **Only when both give nothing** does the research job park a `research_evidence` gate asking for
  `<topic>.md` ([ADR-0027](../architecture/decisions/0027-sovereign-design-provider.md)), or,
  with `[design.research] on_unavailable = "record_gap"` or `--auto-record-research-gaps`, record
  the topic as not researched and go on
  ([`[design.research]`](../reference/configuration.md#designresearch)).
- **BUILD sessions** are told the local SearXNG and how to run `vibey search` and `vibey fetch`,
  but never the Brave key, so a session's search has no backup.
- **Install the local SearXNG** with `vibey searxng install`; `vibey searxng status` says what is
  there ([`vibey searxng`](../reference/cli.md#vibey-searxng)). The worker prints which search it
  will use when it starts.

A local model still has no web access *of its own*: every search and fetch goes through vibey's
own tools, which treat what comes back as untrusted text.

### Watching the model think { #watching-the-model-think }

A DESIGN or DECOMPOSE call to a local model can run for many minutes, and by default it shows
nothing until it returns. Ask for the conversation and follow it from a second terminal:

```bash
vibey -ddd worker --project PROJECT_ID
vibey llm tail
```

`-ddd` makes the client stream Ollama's reply and write every request and every piece of the
reply to the wire log, `~/.local/state/vibey/llm-wire.jsonl`. `vibey llm tail` shows the request
(model, context, output budget, both messages), then the reasoning and the answer growing as they
are generated, then the model's own counts and tokens per second. A call that stalls shows as a
request with nothing after it, which is how a context window set too small or a model still
loading looks from the outside.

**BUILD and REVIEW too.** An engine session is a separate process, so the worker notes each one
in the same log and the tail follows it: a banner naming the engine, the work item and the run,
then every tool call (`turn 3 -> search {...}`) and a one-line result (`<- search: 3 found`,
`<- shell: exit 1 - ...` with the end of the output, where the failure is), the model's streamed
answer, its reasoning (`thinking: ...`), and each turn's time and tokens. When the next item
starts, the tail moves to its run on its own, so one terminal shows the whole project:

```text
[22:35:08] === gptossloop session - work item ws - run fb316537 ===
  turn 1 -> search {"glob": "*", "path": "", "query": "package.json"}
    <- search: 10 found
  turn 1 done - 3.1s (model 2.9s) - in 1346 tokens - out 58 tokens
  thinking: The spec wants a /ministry section; check what exists first.
  turn 2 -> shell {"argv": ["npm", "run", "typecheck"]}
    <- shell: exit 1 - src/app/ministry/page.tsx(4,10): error TS2305 ...
```

Text appears a word at a time, not a token at a time, because the log releases streamed text only
at whitespace: a credential the model repeats cannot then be split across two pieces and escape
redaction. The log holds your full prompts, so it is created readable by you alone; remove it
when you no longer need it. To log without `-ddd`, set `VIBEY_LLM_WIRE_LOG=path`.

### Measuring a capacity fit { #measuring-a-capacity-fit }

The sovereign DESIGN and DECOMPOSE providers reach Ollama through one client with two ceilings:
the context window it asks for (`num_ctx`: `VIBEY_OLLAMA_CONTEXT`, default `8192`, at least
`4096`) and the output it allows (`num_predict`: `VIBEY_OLLAMA_OUTPUT`, default `2048`).
`vibey doctor --sovereign-fit` measures what this host's server actually answers, and records it:

```bash
vibey doctor --sovereign-fit                   # writes ~/.local/state/vibey/sovereign-fit.json
vibey doctor --sovereign-fit --fit-output ./sovereign-fit.json
export VIBEY_OLLAMA_FIT=~/.local/state/vibey/sovereign-fit.json   # for work and worker
```

The probe is `scripts/sovereign_probe.py`, run with doctor's own interpreter against
`VIBEY_OLLAMA_URL` and `VIBEY_OLLAMA_MODEL`. It sends one JSON-mode chat request for each
combination of context `4096`, `8192` and output `512`, `1024`, `2048`, each with a 120-second
timeout. A combination is valid when the reply carries non-empty content, and the fastest valid
one becomes `selected_fit`. The record holds `measured_at`, `url`, `model`, `revision`
(`git rev-parse HEAD` in the directory doctor runs in, else `unknown`), `prompt_shape` (the
probe's own prompt size), every result, and `selected_fit`. With no valid combination doctor
prints `sovereign fit FAIL` and exits 1. The file is still written, with `selected_fit: null`,
which the client ignores.

Doctor does not export anything: set `VIBEY_OLLAMA_FIT` in the environment of `vibey work` and
`vibey worker`. The client then uses the record only when all of these hold:

- its `url` equals `VIBEY_OLLAMA_URL` (default `http://127.0.0.1:11434`) exactly, as a string, so
  a trailing slash is a different server;
- its `model` equals the model in effect: `--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else
  `VIBEY_SOVEREIGN_MODEL`, else `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE`
  (`heretic`);
- when `VIBEY_REVISION` is set, its `revision` equals it;
- its `selected_fit` is valid, with a context of at least `4096` and a positive output, and it
  carries a `prompt_shape`.

Otherwise (unset, unreadable, malformed or mismatched) the configured ceilings apply:
`VIBEY_OLLAMA_CONTEXT` and `VIBEY_OLLAMA_OUTPUT`, `8192` and `2048` by default.

A matching record replaces those two ceilings with its measured context and output, but only for a
request no larger than the prompt it was measured with (the record's system plus user characters).
A larger request falls back to the built-in ceilings, `8192` and `2048`, not to the two variables.
The probe's prompt is 42 characters today, so real DESIGN and DECOMPOSE prompts run on the
built-in ceilings: the record proves what the server answers at each size, not yet a working size
for a full ledger.

The probe script ships in the repository, not in the `vibey-engine` wheel. Doctor looks for it
beside the source tree it runs from, so `--sovereign-fit` works from a checkout (an editable
install) and fails with `sovereign fit FAIL` from a wheel install.

### 6. Run

```bash
vibey worker                                         # sovereign DESIGN/DECOMPOSE, local-first BUILD
vibey worker --engines gptossloop,claudeloop-local   # never fall back to a paid engine
```

- An explicit `--provider` always wins; `claudeloop` (paid) is never a default.
- Verification still rotates: gptossloop's work is reviewed by claudeloop-local (or qwenloop) and
  the other way round. With one local engine in the pool, the review goes to a paid engine if one
  is configured, or the engine reviews its own diff and the ledger says so
  ([ADR-0035](../architecture/decisions/0035-independence-is-the-default-not-an-absolute.md)).
- A run whose backend cannot serve it (the server down, a model not pulled or out of memory, a
  window too small) makes claudeloop exit **78**. The job parks with an `engine_misconfigured`
  gate naming the `doctor` command that shows the cause. Fix it, then answer the gate to retry:
  `vibey answer <gate-id> --raw '{}'`.
- **The Sabbath.** From sundown Friday to sundown Saturday the worker keeps running but claims
  nothing, and `vibey new` exits 75 (sub-doctrine 8.i,
  [ADR-0072](../architecture/decisions/0072-the-sabbath-kept-where-the-machine-stands.md)).
  `--ignore-sabbath` runs one command through the window and says so
  ([`[sabbath]`](../reference/configuration.md#sabbath)).

### Running Claude Code itself on Ollama (a storm)

The same server can carry the interactive Claude Code that drives a storm of lanes. These are the
variables a local claudeloop profile sets for Claude Code; export them in the shell that starts
`claude`:

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

Every model id must be one the server serves: an unset tier falls back to a `claude-*` id the
local server does not have.

### The honest ceiling { #the-honest-ceiling }

A local model is not the paid one it displaces, and the defaults say so:

- **One agent at a time on a 24 GB machine.** A 14-20B model at a 32K window fills it; a second
  concurrent agent evicts the first model (`OLLAMA_MAX_LOADED_MODELS=1`) or does not fit. Run
  `vibey worker -j 1` and one storm lane at a time.
- **Effort tops out at STANDARD.** claudeloop-local's HIGH and MAX run the profile's top tier and
  report `achieved=STANDARD`, so rotation sees a local model for what it is.
- **Use the endpoint-specific tool smoke before a storm.** `qwen2.5-coder:14b` can write tool
  calls as text or misclassify the `qwenloop-verdict` fence when served locally. On the machine
  this was measured on, `qwen3:14b` produced a native `read_file` call through Ollama's
  OpenAI-compatible endpoint, so it is the checked-in storm example. This is a compatibility
  observation, not a guarantee for every serving template; keep the runner's tool smoke and
  bounded completion guard enabled.
- **Research uses your own search first.** See [Research](#research):
  a local SearXNG, then Brave if you set a key, then a gate or a recorded gap. With neither
  search nor evidence files, research still needs you.
- **A paid fallback is visible, not yet announced.** When no local engine is eligible the job goes
  to a paid engine; `vibey engines` and the local engine's health show why, but nothing is
  written to the ledger at that moment yet. Pin the pool with `--engines` if a paid run is never
  acceptable.

### Model families

`vibey models` lists the families vibey knows by name (Qwen Coder, DeepSeek Coder, Codestral,
StarCoder, Gemma, Llama, CodeLlama and CodeGemma), each with a tag to start from and the
`ollama pull` that fetches it, and then what the Ollama on this machine actually has and says each
model can do. Run it before you choose.

What matters is whether a model reports `tools`. The BUILD runner works through tool calls. A
model that reports none is driven through a **text tool-call protocol** instead
(`tool_protocol = "auto"` in the runner's config; `native` and `text` force either way): its tools
are described in the prompt, it writes each call as `<tool_call>{...}</tool_call>`, and the run
says when this is in use. It is about twice as slow per turn, and in the measurement behind
ADR-0093 it did not make such models build correctly, so reach for it to see what a model does,
not to expect a result. Such a model is also good for DESIGN and DECOMPOSE, which ask for JSON and
need no tool-calling. A model whose capabilities your Ollama does not report is shown as unknown,
and left native.

On a small BUILD task Llama 3.1 8B was correct 0 times in 8 (native or text) and stock
`gpt-oss:20b`, the default when it was measured, 1 time in 3; the Heretic build has not been
measured on it. Give a model that reports a large default context (Llama 3.1 does: 131,072) a
`num_ctx 32768` derived model before you judge its speed; the first Llama run here took 8 minutes
to load without it.

Reporting `tools` is necessary, not sufficient: Qwen2.5-Coder 14B reports it and still writes its
calls out as text. Only a run shows whether a model uses them well. The measurements behind the
list, and why a template check is not enough, are in
[ADR-0093](../architecture/decisions/0093-local-model-families-are-named-and-measured-not-assumed.md).

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| doctor: `model '...' is not served by http://127.0.0.1:11434/v1 ...; pull it first` | The default model is not in Ollama | `ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` |
| The first request times out after a warm-up | The model is resident at a larger window than requests use | `ollama stop <the loaded model>` (doctor names it) |
| `response ... stopped: length` in `vibey llm tail` | The prompt and reasoning filled the window | Raise `VIBEY_OLLAMA_CONTEXT`, set `VIBEY_OLLAMA_THINK=low`, raise `VIBEY_OLLAMA_OUTPUT` |
| `run_dir_shape`, `snapshot_schema`, `done_marker` and `structured_verdict` fail together | The host is slower than conformance's 30-second wait | `VIBEY_CONFORMANCE_POLL_SECONDS=420 vibey doctor --conformance --record --engine gptossloop` |
| An `engine_misconfigured` gate, claudeloop exit 78 | The backend cannot serve the run | Run the doctor command the gate names, fix it, then `vibey answer <gate-id> --raw '{}'` |
| A `research_evidence` gate | No evidence file and no search result | `vibey searxng install`, add the file, or `--auto-record-research-gaps` |
| A job ran on a paid engine | No local engine was eligible | `vibey engines`; pin `--engines` to local ones |
| `sovereign fit FAIL` from a wheel install | The probe script is not in the wheel | Run `--sovereign-fit` from a source checkout |
| The worker claims nothing on a Friday evening | The Sabbath window | Wait, or `--ignore-sabbath` for one command |
| Two ~13 GB models on disk | The VS Code extension or the Helm chart runs stock | Set `vibey.model` or `ollama.model` to the Heretic tag |

## Where next

- [VS Code extension](vscode-extension.md): give the same local model a task from your editor.
- [Run agents on your own hardware](outcomes/run-agents-on-your-own-hardware.md): the same path
  told as an outcome.
- [Configuration reference](../reference/configuration.md): every `[features]`, `[engines]` and
  `[design.research]` key.

## Say it in one line

vibey runs on Heretic v2 of GPT-OSS 20B in Ollama by default, local engines first and free per token; one agent at a time, effort up to STANDARD.
