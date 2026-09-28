---
id: skill-2-pipelining-6ffdd3e794
purpose: 2 pipelining
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-pipelining-out-of-order-branch-prediction-and-simd/SKILL.md
requires: ["skill-1-architecture-versus-microarchitecture-72f3eeb537"]
links: ["skill-3-out-of-order-execution-1711d24fb2"]
---

## §2. Pipelining

**⚠️ Overlap instruction execution by splitting it into stages** — ⚠️ **throughput rises to
one instruction per cycle in the ideal case while LATENCY per instruction rises slightly.**
```
⚠️ THE HAZARDS
   ⚠️ STRUCTURAL  two instructions want the same resource
   ⚠️ DATA  ⚠️ RAW (true dependency — the real one) · WAR and WAW
      (⚠️ FALSE dependencies caused by reusing register NAMES —
      and register renaming eliminates them entirely, §3)
   ⚠️ CONTROL  branches (§4)
⚠️ FORWARDING/BYPASSING  route a result directly from one stage to
   another rather than waiting for writeback
⚠️ DEEPER PIPELINES  higher clock, ⚠️ and a far larger mispredict
   penalty. ⚠️ The Pentium 4 is the canonical lesson in taking
   this too far
⚠️ MODERN DEPTHS  roughly 14–20 stages, with the mispredict
   penalty in the same order of magnitude
```

---
