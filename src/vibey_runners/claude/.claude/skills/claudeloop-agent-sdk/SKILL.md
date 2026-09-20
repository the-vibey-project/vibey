---
name: claudeloop-agent-sdk
description: Explains how claudeloop integrates with claude-agent-sdk (ClaudeAgentOptions, ClaudeSDKClient vs query(), RateLimitEvent, ResultMessage, AssistantMessage, session discovery via list_sessions()) and the never-block-on-a-human design (permission_mode, can_use_tool, AskUserQuestion handling, hooks). Use this whenever building or modifying src/claudeloop/infrastructure/agent/ (the M2+ agent gateway, options builder, message translation, session catalog, capacity probe), whenever the user asks about the Claude Agent SDK, ClaudeAgentOptions fields, session resumption, rate-limit events, or why a run might block on a human. Make sure to consult this before writing any code that calls claude_agent_sdk directly — infrastructure/agent/ is the ONLY place that import is allowed, per the onion architecture (see the claudeloop-architecture skill), and getting the never-block guarantees wrong here defeats the entire purpose of this project.
allowed-tools: Read Grep Glob
---

# claudeloop + claude-agent-sdk integration

`infrastructure/agent/` is the only place `claude_agent_sdk`
may be imported — see the `claudeloop-architecture` skill for the enforced
onion rule. This skill covers the SDK integration specifics; consult
`claudeloop-domain-model` for how the resulting signals get classified.

## `ClaudeSDKClient` over `query()` — this is not optional

`query()` (single-shot) raises a **plain `Exception`** after yielding an
error `ResultMessage`, and the underlying process exits non-zero. A
streaming-input `ClaudeSDKClient` **stays alive** across error results — you
can keep sending messages on one live process with no resume/respawn. The
`AgentGateway` adapter (infrastructure/agent/gateway.py::ClaudeAgentGateway) MUST use `ClaudeSDKClient`, not `query()`, or
the whole point of collapsing the legacy respawn loop is lost. See ADR 0002
for the full reasoning.

## Key `ClaudeAgentOptions` fields for this project

- **`permission_mode="bypassPermissions"`** — required for autonomy. Note:
  the Python SDK has **no `dangerously_skip_permissions` field**; this is
  its equivalent. Do not go looking for a field that doesn't exist.
- **`can_use_tool`** — a defensive callback that must NEVER await input.
  Intercepts `AskUserQuestion` specifically and **denies with guidance**
  (not auto-answers) — see the "Never blocking" section below.
- **`output_format`** — a JSON schema
  (`{complete: bool, remaining_work: [str], blocked_on: str|null, summary:
  str}`) so each turn returns a `ResultMessage.structured_output` the
  domain layer's `completion.py` can evaluate directly, rather than
  substring-matching output text. Property descriptions (and the autonomy
  system-prompt fragment) insist `blocked_on` is only for true
  external/human blockers — waitable self-started work goes in
  `remaining_work` with `blocked_on: null`, because any non-null value
  terminates the run as `Blocked`.
- **`resume` / `continue_conversation` / `fork_session` / `session_id`** —
  `session_id` cannot combine with `resume`/`continue_conversation` unless
  `fork_session=True` is also set. Get this wrong and session resumption
  breaks in a way that's easy to miss in a quick test. When building
  options, drop `session_id` whenever `resume` or `continue_conversation`
  is set (see `build_turn_options`).
- **`setting_sources=None`** for the throwaway capacity probe specifically
  — no `CLAUDE.md` should load for a one-token "are we still limited"
  check.
- **`hooks`** — `PermissionRequest` auto-allows; `Notification` logs only,
  never blocks.

## Never blocking on a human — every mitigation, concretely

| Stall path | Mitigation |
|---|---|
| Permission prompts | `permission_mode="bypassPermissions"` |
| Unexpected permission path | Defensive `can_use_tool` returning `PermissionResultAllow` without ever awaiting input |
| `AskUserQuestion` | Intercepted, **denied with guidance** — e.g. "running autonomously, no user available — choose the option you would recommend, note the assumption, and proceed." NEVER fabricate an answer; that silently invents a decision nobody made. |
| `ExitPlanMode` | Auto-approved |
| `Notification` hooks | Logged, never awaited |
| Model asks "Shall I proceed?" in plain text | No tool call to intercept — mitigated via an appended system-prompt fragment establishing autonomous operation |
| TTY-dependent stdin | Never inherit a TTY — must be safe under `nohup`/systemd |
| MCP OAuth | Genuinely cannot complete unattended — the `doctor` command checks configured MCP servers up front and fails fast, naming them, rather than discovering the problem mid-run |

If you're adding a new tool-interception path, apply the same test every
time: **can this ever wait on stdin or a human response?** If yes, it needs
an explicit mitigation in this table before it ships.

## Rate-limit signals — read three, trust none alone

`RateLimitEvent.rate_limit_info`: `status` (`allowed`/`allowed_warning`/
`rejected`), `resets_at`, `rate_limit_type`
(`five_hour`/`seven_day`/`seven_day_opus`/`seven_day_sonnet`/`overage`),
`utilization`, `overage_status`, `overage_resets_at`,
`overage_disabled_reason`. The Claude Code binary contains the string
`[sdkMessageAdapter] Ignoring rate_limit_event message` — treat this event
as possibly absent and always corroborate with `ResultMessage
.api_error_status` and `AssistantMessage.error` (see the
`claudeloop-domain-model` skill's `TurnSignals` section for exactly how
these three combine).

## Session discovery — use the supported API

`list_sessions()` / `get_session_info()` return `SDKSessionInfo` (session_id,
summary, last_modified, custom_title, first_prompt, git_branch, cwd, tag,
created_at) via cheap stat + head/tail reads. **Never** hand-parse
`~/.claude/projects/<encoded-cwd>/*.jsonl` directly — the docs explicitly
warn the transcript format changes between Claude Code releases, and this
API exists specifically to replace that fragile approach from the legacy
script.

## The capacity probe — deliberately minimal

The throwaway turn used while `WAITING` (see `claudeloop-domain-model`):
one-token prompt, `max_turns=1`, no tools, `setting_sources=None`, and
`extra_args={"no-session-persistence": None}` so it leaves no transcript
and doesn't pollute the working session's history with "OK" turns. A
rejected probe isn't billed by the API.

## Backend profiles — the env overlay reaches the turn AND the probe

A `[profiles.<name>]` table (`--profile` / `CLAUDELOOP_PROFILE`) picks the
endpoint Claude Code talks to. The decisions live in `domain/backend.py`
(`BackendProfile`, `BackendRuntime`, `BackendIdentity`); `infrastructure/backend.py`
reads the TOML and the environment; `bootstrap.py` hands the resolved
`BackendRuntime` to both `ClaudeAgentGateway` and `ClaudeCapacityProbe`.

- **The SDK merges `options.env` over `os.environ`**, so the overlay wins. That
  is the only way to *remove* an inherited value: a local profile sets
  `ANTHROPIC_API_KEY=""` so a paid key never reaches a local server. Never
  "just not set" a key you mean to scrub.
- **`build_turn_options` and `build_probe_options` both take `env=` and
  `cli_path=`.** A probe built without the overlay re-checks capacity on
  Anthropic while the run talks to Ollama — the defect this fixed.
- **Local (`base_url` set) implies:** every tier named and no `claude-*` id;
  Claude Code's haiku/sonnet/opus aliases mapped onto the tiers; `--effort`
  not forwarded (`pass_effort`); `--max-budget-usd` not forwarded and
  `TurnAccumulator(cost_mode="zero")` records $0 — Claude Code prices an
  unrecognised model at its default model's rate (observed: $0.0008365 for one
  free qwen2.5-coder:1.5b turn) — while `ResultMessage.usage` token counts are
  kept; `CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC=1`; web search / deep research
  refused.
- **Errors a local backend produces** (captured from the bundled CLI against
  Ollama 0.34.2) — `AssistantMessage.error` / `ResultMessage.api_error_status`:
  model not pulled → `"model_not_found"` / 404; server down → `"server_error"` /
  `None` with "Connection refused … (ConnectionRefused)"; model failed to load →
  `"server_error"` / 500; queue full → `"server_error"` / 503; conversation over
  `context_window` → `"invalid_request"` / `None`, "Prompt is too long" (Claude
  Code reserves `max_output_tokens` out of the window). `TurnAccumulator`
  passes `local_backend=True` into `TurnSignals` so `classify` can read them
  (see `claudeloop-domain-model`). Claude Code retries a refused connection up
  to `CLAUDE_CODE_MAX_RETRIES` times first — about three minutes at the
  default before claudeloop sees it; `extra_env` can lower it.
- **A model that writes tool calls as text does nothing — and can fake Done.**
  Observed live: qwen2.5-coder:14b on Ollama answers even a one-tool request
  with `{"name": ..., "arguments": ...}` as a *text* block; inside Claude Code it
  wrote its Write call and its StructuredOutput call as text, appended the done
  marker, and the run reported Done for a file it never created. Hence a local
  profile's `done_marker_fallback = false` (only a structured verdict completes
  a run; `AutonomousRunner(done_marker_fallback=...)` →
  `evaluate(marker_fallback=...)`) and `doctor`'s `backend-tools` check, which
  POSTs one trivial tool to `/v1/messages` per tier and wants a `tool_use` block.
- **`AssistantMessageError` in the SDK types does not list `model_not_found`;**
  the CLI sends it anyway. Compare strings, not the Literal.
- **Resume never crosses backends:** run meta records `backend`
  (`anthropic` | `gateway:<url>` | `local:<url>`) and `profile`;
  `bootstrap.check_resume_backend` refuses a mismatch.

## `CLAUDE_CODE_RETRY_WATCHDOG` — deliberately off by default

Do not set this env var in the default agent gateway configuration. It
retries 429/529 in-process indefinitely with no progress reporting, no
credits-vs-window discrimination, and no `--max-wait`. It's exposed as an
explicit opt-in flag (`--retry-watchdog`), never the default. See ADR 0005
for the full reasoning if you're tempted to "simplify" by using it instead
of the probe-based waiting policy.

## Full reference

`docs/architecture/decisions/0002-agent-sdk-over-subprocess.md`,
`docs/architecture/decisions/0005-retry-watchdog-off-by-default.md`,
`docs/architecture/decisions/0007-ask-user-question-denied-with-guidance.md`,
`docs/guides/never-blocking.md`, `docs/guides/rate-limits-and-credits.md`,
`docs/guides/local-backend.md`.
