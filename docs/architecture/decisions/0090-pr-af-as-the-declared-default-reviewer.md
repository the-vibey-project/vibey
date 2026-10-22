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

## Amendment 2026-10-22 — the venue chooses the model

**Context.** The first cut made OpenRouter the only way pr-af could reach a model, so the
default reviewer could not run at all without a paid key and an operator with local
hardware had no way to use it. pr-af itself has one model setting for every one of its
agents and an entrypoint that writes an OpenRouter-only configuration, but its opencode
harness reaches any OpenAI-compatible server, and tier names such as `premium` are labels,
not model ids.

**Decision.** `host_provider` (`"openrouter"` by default, `"local"` to opt in) says which
model the **host** venue reviews on; the hosted venue is always OpenRouter, because a hosted
runner cannot reach the operator's machine. A local host therefore reviews for free while its
heartbeat is fresh, and a sleeping machine falls through to the inexpensive hosted model —
cost and independence balanced by the venue, with no new scheduler. `hosted_enabled = false`
drops the paid venue, so a repository can run on its own hardware and never hold the key;
`needs_openrouter` is then false and the secret is neither requested nor rendered.

The local model and server default to the sovereign lane's (`[pr_automation.fallback]`), so
one declaration of "which local model, where" serves both lanes, and `local_model` /
`local_base_url` override it for pr-af alone. The local path is
`vibey_gh.pr_af_local`: a `docker-compose.override.yml` written beside the pinned checkout
that selects the opencode harness, writes an opencode provider for the server, and replaces
the entrypoint that only knows OpenRouter. It never patches third-party code, restates the
image's `CMD` (compose drops it when the entrypoint is replaced), points the container at
`host.docker.internal` in place of a loopback address, and **blanks `OPENROUTER_API_KEY`
inside the container**, so a review declared local cannot reach the paid router by accident.

The host job's preflight observes rather than assumes: the server must answer and must
already hold the model, because a model that has to be pulled would spend the review's
budget downloading it. Either failure is "no verdict", and the fallback decides, exactly as
a missing secret does. The gate names the model the job reported, not the router's.

A smaller model's approval is the unsafe direction, so the verdict is **asymmetric**:
`local_verdict_passes` (false by default) lets a local model's block fail the gate, as any
pr-af block does, but leaves every pass to the sovereign/paid fallback and says so in the
check. A model that can only tighten the gate cannot weaken it; the repository loosens it
deliberately, by a reviewed change, after reading the local reviews.

**Measured, and so not enabled in this repository.** On 2026-10-22 pr-af was run end to end
on `gpt-oss:20b` on the operator's laptop against a one-file dependency bump (#1658, depth
`quick`, `--dry-run`). The path worked — the entrypoint wrote the provider, the key stayed
blank in the container, intake, anatomy, meta-selection, review and the coverage loop all
completed, including a schema retry — but the review was still in phase 6 of 7 at 45
minutes, with eight agent calls and 68 minutes of summed agent time behind it and twelve
consistency-verify agents queued, past pr-af's own 3600 s cap. Capped, that is no verdict
and the fallback decides; it is never a pass. The gate would, however, wait that long on every
pull request, so this repository keeps `host_enabled = false` and records the opt-in beside
the declaration. The capability is shipped, tested and ready for a faster model.

**Consequences.** A local model is smaller than the router's, so verdict quality is
something to measure, not assume: a review that cannot satisfy pr-af's structured outputs
ends with no verdict and the fallback decides, never a pass. The host venue still serialises
reviews (fixed ports 8080 and 8004). Adopters change nothing: both new defaults reproduce the
first cut exactly.

