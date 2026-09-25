# 0070 — Failover to the sovereign engine, and handback on a recorded probe

**Status:** accepted · **Date:** 2026-09-25 · **Cites:** sub-doctrines 8.a, 8.b, 10.f, 10.h, 12.c, 12.d, SD-01 v1.0 §4 · **Related:** ADR-0005, ADR-0015, ADR-0038, ADR-0063, ADR-0064 · **Evidence:** `develop` at `0823cdfd` (ULTRA, #1161, merged), read 2026-09-25; code.claude.com/docs/en/hooks#stopfailure, read 2026-09-25

**Owes:** the advertised ADR count in `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `README.md`
and `docs/index.md`, and a nav entry in `properdocs.yml`, all done in the change that
carries it.

**Numbering:** 0070 was the next free number on `develop` when this was pushed (0001–0069
present; #1161 landed as ADR-0063, not 0070 as once planned). If another open change
merges first with 0070, the second to merge renumbers.

## Context

The operator asked that when a paid model runs out of tokens -- including the *driver*,
the Claude Code session steering the work -- the work continue at once on gptossloop at
ULTRA effort, losslessly, and that it come back to the same Claude Code session once the
paid model is available again (a Claude Code limit that resets on a Tuesday, say).

Three rules already bind this: a capacity rejection outranks a completion claim;
`CreditsExhausted` never has a `resets_at`; and every handoff passes the no-loss gate
(retry, then full transcript, then a human gate -- never a silent partial). Status is
evidence-bounded (10.f): a clock reaching a stated reset time is not evidence that the
paid model answers.

What Claude Code actually signals, from its own documentation (read 2026-09-25, not
guessed): the **`StopFailure`** hook "runs instead of Stop when the turn ends due to an
API error", receives `error` -- one of `rate_limit`, `overloaded`,
`authentication_failed`, `oauth_org_not_allowed`, `account_on_hold`, `billing_error`,
`invalid_request`, `model_not_found`, `server_error`, `max_output_tokens`,
`cloud_credential_error` or `unknown` -- plus optional `error_details` and
`last_assistant_message`, alongside the common `session_id`, `transcript_path` and
`cwd`. "Claude Code ignores the hook's output and exit code." The documentation exposes
no machine-readable reset time: `--output-format json` carries none. Sessions resume
non-interactively with `claude -p --resume <session-id> "<prompt>"`.

## Decision

1. **One pure policy for both levels** (`vibey/domain/failover.py`). `rate_limit` is
   `WindowExhausted(resets_at=None)`; `billing_error` is `CreditsExhausted()`, with no
   clock; the three account errors are `AuthenticationFailed`, which plans no failover
   (waiting and switching engines cannot fix a credential); every other error type is
   not a capacity rejection. A capacity rejection plans a failover to
   `[failover] target_engine` (default `gptossloop`) at `target_effort` (default
   `ULTRA`, ADR-0063), with the earliest probe time: a window's `resets_at` when one is
   known, else now plus `probe_interval_seconds`. `resets_at` only *schedules* the
   probe.
2. **Three trusted ledger kinds**: `EngineFailedOver`, `EngineProbed` (ok or not) and
   `EngineHandedBack`, withheld from publication. The failover's state is projected from
   them, never held elsewhere; only trusted records count, and a new failover resets the
   probe.
3. **Handback only after a recorded successful probe.** The probe is recorded first,
   and the handback is allowed only when an `ok` probe is recorded after the latest
   failover. A probe that exits non-zero, prints no JSON, or reports `is_error` is a
   failed probe, recorded as one.
4. **The no-loss gate in both directions** (`vibey/domain/driver_brief.py`). The driver's
   brief names the whole transcript -- path, line count, SHA-256 -- and the repository
   head, and the gate checks it against the transcript as it stands: STRICT up to three
   times, then FULL_TRANSCRIPT with the transcript copied into the worktree, then HUMAN,
   which parks: a `PARKED-*.md` brief is left for a person and nothing is started.
5. **The driver level.** `vibey driver hook` is the `StopFailure` hook's command (no
   matcher; the classifier ignores what is not capacity). It writes the gated brief
   under `<worktree>/.vibey/driver/`, appends `EngineFailedOver` to the driver's own
   append-only, hash-chained `ledger.jsonl` *before* starting `gptossloop run <brief>`
   detached, and a second hook for an active failover records and starts nothing.
   `vibey driver probe`, run by a launchd agent or a systemd user timer that
   `vibey driver timer` writes (and the operator loads), probes when due, and on a
   recorded success winds gptossloop down, gates the return brief -- listing the commits
   made while the driver was away -- appends `EngineHandedBack`, and resumes the same
   session with `claude -p --resume <session-id>`. The driver is a Claude Code session,
   not a vibey project, so its records live beside its worktree, not in Postgres.
6. **Everything is a key.** `[failover]` in `vibey.toml`: `enabled`, `target_engine`,
   `target_effort`, `probe_interval_seconds`, and the four argv templates
   (`sovereign_argv`, `sovereign_wind_down_argv`, `probe_argv`, `resume_argv`) with
   `{brief}`, `{cwd}`, `{run_id}`, `{session_id}` and `{prompt}`. An unknown key or a
   wrong type is refused by name.
7. **Unattended bounds (12.d).** The sovereign engine is told to commit on the current
   branch and not to push, merge or open a pull request; the returning session is told
   to review every commit it made. Nothing here writes a protected branch or skips a
   gate.

## Consequences

- The driver keeps working through a limit instead of stopping, and comes back to the
  same conversation, with the commits made meanwhile named for review.
- A reset time the operator knows but Claude Code does not expose cannot be read; the
  probe interval stands in, and costs one one-word paid call per interval while a
  failover is active.
- The engine level shares the policy, the gate modes and the ledger kinds. Its BUILD
  path already rotates on a capacity rejection through `RotationRecordingHandler` and
  `SelectingEngineProvider` (ADR-0005); routing that rotation to `target_engine` at
  `target_effort` and recording the three kinds in the Postgres ledger is the follow-up
  this record names, not something this change claims.
- `StopFailure`'s payload beyond the documented fields is not relied on; if Claude Code
  later exposes a reset time, it may schedule the probe and nothing more.
