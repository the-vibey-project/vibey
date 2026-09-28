---
id: skill-8-the-memory-model-c7464a05fc
purpose: 8 the memory model
source: src/vibey_tools/skills/plugins/arm-architecture-deep-dive/skills/arm-aarch64-exception-levels-memory-model-and-mmu/SKILL.md
requires: ["skill-7-exception-levels-901f596968"]
links: ["skill-9-mmu-and-translation-f9ba1ef00d"]
---

## §8. ⚠️ The Memory Model

> **⚠️ §1 → `arm-what-arm-is-licensing-families-and-isa-generations`'s second organizing idea, and the thing most likely to bite you. See a
> microarchitecture reference §8 for consistency models generally.**
```
⚠️ ⚠️ ARM IS WEAKLY ORDERED. ⚠️ Loads and stores can be reordered
   far more freely than on x86-TSO — ⚠️ store-store, load-load,
   load-store and store-load reordering are all permitted where
   no dependency exists
⚠️ ⚠️ THE PRACTICAL CONSEQUENCE: CONCURRENT CODE THAT IS CORRECT
   ON x86 CAN BE BROKEN ON ARM WITH NO SOURCE CHANGE. ⚠️ x86's
   stronger model HIDES missing synchronization. ⚠️ The bugs are
   intermittent, load-dependent and hard to reproduce
⚠️ THE BARRIERS
   ⚠️ DMB  data memory barrier — orders memory accesses
   ⚠️ DSB  data synchronization barrier — stronger, waits for
      completion
   ⚠️ ISB  instruction synchronization barrier — ⚠️ needed after
      changing system state that affects instruction fetch
   ⚠️ Each takes a SHAREABILITY DOMAIN and access-type qualifier
      (ISH, OSH, NSH; LD, ST) — ⚠️ using the weakest sufficient
      variant matters for performance
⚠️ ⚠️ ACQUIRE/RELEASE IS BUILT INTO THE INSTRUCTIONS
   ⚠️ LDAR (load-acquire) and STLR (store-release) — ⚠️ ordering
   semantics without a separate barrier, and generally FASTER
   than a full DMB. ⚠️ This is the idiom to use
⚠️ ⚠️ ADDRESS, DATA AND CONTROL DEPENDENCIES provide some
   ordering for free — ⚠️ and relying on them is subtle and
   compiler-hostile, because the compiler may optimize the
   dependency away
⚠️ MEMORY TYPES  ⚠️ NORMAL (cacheable, reorderable, speculatable)
   vs ⚠️ DEVICE (nGnRnE through nGRE — ⚠️ device memory
   attributes control gathering, reordering and early
   acknowledgement, and getting these wrong on MMIO causes
   baffling driver bugs)
⚠️ CACHE MAINTENANCE  ⚠️ ARM requires explicit cache maintenance
   in places x86 does not, particularly for ⚠️ SELF-MODIFYING
   CODE and JITs — ⚠️ instruction and data caches are not
   coherent, so a JIT must clean D-cache and invalidate I-cache
```

---
