---
id: skill-6-cache-organization-373d70d3a8
purpose: 6 cache organization
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-caches-coherence-consistency-and-virtual-memory/SKILL.md
requires: []
links: ["skill-7-cache-coherence-d30980d133"]
---

## §6. Cache Organization

**⚠️ See a computer-hardware reference for the latency ladder. Here, the mechanism.**
```
⚠️ THE STRUCTURE  address splits into TAG / INDEX / OFFSET
   ⚠️ Direct-mapped (fast, conflict-prone) · fully associative
   (no conflicts, impractical) · ⚠️ N-WAY SET ASSOCIATIVE (the
   real answer, typically 8–16 way at L2/L3)
⚠️ THE THREE Cs of misses  ⚠️ COMPULSORY (first touch) ·
   CAPACITY (working set too big) · ⚠️ CONFLICT (set collisions —
   fixable by associativity or by changing the access stride)
   ⚠️ Plus COHERENCE misses in multiprocessors (§7)
⚠️ REPLACEMENT  LRU is the reference; ⚠️ real caches use
   approximations (pseudo-LRU, RRIP) because true LRU is
   expensive at high associativity
⚠️ WRITE POLICY  write-through vs ⚠️ WRITE-BACK (dominant) ·
   write-allocate vs no-write-allocate · ⚠️ WRITE COMBINING buffers
⚠️ INCLUSIVE vs EXCLUSIVE vs NINE hierarchies — ⚠️ affects
   effective capacity and coherence probe cost
⚠️ ⚠️ THE PATHOLOGIES WORTH KNOWING BY NAME
   ⚠️ FALSE SHARING  two threads writing different variables in
      the SAME LINE — coherence traffic destroys performance
      with no logical sharing at all
   ⚠️ CACHE THRASHING from a stride that maps everything to one set
      (⚠️ powers-of-two array dimensions are the classic cause —
      which is why padding arrays can produce large speedups)
   ⚠️ 4K ALIASING between loads and stores
```

---
