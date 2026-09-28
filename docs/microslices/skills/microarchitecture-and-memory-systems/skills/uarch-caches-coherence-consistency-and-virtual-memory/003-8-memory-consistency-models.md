---
id: skill-8-memory-consistency-models-70d54fc854
purpose: 8 memory consistency models
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-caches-coherence-consistency-and-virtual-memory/SKILL.md
requires: ["skill-7-cache-coherence-d30980d133"]
links: ["skill-9-virtual-memory-and-translation-e74ba766dd"]
---

## §8. ⚠️ Memory Consistency Models

> **⚠️ The most conceptually difficult topic here, and the one most often misunderstood.
> COHERENCE (§7) is about a single location; CONSISTENCY is about the ORDER of operations
> across different locations.**
```
⚠️ SEQUENTIAL CONSISTENCY  ⚠️ the intuitive model — as if all
   operations from all threads interleaved in some global order
   consistent with each program's order. ⚠️ NO REAL HARDWARE
   PROVIDES THIS, because it forbids too many optimizations
⚠️ ⚠️ WHAT REAL HARDWARE DOES
   ⚠️ x86-TSO  ⚠️ relatively strong: stores are buffered, so a
      LOAD MAY BE REORDERED BEFORE AN EARLIER STORE to a
      different address. ⚠️ That one relaxation is enough to break
      naive Dekker-style algorithms
   ⚠️ ARM and RISC-V  ⚠️ WEAKLY ORDERED — loads and stores can be
      reordered much more freely. ⚠️ Code that is correct on x86
      can be BROKEN on ARM with no source change, and this
      surprises people porting between them
⚠️ FENCES / BARRIERS  ⚠️ explicitly constrain reordering; acquire,
   release, and full barriers
⚠️ LANGUAGE MEMORY MODELS  ⚠️ C++11 and Java define their own
   models so portable concurrent code is possible at all.
   ⚠️ memory_order_relaxed / acquire / release / seq_cst map onto
   whatever the hardware needs
⚠️ ⚠️ THE COMPILER REORDERS TOO. ⚠️ A hardware fence without a
   compiler barrier is not enough, and "volatile" is NOT a
   synchronization primitive in C/C++
```
**⚠️ The practical guidance**: ⚠️ **use the language's atomics and locks rather than
hand-rolled fences; ⚠️ if you write lock-free code, TEST ON WEAK HARDWARE, because x86
hides bugs that ARM exposes.**

---
