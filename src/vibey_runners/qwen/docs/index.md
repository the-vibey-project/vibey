# qwenloop

`qwenloop` is an autonomous, local Qwen 2.5 Coder 14B runner. It uses a
portable llama.cpp/Q5_K_M profile by default and can use BF16 through vLLM on
Linux NVIDIA systems with at least 40 GiB of usable VRAM. It can also attach to
a server that is already running, such as Ollama, instead of starting one (see
[Attach to Ollama](#attach-to-ollama-or-any-openai-compatible-endpoint)).

Model installation is always explicit. The package, tests, `doctor`, and Vibey
integration never download model weights.

## Install

`qwenloop` ships inside the `vibey` distribution (vibey ADR-0037); there is no
separate `qwenloop` project to install:

```bash
uv tool install vibey    # or: pipx install vibey / pip install vibey
```

The Python package never bundles model weights.

## Quick start

```bash
qwenloop model install --profile portable
qwenloop model verify
qwenloop doctor
qwenloop run plan.md --run-id <uuid> --cwd <worktree>
```

The stable run contract is `.qwenloop/runs/<run-id>/`, exit code `75` for a
graceful wind-down, the `QWENLOOP_TASK_FULLY_COMPLETE` marker, and a
`qwenloop-verdict` result fence.

## Inference profiles

| Profile | Backend | Intended hardware | Model installation |
|---|---|---|---|
| `portable` | llama.cpp Q5_K_M | Apple Silicon, Linux CPU, supported offload GPUs | Explicit `qwenloop model install --profile portable` |
| `nvidia-bf16` | vLLM BF16 | Linux NVIDIA with at least 40 GiB free VRAM | Operator-managed pinned Hugging Face/vLLM cache |

Servers bind to loopback and require a per-launch bearer token. Qwenloop never
silently changes backend during a run.

## Attach to Ollama, or any OpenAI-compatible endpoint

The `openai-compat` backend attaches to an inference server that someone else runs
instead of spawning llama-server or vllm. Ollama is the main target, but any server that
answers `GET /models` and `POST /chat/completions` under its base URL works:
LM Studio, a vLLM someone else runs, or a hosted gateway.

```bash
ollama pull qwen2.5-coder:14b
export QWENLOOP_BASE_URL=http://127.0.0.1:11434/v1   # the OpenAI base URL, /v1 included
qwenloop doctor                                      # 0 only if it answers AND serves the model
qwenloop run plan.md --run-id <uuid> --cwd <worktree>
```

A running run takes follow-ups: `qwenloop prompt <run-id> "<text>" --cwd <worktree>`
writes one into the run's control inbox, and the model reads it at the start of its next
turn, once, in the order follow-ups were sent. Each is recorded as a `prompt.received`
event and moved to `control/ack` when it is taken.

qwenloop never owns an attached server. `start` checks that the endpoint answers and
serves the configured model, and fails with a message naming which check failed. `stop`
does nothing. `auto` selects `openai-compat` whenever a base URL is configured, and an
explicit `--backend` still wins. `--backend openai-compat` with no base URL attaches to
Ollama's default address, `http://127.0.0.1:11434/v1`. `run`, `run --storm`,
`server start`, and `server status` all use the same backend. A run records the
endpoint URL in place of a pinned revision and digest, because the endpoint manages the
model, not qwenloop.

| Setting | Flag | Environment | Config key | Default |
|---|---|---|---|---|
| Endpoint base URL | `--base-url` | `QWENLOOP_BASE_URL` | `base_url` | unset |
| Model name sent to the endpoint | `--model` | `QWENLOOP_MODEL` | `model` | `qwen2.5-coder:14b` |
| Endpoint API key | — | `QWENLOOP_API_KEY` | — | none, so no `Authorization` header is sent |
| Endpoint probe timeout (seconds) | — | — | `endpoint_timeout_seconds` | `5` |
| Backend | `--backend` | — | `backend` | `auto` |
| Turn limit | `--max-turns` | — | `max_turns` | `40` |
| Consecutive empty replies retried before a run fails | — | — | `max_empty_reply_retries` | `2` |
| Characters of each tool-call argument value recorded in `events.jsonl` | — | — | `max_recorded_argument_chars` | `200` |
| Characters of an empty reply's reasoning recorded as an excerpt | — | — | `empty_reply_reasoning_excerpt_chars` | `400` |
| Server startup wait (seconds) | — | — | `startup_timeout_seconds` | `180` |
| Context window (tokens) | — | — | `context_window` | `32768` |

A flag beats an environment variable, which beats the config file, which beats the
default. The config file is TOML, read from `$QWENLOOP_CONFIG`. When that is unset,
it is read from `<user config dir>/qwenloop/config.toml`, which is
`~/Library/Application Support/qwenloop/config.toml` on macOS and
`~/.config/qwenloop/config.toml` on Linux. A missing default file is fine. A missing
file named by `QWENLOOP_CONFIG`, invalid TOML, an unknown key, or a base URL that is
not `http(s)://` stops the command with exit code 2 and a message naming the problem.
The API key is read only from the environment: it never goes in a file or on a command
line. `portable_profile`, `nvidia_profile`, and `idle_timeout_seconds` are checked for
validity, but nothing uses them yet.

A run's model can call `read_file`, `write_file`, `edit_file`, `shell`, `search` (file
contents, literal unless `regex` is true), `find` (file names, by glob or substring) and
`open_file` (`read_file` by the name gpt-oss reaches for, with an optional line range).
Every path stays inside the run's worktree. An unknown tool name is answered with the list
of the ones that exist. How much one call may read or return is set in the config file's
`[tools]` table, and a limit the model asks for can only narrow these. A `search` that
could not read a candidate file (too large, binary, not UTF-8, unreadable) says so, and
marks its answer `complete: false`. A `regex` search runs in a child process that is killed
at `search_timeout_seconds`, because a pattern can backtrack catastrophically:

| `[tools]` key | Bounds | Default |
|---|---|---|
| `max_read_chars` | characters `read_file` / `open_file` return | `200000` |
| `max_search_matches` | matching lines `search` returns | `100` |
| `max_find_results` | paths `find` returns | `200` |
| `max_line_chars` | characters kept of one matching line | `240` |
| `max_file_bytes` | larger files are skipped by `search` | `2000000` |
| `max_skipped_examples` | skipped files `search` names (it always counts them all) | `5` |
| `search_timeout_seconds` | how long a `regex` search may run before it is killed | `10` |
| `skip_dirs` | directory names `search` and `find` never enter | `.git`, `.venv`, `node_modules`, caches, `.qwenloop` |

Ollama must be able to hold `context_window` tokens. Set its own context length
(`OLLAMA_CONTEXT_LENGTH`, or the model's `num_ctx`) to at least `context_window`, or
lower `context_window` to match. Otherwise Ollama quietly drops the start of a long
prompt, which qwenloop has already trimmed to `context_window`.

## Development

```bash
uv sync --extra dev
uv run ruff check .
uv run ruff format --check .
uv run mypy --strict src/qwenloop
uv run lint-imports
uv run pytest -q
uv run bandit -q -r src/qwenloop
```

First-party code is held to 100% line and branch coverage. Model and hardware
smokes are deliberately separate from the hermetic CI suite.

## Release workflow

Qwenloop uses `develop` as its integration branch and `main` as its release
branch. `vibey-gh` provides provenance fingerprints, merge-train automation,
derived versions, promotion, and post-release branch realignment.

## License

Qwenloop is MIT licensed. Qwen2.5-Coder model artifacts are separately licensed
under Apache License 2.0 and are downloaded only after an explicit operator
command.
