# 0090 — pr-af is the declared default exact-head reviewer

**Status:** proposed · **Date:** 2026-10-22 · **Cites:** sub-doctrine 8.b; ADR-0018, ADR-0038 · **Related:** ADR-0042, ADR-0064

## Context

The exact-head review is the load-bearing gate before the merge train: `PR review / gate` is a
required check, and its verdict is the last automated judgment on a pull request. Today that
verdict comes from vibey's own lanes — the sovereign local model, a declared paid model, or
both split by the documentation contract. That logic is still being completed, and a review
that is narrower than the change it judges is a known failure mode: the local lane sees the
diff only, and a large diff is refused rather than judged.

Agent-Field `pr-af` is an open-source reviewer built for exactly this surface. It runs as an
AgentField node behind a control plane, reviews a pull request at its exact head, posts its
review to GitHub, and returns a `ReviewResult` whose `summary.blocking_count` comes from its
own merge gate. It reaches a model through OpenRouter, so it is a paid counterparty under
sub-doctrine 8.b. It is also third-party code that must run with a token able to write the
pull request.

This repository wants pr-af as its default reviewer now, without making every adopter pay for
it or depend on it, and without letting an infrastructure failure turn the required gate into
a hard stop on every pull request.

## Decision

`[pr_automation.pr_af]` declares pr-af. `enabled` defaults to **false**, so a repository that
says nothing never schedules the job or reads the OpenRouter secret; this repository declares
it on. The reviewer's code is pinned to a full 40-character commit SHA, never a branch,
because a moving ref would let code that can write the pull request change without a diff in
this repository.

When pr-af is declared, `default = true` makes its verdict authoritative: the gate follows
`summary.blocking_count` (its own merge gate's decision, not a severity label) and the review
event it chose. Where it is offered, the sovereign/paid lane still runs beside it as the
second opinion. When pr-af
produces **no** verdict — a missing secret, an unreachable control plane, a failed execution,
a result the details endpoint did not carry, or a review that reached its own cost or duration
cap — the gate falls back to the lane it would have used before this table existed, and says
in the check summary that the fallback decided. A budget-exhausted review is never a pass.

The default venue is a GitHub-hosted runner. `host_enabled` prefers the operator's own runner
only while its heartbeat is fresh, and the hosted job runs whenever the host is not ready, so
a sleeping laptop cannot queue every pull request. A fork head never reaches the self-hosted
venue; the head-repository check is repeated in the job as defence in depth. Both venues use
one per-run compose project and the same pinned commit.

## Consequences

- The gate's primary verdict is now a third-party reviewer's own merge gate, with vibey's
  lanes as the fallback and second opinion. The check title names `pr-af` so a reader can tell
  which reviewer passed a head.
- An OpenRouter key is required for the lane to run. Absent, the job skips with a step summary
  and the fallback decides; the gate degrades rather than blocks.
- A pr-af review costs money and 35–50 minutes of runner time in practice. The review's own
  caps and the job's `timeout_minutes` bound both; reaching either yields no verdict.
- Updating the reviewer is a reviewed dependency bump: the pinned SHA changes in
  `.vibey-gh.toml` and the rendered workflows together.
- The hosted venue publishes fixed ports 8080 and 8004, so a host offering the lane must not
  run two reviews concurrently.
- The table is the whole declaration. An undeclared repository renders both pr-af jobs with
  `if: false`, so GitHub never schedules them.

## Alternatives rejected

- **Pin a branch or tag.** Third-party code would run with a token that can write the pull
  request, and its content could change between runs with no diff in this repository.
- **Declare it on for every adopter.** That spends an adopter's money and reads their secret
  without their declaration, which sub-doctrine 8.b forbids.
- **Host-only.** A sleeping or absent host would queue the required gate forever; the hosted
  venue is what makes the default dependable.
- **Run both venues on every pull request.** The host is an alternative venue, not a second
  review. Running both doubles the cost and gives two competing verdicts on one head.
- **Treat a missing verdict as a failure.** A required check that fails on an unreachable
  control plane or an unset secret turns a billing or infrastructure problem into a stop on
  every pull request. The reported gap plus the fallback is the honest reading.
- **Gate on severity rather than `blocking_count`.** pr-af already separates "how bad" from
  "must fix before merge"; re-deriving blocking from severity would silently change its
  verdict.

## Rule status

This is a mechanism decision, not a governing rule about conduct, so ADR-0020 does not require
a sub-doctrine. The paid-counterparty rule it applies is already 8.b.
