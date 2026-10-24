# 0094 — The cost of routing the cache through its lane is accepted

**Status:** proposed · **Date:** 2026-10-24 · **Cites:** sub-doctrines 8.f, 8.g · **Related:** ADR-0044, ADR-0045 · **Ruling:** #668, item 2

## Context

Sub-doctrine 8.f says every sovereign surface runs in one lane driven by the bus, and that the cost of
routing the cache that way "is measured and published with the design". The design is the storm's draft
`docs/plans/qwenstorm-3.0.0/specs/ADR-surface-lanes.md`, which that file calls "0047". It was never
merged as an ADR, and the number 0047 in this tree is *the toil is automated*, so this record carries
the decision and the draft carries the argument.

The draft's section 10 states the cost plainly: a cache read crosses the broker twice. Its figures:

| path | p50 | p99 | source |
|---|---|---|---|
| today's `RedisCacheAdapter.get` (a new connection per read) | 0.18 ms | 0.42 to 0.51 ms | measured, 2026-09-22, the operator's laptop |
| one persistent connection | 0.08 ms | 0.17 to 0.21 ms | measured |
| pipelined, per GET | 0.006 ms | 0.011 to 0.033 ms | measured |
| through the lane, a hit in its memo | about 0.4 to 1.0 ms | about 2 to 5 ms | **estimated** |
| through the lane, a memo miss | about 0.5 to 1.1 ms | about 2 to 5 ms | **estimated** |

By that estimate a read through the lane is 2 to 6 times today's adapter at p50 and 4 to 10 times at p99,
and one process is the ceiling for cache reads in a deployment (an estimated 5,000 to 15,000 reads a
second). Today the cache has no reader, so no hot path pays it.

## Decision

**The operator accepts that cost, as published.** The cache stays behind its lane and reads are not
exempted from 8.f. The cache is for values that cost well over the lane's p99 (about 5 ms) to produce, or
that must be shared between processes; sub-millisecond memoization inside one process is not a use of the
cache surface and stays a local dictionary.

The draft named two other ways out, and the operator took neither: amend 8.f to exempt cache reads, or
drop the cache surface.

## Consequences

- **Nothing is built yet.** No lane code exists in the tree. This record removes a blocker for the lane
  that flips the default (the draft's S33); it does not remove the others: the lanes merged, the cluster
  smoke green in `queue` mode, and 8.f ratified.
- **The measurement is still owed, and is not waived.** The draft's lane S32 measures p50, p95 and p99 and
  throughput for four modes (the direct adapter, the pipelined adapter, the queue with a memo hit, the
  queue with a memo miss) at concurrency 1 and 16, on the operator's laptop and on a Linux node. Until it
  runs, the lane figures above are estimates, and what was accepted is the cost *as estimated*.
- **Revisit if the measurement lands outside the ranges above.** A p99 far past 5 ms would be new
  evidence about a cost accepted on an estimate, and this decision should be taken again.
- **Rule status.** This is a decision under an existing rule (8.f), not a new rule, so it owes no
  sub-doctrine (ADR-0020).
