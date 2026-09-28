---
id: skill-10-prefetching-f2d157a49c
purpose: 10 prefetching
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-caches-coherence-consistency-and-virtual-memory/SKILL.md
requires: ["skill-9-virtual-memory-and-translation-e74ba766dd"]
links: []
---

## §10. Prefetching

**⚠️ Fetch data before it's requested, to hide latency.**
⚠️ **Hardware prefetchers detect sequential streams and constant strides, and increasingly
more complex patterns; ⚠️ they cannot follow pointer chasing, which is why linked lists
and trees perform so badly relative to arrays.**
**⚠️ Software prefetch instructions** exist and ⚠️ **are difficult to use well — too early
and the line is evicted, too late and you gained nothing.**
**⚠️ The costs**: ⚠️ **useless prefetches consume bandwidth and can EVICT useful data, so an
aggressive prefetcher can make a bandwidth-bound workload slower.**
**⚠️ The design implication**: ⚠️ **data structures with predictable access patterns are
fast almost for free; ⚠️ this is a large part of why structure-of-arrays beats array-of-
structures in performance-critical code.**

---

# PART II — THROUGHPUT ARCHITECTURES
