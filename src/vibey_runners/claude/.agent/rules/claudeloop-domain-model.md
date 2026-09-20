# claudeloop-domain-model (Antigravity mirror of `.claude/skills/claudeloop-domain-model/SKILL.md`)


# claudeloop domain model

Everything in `src/claudeloop/domain/` is frozen dataclass, zero
third-party imports, 100% test coverage.

## CapacityState (capacity.py)

```python
CapacityState = (
    Available | WindowExhausted | CreditsExhausted | AuthenticationFailed | BackendMisconfigured
)
```

**Most important fact**: `CreditsExhausted` has NO `resets_at` field — not
`None`, the type doesn't carry one. Waiting cannot fix an empty balance.
`WindowExhausted` carries `resets_at: datetime | None`. `AuthenticationFailed`
and `BackendMisconfigured` (backend unreachable / model missing / model failed to
load — needs a human, exit 78) are the terminal, non-waitable states.

## classify.py — TurnSignals → CapacityState

Reads three SDK signals. **Ordering is load-bearing**, in this sequence:

1. `assistant_error == "authentication_failed"` → `AuthenticationFailed`
2. `assistant_error == "billing_error"` → `CreditsExhausted`
3. `backend_misconfiguration()` → `BackendMisconfigured`: `model_not_found` on
   any backend; on a local backend (`local_backend`) also 404, 500, "Prompt is
   too long", or an unreachable-connection error. Needs a real error signal,
   never text alone.
4. Local backend + HTTP 503 → `WindowExhausted(rate_limit_type="local")`
5. `rate_limit_status == "allowed_warning"` → `Available` (NOT a rejection)
6. Credit signals (`credits_required`, `out_of_credits`,
   `overage_disabled_reason`) win over stray `resets_at` → `CreditsExhausted`
7. Anything else rejected → `WindowExhausted`

Preserve order. Re-run `tests/domain/test_classify.py`.

## CompletionVerdict (completion.py)

```python
CompletionVerdict = Done | Continue | Blocked
```

Primary: `StructuredVerdict` from `output_format`. `blocked_on` outranks
`complete`, terminates run. Fallback: substring-match
`CLAUDELOOP_TASK_FULLY_COMPLETE` — off when `marker_fallback=False` (a local
backend's default: a model that cannot call tools once typed the marker and
"completed" work it never did).

## waiting.py — next_probe_instant()

Returns **instant to probe**, never a duration.

- `CreditsExhausted` — exponential backoff, clamp BEFORE constructing
  `timedelta` (overflow at realistic probe counts).
- `WindowExhausted(resets_at=X)` — `min(X + reset_grace, now +
  window_probe_interval)`.

See `docs/architecture/domain-model.md`.
