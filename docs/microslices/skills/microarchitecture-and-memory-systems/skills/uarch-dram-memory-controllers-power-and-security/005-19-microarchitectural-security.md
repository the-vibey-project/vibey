---
id: skill-19-microarchitectural-security-620ea5ed6b
purpose: 19 microarchitectural security
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-dram-memory-controllers-power-and-security/SKILL.md
requires: ["skill-18-power-and-clocking-48545d57bd"]
links: []
---

## §19. ⚠️ Microarchitectural Security

> **⚠️ The class of vulnerability created by §1 → `uarch-pipelining-out-of-order-branch-prediction-and-simd`'s leak: architectural state is restored on
> misspeculation, microarchitectural state is not.**
```
⚠️ THE MECHANISM  ⚠️ 1. Get the processor to speculatively perform
   an action it shouldn't. ⚠️ 2. That action leaves a trace in
   microarchitectural state — usually a cache line. ⚠️ 3. Recover
   the trace by timing (FLUSH+RELOAD, PRIME+PROBE)
⚠️ THE FAMILIES
   ⚠️ SPECTRE  ⚠️ mistrain the branch predictor (§4) so the victim
      speculatively accesses data it shouldn't. ⚠️ Crosses
      software boundaries; ⚠️ genuinely hard to fix in hardware
      because it exploits speculation itself
   ⚠️ MELTDOWN  ⚠️ speculative access across a PRIVILEGE boundary
      before the permission check retires. ⚠️ Fixable in hardware,
      and largely fixed
   ⚠️ MDS / microarchitectural data sampling  leakage from internal
      buffers
   ⚠️ Later variants have continued to appear, which is the point
⚠️ MITIGATIONS AND THEIR COST  ⚠️ KPTI page table isolation ·
   retpolines · IBRS/IBPB · flushing buffers on switch ·
   ⚠️ DISABLING SMT in the highest-security configurations
   ⚠️ THE COSTS ARE REAL — ⚠️ which means pre-2018 benchmark
   comparisons are not valid against patched systems
⚠️ ROWHAMMER (§15) is the memory-side analogue
⚠️ CONSTANT-TIME PROGRAMMING (see a cryptography reference §17)
   ⚠️ is the software-side response: no secret-dependent branches
   or memory addresses. ⚠️ And compilers can undo it, which is
   why crypto libraries fight their own toolchains
```
