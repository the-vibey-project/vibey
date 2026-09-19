# claudeloop-agent-sdk (Antigravity mirror of `.claude/skills/claudeloop-agent-sdk/SKILL.md`)


# claudeloop + claude-agent-sdk

`infrastructure/agent/` is the only place `claude_agent_sdk` may be
imported.

- Default gateway is the SDK (`ClaudeSDKClient`). Use `ClaudeSDKClient`,
  never `query()` — the client stays alive across error results.
- Autonomy: `permission_mode="bypassPermissions"` (no
  `dangerously_skip_permissions` field in Python SDK — this is the
  equivalent).
- `can_use_tool` denies `AskUserQuestion` with guidance, never awaits input.
- `output_format` is JSON schema (`{complete, remaining_work, blocked_on,
  summary}`) — structured output is primary, substring fallback is legacy.
- `blocked_on` must be null for waitable work — only true external/human
  blockers. Non-null terminates the run as `Blocked`.
- Rate-limit signals: read three (`RateLimitEvent`, `ResultMessage
  .api_error_status`, `AssistantMessage.error`), trust none alone.
- `CLAUDE_CODE_RETRY_WATCHDOG` off by default. Opt-in via
  `--retry-watchdog`. See ADR 0005.
- Backend profiles (`--profile`, `domain/backend.py`): the SDK merges
  `options.env` over `os.environ`, so the profile overlay wins — a local
  profile sets `ANTHROPIC_API_KEY=""` to scrub a paid key. Both
  `build_turn_options` and `build_probe_options` take `env=` / `cli_path=`;
  a probe without the overlay would still ask Anthropic. Local means: tiers
  required, no `claude-*` ids, no effort, no `--max-budget-usd`, cost recorded
  as $0 (Claude Code guesses a price for unknown models) with token counts
  kept, and `TurnSignals.local_backend=True` so `classify` reads Ollama's
  404 / 500 / refused-connection / "Prompt is too long" as
  `BackendMisconfigured` and 503 as a local
  window. The CLI sends `error: "model_not_found"` although the SDK Literal
  does not list it. `resume` refuses to cross backends (run meta `backend`).
  A model that writes tool calls as text (qwen2.5-coder:14b on Ollama, live)
  can fake Done via the marker, so local profiles set
  `done_marker_fallback = false` and `doctor` checks for real `tool_use`.

See ADR 0002, 0005, 0007 and `docs/guides/local-backend.md`.
