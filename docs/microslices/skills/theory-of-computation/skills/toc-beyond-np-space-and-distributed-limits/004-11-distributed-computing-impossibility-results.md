---
id: skill-11-distributed-computing-impossibility-results-9e7cb01903
purpose: 11 distributed computing impossibility results
source: src/vibey_tools/skills/plugins/theory-of-computation/skills/toc-beyond-np-space-and-distributed-limits/SKILL.md
requires: ["skill-10-space-and-memory-0e7de93f11"]
links: []
---

## §11. Distributed Computing Impossibility Results

**[DURABLE] Theory's most immediately actionable contribution to systems engineering.**
These are theorems, not architectural opinions, and violating them is not a design
trade-off — it's a claim to have solved something proven impossible.

**FLP impossibility (1985)**: **in an asynchronous system with even one faulty process,
there is no deterministic algorithm guaranteeing consensus.** ⚠️ **This is why every real
consensus protocol uses timeouts, randomization, or a partial-synchrony assumption** —
Paxos and Raft don't refute FLP, they add an assumption FLP excludes. **Anyone claiming
deterministic asynchronous consensus is wrong.**

**CAP**: under network **partition**, choose consistency or availability. **⚠️ CAP is
routinely over-applied.** It is about behaviour *during a partition*, not a general licence
to be inconsistent, and the more useful modern framing is **PACELC**: under Partition,
choose A or C; **Else**, choose Latency or Consistency — which is the trade-off you're
actually making 99.9% of the time.

**The Two Generals Problem**: no protocol achieves guaranteed agreement over a lossy
channel. **⚠️ This is why exactly-once delivery does not exist**, and why the achievable
target is at-least-once plus idempotency (which is why §3 → `toc-automata-regex-and-parsing` of a payments reference and this
paragraph are the same fact).

**Byzantine fault tolerance**: tolerating arbitrary (malicious) faults requires **n > 3f**
nodes for f faults.

**Linearizability, serializability, and the consistency zoo** — these are formal
definitions with precise meanings, and **"eventual consistency" without specifying which
model is not a specification.**

**[DURABLE] The practical instruction**: when a design assumes reliable delivery, ordered
delivery, synchronized clocks, or partition-free operation, **name the assumption
explicitly** — because you have just chosen a side of one of these theorems, and it should
be a decision rather than an accident.
