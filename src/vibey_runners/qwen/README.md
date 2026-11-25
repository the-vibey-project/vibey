---
description: "Reference for gptossloop and qwenloop, the local-model session runner inside vibey-engine: every command, setting, default, tool and exit code."
---

# qwenloop and gptossloop: run a coding agent on a model you host

> [!IMPORTANT]
> **Bottom Line Up Front (BLUF):** This package is vibey's local-model session runner. It installs
> two commands: `gptossloop`, the sovereign default engine on GPT-OSS 20B (the Heretic v2 build,
> ADR-0099), and `qwenloop`, the opt-in twin on Qwen3 14B. It ships inside `vibey-engine`. With
> Ollama running, `ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` (about
> 12.1 GB) and `gptossloop doctor` are all it takes before `gptossloop run plan.md` runs a plan on
> your own machine, with no per-token bill.

> [!IMPORTANT]
> **Work in progress — not a final product:** `qwenloop`, `gptossloop`, and `vibey` are in active development and not a final product. Folks will be notified on the [Discord server](https://discord.gg/Qvu8aYnVS) once the product is finally done.

> **Now part of the vibey monorepo.** `qwenloop` lives in [the-vibey-project/vibey](https://github.com/the-vibey-project/vibey) at [`src/vibey_runners/qwen`](https://github.com/the-vibey-project/vibey/tree/develop/src/vibey_runners/qwen) (vibey ADR-0021). It is not published on its own any more: it ships inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/) package, so `pip install vibey-engine` installs it (vibey ADR-0037).

[![CI](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/ci.yml)
[![Provenance](https://github.com/the-vibey-project/vibey/actions/workflows/provenance.yml/badge.svg)](https://github.com/the-vibey-project/vibey/actions/workflows/provenance.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Model: Apache--2.0](https://img.shields.io/badge/model-Apache--2.0-orange.svg)](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct)

## How to read this page

Daniel had the page open on his phone, scrolling past table after table.

**Daniel:** Professor, do I read all of this before I run anything?

**Professor Feynman:** No. Think of it as the manual in a car's glove box. You read the first
page, drive, and open it again when a light comes on. Do the quick start. Come back to the
settings table when you want to change a default, and to "When it goes wrong" when a command
exits with a number you do not recognise.

**Daniel:** And the two names? Two programs?

**Professor Feynman:** One program wearing two name badges. Each badge asks for a different
model and reads its own settings. Everything else is the same.

## The two engines

One runner, two commands (vibey ADR-0064). The code is `src/qwenloop/domain/config.py`
(`GPTOSSLOOP`, `QWENLOOP`).

| Engine | Model it asks an endpoint for | Settings it reads | Config file | In vibey |
|---|---|---|---|---|
| `gptossloop` | `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` (GPT-OSS 20B, Heretic v2, ADR-0099) | `GPTOSSLOOP_*` | `<user config dir>/gptossloop/config.toml` | the sovereign default engine, on unless switched off |
| `qwenloop` | `qwen3:14b` (Qwen3 14B) | `QWENLOOP_*` | `<user config dir>/qwenloop/config.toml` | opt-in (`VIBEY_FEATURE_QWENLOOP=1`) |

Each reads only its own settings, so naming a model for one never changes the other's. Everything
else is shared: the verbs (`run`, `stop`, `wind-down`, `prompt`, `doctor`, …), the run records in
`.qwenloop/runs/<run-id>/`, the `QWENLOOP_TASK_FULLY_COMPLETE` marker, the `qwenloop-verdict`
fence, and the pinned llama.cpp/vLLM profiles.

- **Why Heretic v2 for gptossloop.** It is GPT-OSS 20B with its refusal direction removed, at the
  same size and memory footprint as stock. A coding agent that declines its work is a stalled
  loop (ADR-0099, `src/vibey/domain/sovereign_model.py`). Stock `gpt-oss:20b` is still available:
  set `GPTOSSLOOP_MODEL=gpt-oss:20b`, or, through vibey, `VIBEY_SOVEREIGN_MODEL=stock`.
- **Why Qwen3 for qwenloop.** The runner drives native tool calls, and `qwen2.5-coder:14b` on
  Ollama writes its calls out as text. Before ADR-0064 the bare `qwenloop` asked for GPT-OSS; that
  is now `gptossloop`'s job.

The runner attaches to a server that is already running, such as Ollama, or starts its own: a
portable llama.cpp Q5_K_M profile, or BF16 through vLLM on Linux NVIDIA systems with at least
40 GiB of usable VRAM. Both managed profiles are pinned to Qwen2.5-Coder 14B. The examples below
use one engine; every one works the same with the other and its own settings.

Model installation is always explicit. The package, its tests, `doctor`, and vibey never download
model weights for you.

## Install

`qwenloop` and `gptossloop` ship inside the [`vibey-engine`](https://pypi.org/project/vibey-engine/)
package (vibey ADR-0037):

```bash
uv tool install vibey-engine    # or: pipx install vibey-engine / pip install vibey-engine
```

That installs both commands. Check it worked:

```bash
gptossloop --version
```

You should see `gptossloop` followed by the version, for example `gptossloop 0.4.0`.

In vibey, `gptossloop` is on by default (switched off by `VIBEY_FEATURE_GPTOSSLOOP=0` or
`[features] gptossloop = false`); `qwenloop` is a separate opt-in (`VIBEY_FEATURE_QWENLOOP=1`, or
`[features] qwenloop = true`).

## Quick start with Ollama

1. Pull the model the engine asks for. For `gptossloop`:

   ```bash
   ollama pull hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE
   ```

   For `qwenloop` instead:

   ```bash
   ollama pull qwen3:14b
   ```

2. Point the engine at Ollama's OpenAI-compatible address (the `/v1` is part of it):

   ```bash
   export GPTOSSLOOP_BASE_URL=http://127.0.0.1:11434/v1
   ```

   With nothing configured and a local Ollama running, the `auto` backend picks Ollama anyway
   (see [How `auto` picks a backend](#how-auto-picks-a-backend)), so this step only makes the
   choice explicit.

3. Check that the endpoint answers and serves the model:

   ```bash
   gptossloop doctor
   ```

   You should see lines naming the backend, the endpoint and `model: <tag> ok`, and exit status 0.
   If the model is not pulled you see `model: <tag> unavailable` and exit status 1.

4. Run a plan in a git worktree:

   ```bash
   gptossloop run plan.md --cwd .
   ```

   The run id is generated unless you pass `--run-id`. The run writes its records under
   `.qwenloop/runs/<run-id>/` and exits 0 when the plan is complete.

The pinned llama.cpp profile is the other path, for a machine with no Ollama:

```bash
qwenloop model install --profile portable
qwenloop model verify
qwenloop doctor
qwenloop run plan.md --run-id <uuid> --cwd <worktree>
```

Replace `<uuid>` with any id you choose and `<worktree>` with the git worktree the run may edit.

## How vibey drives this runner

- **Endpoint and model.** vibey has one local setting, `VIBEY_OLLAMA_URL`. When it is set and the
  runner's own variable is not, vibey hands `gptossloop` `GPTOSSLOOP_BASE_URL=<VIBEY_OLLAMA_URL>/v1`
  and `GPTOSSLOOP_MODEL` from `--ollama-model`, else `VIBEY_OLLAMA_MODEL`, else
  `VIBEY_SOVEREIGN_MODEL`, else the Heretic v2 default. `qwenloop` gets only `QWENLOOP_BASE_URL`;
  it runs the Qwen model it names itself
  (`src/vibey/infrastructure/engines/local_engines.py`, `LocalEndpointEnvironment`).
- **Capability snapshot.** vibey hands a BUILD run its capability snapshot with
  `--capabilities PATH`: the `capabilities.json` it wrote into the run's own folder (ADR-0103).
  With it, the run reaches exactly the snapshot's MCP servers (never `~/.claude.json` or
  `QWENLOOP_MCP_CONFIG`), reads the snapshot's skills and plugin commands on demand
  (`skills_list`, `skill_read`), and carries a capability block in its system prompt: the skill
  and server listing, then the repository's `CLAUDE.md` and `AGENTS.md`, together within
  `[loops] capability_prompt_tokens`. A file that does not fit is named with its size, never cut.
  The run's first event is `capabilities.applied` (counts and names only). A document that is
  refused or cannot be read exits `78` before any model is started or called. `--capabilities`
  goes with a PLAN, never with `--storm`.
- **Web search.** The `web_search` and `web_fetch` tools run vibey's own `vibey search` and
  `vibey fetch`, so they use the local SearXNG the worker named (ADR-0102). They work only in a
  session a vibey worker started (the `WEBSEARCH_PROVIDER` variable is set); anywhere else the
  model is told web search is not set up. A session is never given a Brave key.

## Commands

Run `qwenloop --help` or `gptossloop --help` for the same list. Source:
`src/qwenloop/cli/app.py`.

| Command | What it does |
|---|---|
| `run [PLAN]` | Drive a plan to completion, or sweep repositories with `--storm` (flags below). |
| `doctor` | Exit 0 only when a run could start: with an endpoint, that it answers and serves the model; otherwise that `llama-server` or `vllm` is installed. Takes `--backend`, `--base-url`, `--model`. |
| `prompt RUN_ID TEXT [--cwd DIR]` | Send a running run a follow-up; the model reads it at the start of its next turn, once, in the order sent. Recorded as a `prompt.received` event and moved to `control/ack` when taken. |
| `stop RUN_ID [--cwd DIR]` | Ask the run to stop. |
| `wind-down RUN_ID [--cwd DIR]` | Ask the run to finish its turn and exit `75`. |
| `whoami` | Print `{"identity": "local", "provider_dollars": 0, "owner": <uid>}`. |
| `usage [--cwd DIR]` | Print how many runs `.qwenloop/runs/` holds, and `provider_dollars: 0`. |
| `model list` / `inspect` / `verify` / `install --profile portable\|nvidia-bf16` / `remove PROFILE --yes` | The pinned managed-server profiles. `install` downloads only the portable GGUF; the BF16 snapshot is installed through vLLM/Hugging Face. `remove` refuses to delete and tells you to move the directory to the Trash. |
| `server status` / `start` / `stop` | The managed server, or a check that the configured endpoint is ready. `stop` stops a managed server only; an attached endpoint is never stopped. |
| `server turn-worker` | Host the model behind the RabbitMQ shared-turn mode. Exits 2 unless `turn_dispatch_mode = "rabbitmq"` and `turn_queue_url` are set. |
| `server benchmark [--samples N] [--concurrency N]` | Measure direct against hybrid dispatch (defaults 3 and 2) and save the faster mode to `<user cache dir>/<engine>/dispatch-benchmark.json`, which `turn_dispatch_mode = "auto"` reads. |
| `tool approve NAME` / `tool deny NAME` | Print an approval or denial for the active run. |
| `--version` | Print the engine name and version. |

These commands exist for parity with the paid runners and print a one-line pointer to `status`
and the run artifacts instead of acting: `resume`, `status`, `logs`, `watch`, `snapshot`,
`reset`, `runs`, `sessions`, `threads`, `agents`, `savepoints`, `unwind`, `capacity`, `models`,
`effort`, `preset`, `permission-mode`, `approval`, `sandbox`, `cwd`, `slash`, `hooks`, `config`,
`attach`, `unattach`, `folder`, `skill`, `plugin`, `connector`, `memory`, `artifact`, `github`,
`research`, `web-search`, `chat`, `response`, `voice`, `speak`, `cloud`, `api`.

### `run` flags

| Flag | Default | Meaning |
|---|---|---|
| `PLAN` | none | The plan file. Required unless `--storm`. |
| `--run-id` | a new UUID | Name the run. |
| `--cwd` | `.` | The worktree the run works in. |
| `--effort` | `standard` | `standard`, `ultra` or `extreme`. `ultra` and `extreme` raise the turn limit from 40 to 120 when no turn limit is set. |
| `--preset` | `standard` | Accepted for parity and ignored. |
| `--backend` | config `backend`, else `auto` | `auto`, `llama.cpp`, `vllm` or `openai-compat`. |
| `--max-turns` | config `max_turns`, else 40 | Turn limit. |
| `--base-url` | `<PREFIX>_BASE_URL`, else config `base_url` | OpenAI-compatible base URL, `/v1` included. |
| `--model` | `<PREFIX>_MODEL`, else config `model`, else the engine's default | Model name the endpoint serves. |
| `--capabilities` | none | The capability document vibey wrote; refused documents exit 78. |
| `--desktop-notifications` / `--no-desktop-notifications` | on | Lifecycle desktop alerts; macOS alerts use the Ping sound. |
| `--storm` | off | Sweep every repository's open backlog instead of running a plan. |
| `--max-attempts` | `3` (1 to 10) | Storm: repair iterations per item before reporting a blocker. |
| `--owner` | `adammatthewsteinberger` | Storm: the GitHub owner whose repositories are discovered (needs `gh`). |
| `--repos-root` | `~/git` | Storm: where the cloned repositories are looked for. |
| `--repo` | discovery | Storm: restrict to this repository (repeatable). |
| `--author` | `Adam Matthew Steinberger` | Storm: the author name passed to `vibey-gh paper`/`book`. |

## Storms use Convergence-Driven Development

Storm mode applies **Convergence-Driven Development (CDD)** above
Specification-Driven Development (SDD) and Test-Driven Development (TDD).
Each open issue or pull request receives its own bounded run. Before editing,
the plan grounds the model in `git ls-files`, the tracked manifests, the actual
language and package layout, and the relevant tests. The model must map the
item's criteria to code, executable checks and evidence; run the checks; inspect
the diff and working tree; and report `criteria`, `tests`, `repository`,
`levels`, `trajectory`, `composition`, and `delivery` in its final verdict.
`levels` covers the overall project vision, phase/milestone, feature set/epic, and
feature/unit/user story; an item cannot hide divergence in a wider scope.
If the repository is one atom in a multi-project product or platform, report
the molecule-level interaction trajectory as well.
`composition` identifies atom, molecule and organism-level interactions, or
explicitly records that a higher-order composition is not applicable.

Every iteration classifies itself as converging, neutral or diverging against
the remaining work. A small divergence is allowed only when it has a bounded
path to reconvergence; a large or pathless divergence is abandoned. A failed
item gets bounded repair attempts before the storm reports a blocker, and the
storm never advances to another item while the current one is unresolved.
Configure the repair bound with `--max-attempts` (default `3`):

```bash
qwenloop run --storm --max-attempts 3 --desktop-notifications
```

The local runner prepares verified, commit-ready work. It does not push or
create pull requests from inside a model run; remote publication is a separate
explicitly authorized checkpoint. A marker, verdict, generated file or large
amount of activity is not completion evidence by itself. See the repository's
[CDD guide](../../../docs/guides/convergence-driven-development.md), governance
canon (sub-doctrine 9.c), and ADR-0039.

## Backends

### Inference profiles

| Profile | Backend | Intended hardware | Model installation |
|---|---|---|---|
| `portable` (`qwen2.5-coder-14b-q5-k-m`) | llama.cpp Q5_K_M | Apple Silicon, Linux CPU, supported offload GPUs | Explicit `qwenloop model install --profile portable` |
| `nvidia-bf16` (`qwen2.5-coder-14b-bf16`) | vLLM BF16 | Linux NVIDIA with at least 40 GiB free VRAM | Operator-managed pinned Hugging Face/vLLM cache |

Managed servers bind to loopback and require a per-launch bearer token. The runner never silently
changes backend during a run.

### How `auto` picks a backend

`src/qwenloop/application/backend_selection.py`, in this order:

1. An explicit `--backend` or config `backend` wins.
2. A configured base URL selects `openai-compat`.
3. With nothing configured, a local Ollama that is running selects `openai-compat` at
   `http://127.0.0.1:11434/v1`.
4. Linux with an NVIDIA GPU of at least 40 GiB usable VRAM and `vllm` installed selects `vllm`.
5. Otherwise `llama.cpp`, the portable profile.

### Attach to Ollama, or any OpenAI-compatible endpoint

The `openai-compat` backend attaches to an inference server that someone else runs instead of
spawning `llama-server` or `vllm`. Ollama is the main target, but any server that answers
`GET /models` and `POST /chat/completions` under its base URL works: LM Studio, a vLLM someone
else runs, or a hosted gateway.

The runner never owns an attached server. `server start` checks that the endpoint answers and
serves the configured model, and fails with a message naming which check failed. `server stop`
leaves it alone. `--backend openai-compat` with no base URL attaches to Ollama's default address,
`http://127.0.0.1:11434/v1`. `run`, `run --storm`, `server start`, and `server status` all use the
same backend. A run records the endpoint URL in place of a pinned revision and digest, because the
endpoint manages the model, not the runner.

Ollama must be able to hold `context_window` tokens. Set its own context length
(`OLLAMA_CONTEXT_LENGTH`, or the model's `num_ctx`) to at least `context_window`, or lower
`context_window` to match. Otherwise Ollama quietly drops the start of a long prompt, which the
runner has already trimmed to `context_window`.

## Settings

Each engine reads its own environment variables: `GPTOSSLOOP_*` for `gptossloop`, `QWENLOOP_*`
for `qwenloop` (written `<PREFIX>_*` below). A flag beats an environment variable, which beats the
config file, which beats the default.

| Setting | Flag | Environment | Config key | Default |
|---|---|---|---|---|
| Endpoint base URL | `--base-url` | `<PREFIX>_BASE_URL` | `base_url` | unset |
| Model name sent to the endpoint | `--model` | `<PREFIX>_MODEL` | `model` | `hf.co/mradermacher/gpt-oss-20b-heretic-v2-GGUF:MXFP4_MOE` (gptossloop), `qwen3:14b` (qwenloop) |
| Endpoint API key | — | `<PREFIX>_API_KEY` | — | none, so no `Authorization` header is sent |
| Endpoint probe timeout (seconds) | — | — | `endpoint_timeout_seconds` | `5` |
| Model request timeout (seconds; `0` waits indefinitely) | — | — | `idle_timeout_seconds` | `900` |
| Backend | `--backend` | — | `backend` | `auto` |
| Turn limit | `--max-turns` | — | `max_turns` | `40` |
| Consecutive empty replies retried before a run fails | — | — | `max_empty_reply_retries` | `2` |
| Tool-call protocol: `auto` carries calls as text for a model whose Ollama reports no tool-calling, `native` and `text` force either | — | — | `tool_protocol` | `auto` |
| Characters of each tool-call argument value recorded in `events.jsonl` | — | — | `max_recorded_argument_chars` | `200` |
| Characters of an empty reply's reasoning recorded as an excerpt | — | — | `empty_reply_reasoning_excerpt_chars` | `400` |
| Characters of one tool result shown to the model (the rest is cut, and the cut named) | — | — | `max_tool_result_chars` | `12000` |
| Server startup wait (seconds) | — | — | `startup_timeout_seconds` | `180` |
| Context window (tokens) | — | — | `context_window` | `32768` |
| Turn dispatch mode | — | — | `turn_dispatch_mode` | `auto` |
| Hybrid lane concurrency | — | — | `hybrid_concurrency` | `2` |
| RabbitMQ URL (required for shared mode) | — | — | `turn_queue_url` | unset |
| RabbitMQ request queue | — | — | `turn_queue_name` | `vibey.llm.turns` |
| Managed portable profile name | — | — | `portable_profile` | `qwen2.5-coder-14b-q5-k-m` |
| Managed NVIDIA profile name | — | — | `nvidia_profile` | `qwen2.5-coder-14b-bf16` |

`portable_profile` and `nvidia_profile` are checked for validity, but nothing uses them yet.

The config file is TOML, read from `$<PREFIX>_CONFIG`. When that is unset, it is read from
`<user config dir>/<engine>/config.toml`: for qwenloop
`~/Library/Application Support/qwenloop/config.toml` on macOS and
`~/.config/qwenloop/config.toml` on Linux, and the same under `gptossloop/` for gptossloop. A
missing default file is fine. A missing file named by `<PREFIX>_CONFIG`, invalid TOML, an unknown
key, or a base URL that is not `http(s)://` stops the command with exit code 2 and a message
naming the problem. The API key is read only from the environment: it never goes in a file or on
a command line.

### Turn dispatch

`turn_dispatch_mode = "auto"` (the default) uses the persisted per-device benchmark winner from
`server benchmark`, and falls back to direct until a benchmark has completed. Set it to
`"direct"` to keep one model turn local to the run. Set it to `"hybrid"` to multiplex up to
`hybrid_concurrency` lane turns through one resident inference server in the same process. Hybrid
mode is local and needs no broker; it is useful when several lanes share one device. Set it to
`"rabbitmq"`, provide `turn_queue_url`, and optionally set `turn_queue_name` to publish turns to a
named shared queue; a `server turn-worker` process owns the model server and can serve several
lane processes. Shared mode is explicit opt-in and needs a durable RabbitMQ deployment; it never
changes the direct default silently.

The broker URL may contain credentials. Keep it in operator-owned secret configuration, restrict
RabbitMQ vhost and queue permissions to worker and lane identities, use TLS when the broker is not
local, and never include the URL in diagnostics or committed files. `aio-pika` is included in the
`vibey-engine` distribution.

## Tools the model can call

A run's model can call these 14 tools (`CODING_TOOL_NAMES`, `src/qwenloop/domain/model.py`):

| Tool | What it does |
|---|---|
| `read_file`, `write_file`, `edit_file` | Read, write and edit files in the worktree. |
| `shell` | Run an argv. `sudo`, `rm`, `shutdown` and `reboot` are refused. The command sees an allow-list of the environment: system basics such as `PATH` and `HOME`, never a `VIBEY_*` or `PG*` variable, and never a name containing `KEY`, `TOKEN`, `SECRET`, `PASSWORD`, `PASSWD`, `CREDENTIAL`, `DSN` or `DATABASE_URL` (`ShellEnvironment`). |
| `outline` | A source file's declarations with line numbers and no bodies; `exports_only` keeps what other files can import. |
| `search` | File contents, literal unless `regex` is true. |
| `find` | File names, by glob or substring. |
| `open_file` | `read_file` by the name gpt-oss reaches for, with an optional line range. |
| `web_search`, `web_fetch` | Through `vibey search` and `vibey fetch`, in a vibey worker's session only (see above). |
| `mcp_list`, `mcp_call` | MCP servers (below). |
| `skills_list`, `skill_read` | In a run given `--capabilities`: the snapshot's skills and plugin commands (`plugin:skill`, `plugin:command`), listed and read a page at a time within `[loops] capability_answer_tokens`, as instruction text rather than untrusted data. |

Every path stays inside the run's worktree. An unknown tool name is answered with the list of the
ones that exist. A `search` that could not read a candidate file (too large, binary, not UTF-8,
unreadable) says so and marks its answer `complete: false`. A `regex` search runs in a child
process that is killed at `search_timeout_seconds`, because a pattern can backtrack
catastrophically. How much one call may read or return is set in the config file's `[tools]`
table, and a limit the model asks for can only narrow these:

| `[tools]` key | Bounds | Default |
|---|---|---|
| `max_read_chars` | characters `read_file` / `open_file` return | `200000` |
| `max_search_matches` | matching lines `search` returns | `40` |
| `max_find_results` | paths `find` returns | `60` |
| `max_line_chars` | characters kept of one matching line | `160` |
| `max_file_bytes` | larger files are skipped by `search` | `2000000` |
| `max_skipped_examples` | skipped files `search` names (it always counts them all) | `5` |
| `search_timeout_seconds` | how long a `regex` search may run before it is killed | `10` |
| `skip_dirs` | directory names `search` and `find` never enter | `.git`, `.hg`, `.svn`, `.venv`, `venv`, `node_modules`, `__pycache__`, `.mypy_cache`, `.pytest_cache`, `.ruff_cache`, `.tox`, `.qwenloop` |

### MCP servers

The model reaches MCP servers through two tools. `mcp_list` names the servers; given a server, it
names that server's tools with one line each; given a server and a tool, it returns that one
tool's input schema, whole, or says the schema is too large for the answer budget. Long lists come
a page at a time (`page`), and an `mcp_call` answer longer than the budget is cut with a line
naming both lengths. With `--capabilities` the servers are exactly the snapshot's: a `local` one
over stdio, started through the scrubbed launcher with only its `env_allow` variables, and a
`remote` one over streamable HTTP, sent no environment, cookie, credential or proxy and never
redirected. A server is started on its first use and kept for the run as one persistent session,
and every server the run started is closed when the run ends, SIGTERM included (exit `130`). A
server that will not start, dies, hangs or answers with an error is an error the model reads,
never the end of the run. The config file's `[mcp]` table bounds it:

| `[mcp]` key | Bounds | Default |
|---|---|---|
| `request_timeout_seconds` | how long one MCP request may take before its session is ended | `60` |
| `restarts` | how often a server that died is started again in one run | `1` |
| `close_grace_seconds` | how long a stdio server has to exit before its process group is killed | `2` |
| `remote_calls_per_session` | `tools/call` requests each remote server may take in one run | `64` |
| `max_tools` | tools read from one server's listing (the listing says when it is reached) | `1024` |

## The run contract and exit codes

The stable run contract is `.qwenloop/runs/<run-id>/`, the `QWENLOOP_TASK_FULLY_COMPLETE` marker,
the `qwenloop-verdict` result fence, and these exit codes:

| Exit | Meaning |
|---|---|
| `0` | The run completed. |
| `1` | The run did not complete, or the server or endpoint was unavailable. |
| `2` | A bad setting, config file or flag (the message names it), or `server turn-worker` without shared mode. |
| `75` | Wound down on purpose (`wind-down`). |
| `78` | The capability document was refused or could not be read; no model was started. |
| `130` | Stopped by SIGTERM; every MCP server the run started is closed. |

## When it goes wrong

| What you see | What it means | What to do |
|---|---|---|
| `doctor` prints `model: <tag> unavailable` and exits 1 | The endpoint answers but does not serve that model. | `ollama pull <tag>`, using the tag `doctor` printed. |
| `llama-server: missing` and `vllm: missing`, exit 1 | No endpoint is configured, no Ollama is running, and no managed server is installed. | Start Ollama, or set `<PREFIX>_BASE_URL`, or install `llama-server`. |
| `<engine> configuration: unknown qwenloop config key(s): …`, exit 2 | A typo in the config file. | Fix the key; the settings table lists every valid one. |
| `<engine> cannot start: …`, exit 78 | The `--capabilities` document was refused. | Re-run vibey's BUILD step, which writes the document, or check the path. |
| `carrying tool calls as text (no native tool-calling; slower and less reliable than native)` | Ollama reports the model cannot call tools natively. | Use a model with native tool-calling, or set `tool_protocol = "native"` to force it. |
| A long prompt behaves as if its start was forgotten | Ollama's context is smaller than `context_window`. | Raise `OLLAMA_CONTEXT_LENGTH`, or lower `context_window`. |

## Development

The CI `tools` job runs this package's own suite on Python 3.12, 3.13 and 3.14, with plain pip,
from this directory:

```bash
pip install -e ../common && pip install -e ".[dev]"
mypy --strict src/qwenloop && lint-imports && bandit -q -r src/qwenloop
python -m pytest -q
```

`pytest` enforces 100% line and branch coverage (`--cov-fail-under=100` in `pyproject.toml`).
Model and hardware smokes are deliberately separate from the hermetic CI suite.

## Releases

This package has no release of its own. It ships inside `vibey-engine` (ADR-0037, ADR-0069), which
the monorepo publishes: a push to `develop` publishes a dev build to TestPyPI and a push to `main`
publishes to PyPI. Provenance, the merge train, version derivation and promotion are the
monorepo's, run by `vibey-gh`.

## License

qwenloop is MIT licensed. Qwen2.5-Coder model artifacts are separately licensed under Apache
License 2.0 and are downloaded only after an explicit operator command. Models an endpoint serves
(GPT-OSS 20B and its Heretic v2 build, Qwen3 14B) are the endpoint's, under their own licenses,
and this package never downloads them.

## Where next

- [Local models with Ollama](../../../docs/guides/local-models-ollama.md): set up Ollama and the
  default model for the whole of vibey, not just this runner.
- [ADR-0064](../../../docs/architecture/decisions/0064-gptossloop-is-the-sovereign-engine.md)
  and [ADR-0099](../../../docs/architecture/decisions/0099-heretic-v2-of-gpt-oss-20b-is-the-sovereign-default-model.md):
  why there are two engines and why the default model is Heretic v2.
- [The CDD guide](../../../docs/guides/convergence-driven-development.md): the loop storm mode
  follows.

## Say it in one line

gptossloop and qwenloop are one local runner under two names; pull the model gptossloop asks for,
run `gptossloop doctor`, and a plan runs on your own hardware.
