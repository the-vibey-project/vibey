---
id: skill-2-the-machine-you-are-actually-programming-5042ea6ca7
purpose: 2 the machine you are actually programming
source: src/vibey_tools/skills/plugins/algorithms-deep-dive/skills/algo-foundations-and-machine-model/SKILL.md
requires: ["skill-1-choosing-b2a655545d"]
links: []
---

## §2. The Machine You Are Actually Programming

**[DURABLE] This section explains most of the gap between predicted and measured
performance, and it is the single highest-value part of this document.**

### 2.1 The memory hierarchy

```
register       <1 ns      ~0 cycles
L1 cache        ~1 ns      ~4 cycles       32–64 KB
L2 cache        ~4 ns     ~12 cycles       256 KB – 2 MB
L3 cache       ~15 ns     ~40 cycles       8–64 MB, shared
DRAM           ~80 ns   ~200–300 cycles    ⚠️ THE CLIFF
NVMe SSD       ~50 µs                      ~100,000 cycles
network         ~1 ms+
```

**[DURABLE] The consequences that should change your defaults:**
- **The cache line is 64 bytes.** That's the unit of transfer. Touching one byte costs you
  a line.
- **Sequential access is prefetched; random access is not.** A hardware prefetcher can
  hide latency on a predictable stride and does nothing for pointer chasing.
- **⚠️ This is why a linked list loses to an array with identical asymptotics.** The array
  scan is ~64 bytes per miss, prefetched; the list is one miss per node, unprefetchable.
  **A "O(n) scan" on a contiguous array often beats an "O(log n) search" on a tree for
  n in the thousands** — and this is the most common surprise for people who learned
  complexity before they learned hardware.
- **Structure of Arrays beats Array of Structures** when you touch one field across many
  records. You stop loading the fields you don't need.
- **Working set size is a step function.** Performance is fine until your data stops
  fitting in a cache level, then falls off a cliff. **Benchmark across sizes, not at one
  size** (§13 → `algo-probabilistic-concurrency-and-measurement`).

### 2.2 Branches

**~15–20 cycles for a mispredict.** Predictable branches are nearly free; unpredictable
ones are catastrophic. **This is why branchless techniques exist**: conditional moves,
arithmetic masking, and the branchless partitioning that makes modern quicksort fast (§7 → `algo-core-algorithms`).

**⚠️ It's also why sorted input can make code *faster*** — the famous "why is processing a
sorted array faster" effect is entirely branch prediction, and it's a useful sanity check
on whether you understand your own profile.

### 2.3 Allocation, indirection, and the rest

**Allocation is expensive and often the real cost** in a structure that looks
algorithmically fine. Pre-allocate, pool, reuse, and prefer structures that allocate in
blocks over ones that allocate per element. **In GC languages, allocation is future GC
pressure**, and a GC pause is a latency spike attributed to the wrong place.

**Pointer indirection costs a potential cache miss each hop.** Every level of a pointer
structure is a chance to stall.

**SIMD** processes 4–16 elements per instruction. Autovectorization is real but fragile;
the structures that vectorize are flat, contiguous, and branch-light. **This is a data
layout question before it's an instruction-selection question.**

**[DURABLE] The synthesis: the constant factor is not a footnote in this domain — it
routinely spans two orders of magnitude, and it is determined mostly by memory layout.**
