---
id: skill-7-cache-coherence-d30980d133
purpose: 7 cache coherence
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-caches-coherence-consistency-and-virtual-memory/SKILL.md
requires: ["skill-6-cache-organization-373d70d3a8"]
links: ["skill-8-memory-consistency-models-70d54fc854"]
---

## §7. ⚠️ Cache Coherence

> **⚠️ How multiple caches maintain a consistent view of memory — and the source of
> multicore scaling limits.**
```
⚠️ MESI and relatives  each line is Modified / Exclusive / Shared /
   Invalid. ⚠️ MOESI adds Owned; MESIF adds Forward
   ⚠️ THE INVARIANT: one writer OR many readers, never both
⚠️ PROTOCOL FAMILIES  ⚠️ SNOOPING (every cache watches a shared
   bus — simple, doesn't scale) vs ⚠️ DIRECTORY-BASED (a directory
   tracks who holds each line — scales, adds latency and storage)
⚠️ ⚠️ THE COST  a write to a SHARED line requires INVALIDATING every
   other copy and waiting. ⚠️ A contended line ping-ponging between
   cores can be orders of magnitude slower than uncontended access
⚠️ THEREFORE  ⚠️ atomics and locks are expensive not because of the
   instruction but because of the COHERENCE TRAFFIC. ⚠️ An
   uncontended atomic is cheap; a contended one is not, and the
   difference is enormous
⚠️ SCALABLE SYNCHRONIZATION  ⚠️ MCS and ticket locks queue waiters
   to avoid all-cores-spinning-on-one-line; ⚠️ RCU and per-CPU
   data avoid sharing altogether — which is the real answer
⚠️ NUMA  ⚠️ coherence across sockets is far more expensive again
```

---
