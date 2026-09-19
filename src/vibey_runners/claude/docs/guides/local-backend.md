# Running for free on a local backend (Ollama)

`claudeloop` drives Claude Code. Claude Code talks to a model over the
Anthropic Messages API — and a growing number of servers speak that API
locally, [Ollama](https://ollama.com) among them. A **backend profile** points
a run at one of those servers instead of Anthropic. Claude Code still runs the
agent loop, the tools and the file edits; only the model behind it changes,
and it costs nothing.

It is a real trade, not a free lunch: see [What to expect](#what-to-expect)
before you point a long unattended run at a 14B model.

## Quick start

1. Serve a model **that makes real tool calls** through the server's Anthropic
    endpoint. For Ollama:

    ```bash
    ollama pull your-model:tag
    ```

    Any server that answers `POST /v1/messages` in the Anthropic format works;
    this was verified against Ollama 0.34.2 on `http://127.0.0.1:11434`. Not every
    model qualifies — `qwen2.5-coder:14b`, tested here, does **not** (see
    [What to expect](#what-to-expect)); step 3's `doctor` tells you which do.

2. Describe it in `claudeloop.toml` (or `~/.config/claudeloop/config.toml`):

    ```toml
    [profiles.local]
    base_url = "http://127.0.0.1:11434"
    model_low = "your-model:tag"
    model_medium = "your-model:tag"
    model_high = "your-bigger-model:tag"
    small_fast_model = "your-small-model:tag"
    context_window = 32768
    max_output_tokens = 8192
    ```

3. Check it, then run it:

    ```bash
    claudeloop doctor --profile local
    claudeloop run plan.md --profile local
    ```

    `CLAUDELOOP_PROFILE=local`, or `profile = "local"` at the top of the file,
    selects it without the flag.

## What a local profile changes

A profile is *local* when it has a `base_url`. Every one of these follows from
that, and each has a reason:

| | Anthropic (default) | Local profile |
|---|---|---|
| Endpoint | Anthropic | `base_url` → `ANTHROPIC_BASE_URL` |
| `ANTHROPIC_API_KEY` | inherited | **blanked** (`""`), so a paid key never leaves the machine |
| Token | your Anthropic login | `auth_token` (default `"ollama"`), or the variable named by `auth_token_env` |
| Model tiers `low`/`medium`/`high` | `claude-sonnet-4-5` / `claude-opus-4-6` / `claude-fable-5` | **must be named** — those ids do not exist on a local server |
| A `claude-*` model id | fine | **refused**, from `--model`, the profile, or `claudeloop model` on a live run |
| Claude Code's haiku / sonnet / opus aliases | Anthropic's | mapped to `small_fast_model` / `model_low` / `model_medium`, so no `claude-*` id is ever sent |
| Cost per turn | what Claude Code reports | **$0** (`cost_mode = "zero"`); token counts kept |
| `--max-budget-usd` to Claude Code | forwarded | not forwarded |
| `--effort` to Claude Code | forwarded | not forwarded (`pass_effort = false`) |
| Telemetry / update checks | Claude Code's default | off (`CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`) |
| Web search, deep research | available | **refused** — they are Anthropic server-side tools |
| Completing on the done-marker text alone | allowed (fallback) | **off** (`done_marker_fallback = false`) — only a structured verdict completes a run |
| Capacity probe | Anthropic | the same backend as the turns |

### Why cost is recorded as zero

Claude Code prices a model it does not recognise at its default model's rate —
it even says `costUSD is a guess`. Captured on this change's live smoke run:
one `"Reply OK"` probe to a local `qwen2.5-coder:1.5b` reported **$0.00085**, and
one 14,233-token turn to `qwen2.5-coder:14b` reported **$0.0737**. Nobody spent
either. Left alone, that figure feeds Claude Code's own `--max-budget-usd`,
claudeloop's 80% budget downgrade, its dollar cap, and any supervisor's spend
brake (vibey sums `turn.completed.cost_usd`). With `cost_mode = "zero"` each
turn is recorded at $0 and the guess is kept on the raw event as
`reported_cost_usd`, for the record. `input_tokens` / `output_tokens` are kept
on every `turn.completed` event — they are also what tells a tool-only turn
from an empty response now that cost cannot.

`cost_mode = "zero"` is refused on an Anthropic profile: there it would hide
real spend.

## When the backend cannot serve the run

A local server fails in ways Anthropic does not, and none of them is fixed by
waiting. Each used to be read as *Available* and the turn re-sent until the
turn budget ran out. They are now a terminal capacity state,
`BackendMisconfigured`, and `run` / `resume` exit **78**:

| What happened | What Claude Code reports | `reason` |
|---|---|---|
| The model is not pulled (any backend, Anthropic included) | `error: "model_not_found"`, HTTP 404 | `model_not_found` |
| `base_url` points at the wrong path | HTTP 404 | `endpoint_not_found` |
| The server is not running | `error: "server_error"`, no status, "Connection refused" | `unreachable` |
| The model failed to load — usually out of memory | HTTP 500 | `model_load_failed` |
| The conversation does not fit `context_window` | `error: "invalid_request"`, "Prompt is too long" | `context_too_small` |

The failure reason names the backend's own words, and the run points you at
`claudeloop doctor --profile NAME`. Each row was captured from the Claude Code
CLI bundled with claude-agent-sdk, against Ollama 0.34.2 or a stub returning
Ollama's own error bodies; the payloads are pinned in
`tests/domain/test_classify.py`.

One local error *is* fixed by a clock: Ollama answers **503** when its request
queue is full (`OLLAMA_MAX_QUEUE`). That is `WindowExhausted` with
`rate_limit_type = "local"`, and the run waits and probes like any other
window.

Claude Code retries a refused connection itself before claudeloop ever sees
it — up to `CLAUDE_CODE_MAX_RETRIES` times, which takes about three minutes at
the default. To give up sooner, set it in the profile:

```toml
[profiles.local]
extra_env = { CLAUDE_CODE_MAX_RETRIES = 2 }
```

## `doctor --profile`

For a local profile, `claudeloop doctor --profile local` replaces the Anthropic
login check with four that matter here:

- **backend-auth** — the token resolves (an `auth_token_env` that is unset
  fails here, not three hours into a run);
- **backend** — `base_url` answers (it asks `GET /v1/models`, then Ollama's
  `GET /api/tags`);
- **backend-models** — every model the profile names is present, with the
  `ollama pull` line for the first one that is not;
- **backend-tools** — each tier, asked once to call a trivial tool through the
  server's Anthropic endpoint, answers with a real `tool_use` block. Claude Code
  acts *only* through tool calls; a model that writes them out as text changes
  nothing, however long it runs. This is the check to trust before a long run.

`doctor` also looks for Claude Code in the order the SDK does — a profile's
`cli_path`, then the CLI bundled with claude-agent-sdk, then `claude` on
`PATH` — so it checks the CLI a run will really launch, and no longer fails a
machine (or container) with no global install.

## Resuming

Run meta (`.claudeloop/runs/<id>/meta.json`) records `backend` —
`anthropic`, `gateway:<url>` for an `ANTHROPIC_BASE_URL` you set yourself, or
`local:<url>` — and `profile`. `claudeloop resume` refuses, with exit 2, to
continue a session last run against a different backend: a transcript made by
one model server is not replayed on another. Select the profile the session
was started with. Runs from before this was recorded carry no backend and are
not refused.

## What to expect

A local model is not Claude, and Claude Code's agent loop leans on reliable
tool calling and a large context. Measured on this change's live smoke run —
Claude Code 2.1.259 (bundled with claude-agent-sdk 0.2.152), Ollama 0.34.2,
`qwen2.5-coder:14b` (Q4_K_M) on an Apple-silicon Mac, a one-line plan
("create `hello.txt` containing `hello from ollama`"):

- **`doctor --profile local`** — CLI, token, reachability and models all pass;
  **`backend-tools` fails** in about four seconds: asked to call one trivial
  tool, `qwen2.5-coder:14b` answers with the call written out as JSON text
  (`{"name": "record_answer", "arguments": …}`), not a `tool_use` block. A bare
  `curl` to Ollama's `/v1/messages` shows the same, so this is the model behind
  Ollama's Anthropic endpoint, not claudeloop or Claude Code.
- **A profile pointing at a port nothing listens on** — the run ends with exit
  78, `backend misconfigured (unreachable): API Error: Connection refused …`,
  after about three minutes of Claude Code's own retries.
- **`context_window = 32768`, no `max_output_tokens`** — the capacity probe
  answered (recorded at $0; Claude Code guessed $0.00085). The first turn took
  about two minutes, sent 14,233 input tokens (Claude Code guessed $0.0737),
  wrote the `Write` call as text, and ended "Prompt is too long". Claude Code
  then auto-compacted before every further request — about 95 seconds each on
  this machine — and the model kept writing its tool calls as text. Stopped by
  hand; no file was written.
- **With `max_output_tokens = 8192` added, before the guards in this change** —
  one two-minute turn. The model wrote its `Write` call as text; when Claude Code
  demanded the structured verdict it wrote *that* as text too, then typed the
  done marker. claudeloop reported **Done, exit 0 — and `hello.txt` was never
  created.** That false completion is why a local profile now turns the
  done-marker fallback off and why `doctor` checks `backend-tools`.
- **The same run on this change's code** — the turn again wrote its tool call as
  text, the marker no longer counted, and the run ended `budget exhausted`,
  exit 1: an honest failure instead of a false success.

In short: the plumbing — routing, $0 accounting, error classification, the
probe, `doctor` — works end to end against Ollama; **`qwen2.5-coder:14b` does
not make tool calls through Ollama's Anthropic endpoint, so it cannot do agent
work under Claude Code at all.** Use a model that passes `backend-tools`.

Things that follow from that:

- **Size the window honestly.** Claude Code's own system prompt and tool
  definitions are about 14,000 tokens before your plan. Claude Code also
  reserves `max_output_tokens` out of `context_window`, so set both: a
  `context_window` of 32768 with no `max_output_tokens` left too little room: the
  first turn was refused as "Prompt is too long" (now `context_too_small`,
  exit 78) and Claude Code compacted before every request after it. The server must actually
  serve that window too (for Ollama, `OLLAMA_CONTEXT_LENGTH` or the model's
  `num_ctx`).
- **Pick a model that emits real tool calls** through the server's Anthropic
  endpoint — `doctor`'s `backend-tools` check asks each tier directly. A model
  that writes its tool call out as JSON text has not called anything, and the
  run will not make progress.
- **Expect minutes per turn**, not seconds: Claude Code's prompt is large, and a
  14B model on a laptop took about two minutes for one turn here.
- **Keep the plan small** and the turn budget (`--max-turns`) bounded while you
  find out what your model can do.

## Keys

The full key table — defaults, and the Claude Code environment variable each
one sets — is in the
[configuration reference](../getting-started/configuration.md#backend-profiles).
