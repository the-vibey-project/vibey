# Triaged delivery bridge

`scripts/triaged_delivery.py` takes triaged GitHub issues (`vibey-gh:triaged`) into Vibey one
at a time: it dispatches a project for the issue, drives the normal worker, and publishes the
finished project as a pull request. `scripts/triage_queue.py` is its durable ordering and
lease authority, the `triaged_ticket` table (migration 0020). This page is how to run the
bridge unattended, and what it will and will not do while nobody is watching.

## What one pass does

1. **Reap and reconcile** (with a ticket store). Expired ticket leases go back to `ready`.
   The open triaged issues are upserted; a claimable ticket whose issue was closed, or lost
   the triaged label, is retired to `blocked` (its reason is in the ticket's evidence file).
   A listing that reached its limit retires nothing: an issue past the limit is unknown, not
   closed.
2. **Resume before selecting.** For each dispatched project, in priority order:
   - DONE: publish it (idempotently: an existing pull request is reused) and mark the ticket
     `completed`. The slot is free.
   - abandoned: the ticket is `blocked`. The slot is free.
   - waiting on a person (an open human gate, or a design waiting for `vibey design accept`):
     record it and stop. **Nothing new is selected**: one active project at a time.
   - otherwise: drive it again, bounded by `--max-steps`, and stop.
3. **Only with nothing in flight**, claim the next issue (a ticket lease plus an idempotent
   dispatch comment), create its project with `vibey new`, and drive it.

A dispatch that fails hands the ticket back to `ready` for the next pass; after
`VIBEY_TRIAGED_DELIVERY_MAX_DISPATCH_FAILURES` (3) failures in a row it is `blocked`. A pass
killed outright leaves its lease to run out, and the next pass after that reaps it. A worker
run that exceeds `--worker-timeout` is stopped with its whole process tree; its job lease is
left to expire, and each later pass runs `vibey queue reap --project <id>` before driving that
project again, until the worker makes progress.

## What waits for a person

By default the bridge answers **no** human gate:

| Waits for | How a person clears it |
|---|---|
| DESIGN interview questions | `vibey answer <gate> ...` (see `vibey gates`) |
| The design's acceptance | `vibey design accept <project>` |
| The REVIEW verdict | `vibey answer <gate> --verdict ...` |
| Merging | the PR automation promotes the green draft; the merge train lands it |

The evidence file says which one a project is waiting on (`outcome`: `parked_at_gate`,
`design_awaiting_acceptance`, `awaiting_capacity`, `worker_timeout`, `pr_draft_awaiting_promotion`, ...).

### The opt-in: `--answer-design-defaults`

`--answer-design-defaults` (or `VIBEY_TRIAGED_DELIVERY_ANSWER_DESIGN_DEFAULTS=1`) lets the
bridge answer DESIGN interview questions with their declared defaults and accept the design.
It is off by default because those answers are a person's decisions about what to build.
With it on, every answer is recorded under `--answer-by` (`automation:triaged-delivery`), not
under the account that runs the bridge, and the operating-system account is recorded beside
it as always. Two limits to know:

- `vibey answer --by` sets the recorded name only. The `GateAnswered` ledger event is
  written with `trusted` provenance whoever answers; the label and the account are what tell
  an automated answer from a person's.
- `vibey design accept` takes no `--by`. The bridge records `design_accepted_by` in its own
  evidence file; the ledger does not name who accepted.

The opt-in never answers a REVIEW verdict, a deployment choice, or any other gate.

## Running it unattended

From the repository checkout, with `gh` logged in under a credential a background service can
read (a keyring login fails under launchd; see the
[sovereign review runner](sovereign-review-runner.md#why-a-dedicated-credential)):

```bash
# one pass, for a timer (launchd StartInterval / a systemd timer)
uv run python scripts/triaged_delivery.py --once

# or its own supervisor loop: a failed pass is reported and the loop goes on
uv run python scripts/triaged_delivery.py --interval 300
```

With `VIBEY_PG_URL` set the ticket store is used; without it the bridge falls back to the
dispatch and publication markers in issue comments. Worktrees are created in the storm home
(`VIBEY_STORM_HOME`), never on volatile storage.

In a split install (ADR-0055) the application role holds no grant on `triaged_ticket` or
`triaged_ticket_bump_seq` (`APP_ROLE_GRANTS` does not list them), so a `VIBEY_PG_URL` naming
that role fails with `permission denied`. Until the grant is declared, run the bridge without
a ticket store or against a role that has it.

## Settings

Every setting is a flag and an environment variable; the flag wins.

| Flag | Environment | Default |
|---|---|---|
| `--answer-design-defaults` | `VIBEY_TRIAGED_DELIVERY_ANSWER_DESIGN_DEFAULTS` | off |
| `--answer-by` | `VIBEY_TRIAGED_DELIVERY_ANSWER_BY` | `automation:triaged-delivery` |
| `--draft` / `--no-draft` | `VIBEY_TRIAGED_DELIVERY_DRAFT` | draft |
| `--base` | `VIBEY_TRIAGED_DELIVERY_BASE` | `develop` |
| `--provider` | `VIBEY_TRIAGED_DELIVERY_PROVIDER` | `gptossloop` |
| `--worker-timeout` | `VIBEY_TRIAGED_DELIVERY_WORKER_TIMEOUT` | 900 s |
| `--max-steps` | `VIBEY_TRIAGED_DELIVERY_MAX_STEPS` | 100 |
| `--lease-seconds` | `VIBEY_TRIAGED_DELIVERY_LEASE_SECONDS` | 900 |
| | `VIBEY_TRIAGED_DELIVERY_VIBEY` | `uv run vibey` |
| | `VIBEY_TRIAGED_DELIVERY_OWNER` | `triaged-delivery` |
| | `VIBEY_TRIAGED_DELIVERY_BRANCH_PREFIX` | `delivery` |
| | `VIBEY_TRIAGED_DELIVERY_MAX_DISPATCH_FAILURES` | 3 |
| | `VIBEY_PG_URL`, `VIBEY_GITHUB_REPOSITORY`, `VIBEY_STORM_HOME`, `VIBEY_PUSH_GATE` | as before |

A finished project is pushed through the push gate as `<prefix>/<issue>-<project>`: every
project's local integration branch is `vibey/<cycle>/integration`, so that name alone would
collide on the remote between two deliveries.

## Evidence

`.vibey/delivery-evidence/<project>.json` holds the latest status, open gates, cost and
outcome for each project; `ticket-<issue>.json` holds a ticket's retirements, adoptions and
dispatch failures. They record what was observed; a pull request's existence is not a claim
that it merged.
