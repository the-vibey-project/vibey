# ADR-0034: verify independence is the default, not an absolute

- **Status:** Accepted
- **Date:** 2026-09-15
- **Supersedes:** nothing. Refines the rule stated in
  `docs/plans/phase-protocols.md` §2.3.

## Context

`build.verify` is a separate job from a different engine than the one that
implemented the item: an engine grading its own work is the weakest possible
check. Until now that rule was absolute in two independent places --
`selection_inputs_for_job` always added the implementer to the requirement's
`excluded` set, and `BuildVerifyHandler` separately hard-failed a reviewer that
matched the implementer.

On a one-engine pool (`vibey work --engines qwenloop`, the sovereign
single-vendor case the project is meant to support) that combination had no
exit. The exclusion emptied the eligible set, `NoEligibleEngine` became a
`CapacityDeferred`, and BUILD deferred the same job forever: no park, no
failure, no human gate, and nothing in the ledger. The handler's `VIBEY`
failure never even ran, because selection never got that far. A rule that is
absolute in two places, with no third place that notices they have deadlocked,
is not a stronger rule -- it is a silent stall.

## Decision

Independence stays the default and becomes waivable in exactly one case: when
excluding the implementer would leave the worker's **configured** pool (its
adapters, narrowed by `--engines`) with no reviewer at all.

1. **One definition.** The waiver is derived once, in
   `selection_inputs_for_job`, and returned as `SelectionInputs.independence_waived`.
   `BuildVerifyHandler` asks that same derivation rather than re-deriving the
   rule. Two copies of one rule disagreeing is the defect this ADR exists to
   kill; a third copy would recreate it.
2. **Configuration, never live health.** The pool is what the operator
   configured. Keying off health would silently drop independence whenever the
   second engine happened to be circuit-open -- a much worse trade, and one
   nobody asked for.
3. **Never silent.** A waived review is recorded as a `DecisionRecorded`
   (`d_verify_independence_<item>`) carrying the pool and
   `independent_review: false`, and the job's own result carries
   `independent_review` either way. The decision is written **on the success
   path only**: the ledger is append-only, so a decision saying an item "was
   verified" must not exist until it was.
4. **The adopter decides.** `verify.require_independent_review = true` in the
   project config restores the absolute rule, in which case no waiver policy is
   wired and a solo-pool verify fails as before (ADR-0018). The default is the
   permissive reading because the measured alternative was an unrecoverable
   stall, and because a project that would rather stall can say so in one line.

## Consequences

- A single-engine project can finish BUILD. That is the whole point.
- A self-review is visibly weaker than an independent one, and the record says
  so in the two places a human or a successor engine reads: the ledger's
  decision log and the job result.
- The waiver is *not* a general escape hatch. A two-engine pool with one
  unhealthy engine still defers -- the same stall by a different door -- and
  closing that is its own slice, not this one.
- ADR-0020: this ADR records the decision. Whether §2.3's relaxation should
  also be spelled out as ratified sub-doctrine text in the governance corpus is
  the operator's call, and the canon is deliberately not edited here.

## Alternatives considered

- **Park for a human.** Honest, but it makes an unattended single-vendor BUILD
  impossible by construction, and the operator can opt into exactly this by
  setting `verify.require_independent_review` and answering the failure.
- **Let the handler keep its own copy of the rule and just soften it.** That is
  the shape that produced the deadlock. Rejected.
- **Waive on live health rather than configuration.** Cheaper to implement and
  strictly worse: it drops independence for reasons the operator never chose.
