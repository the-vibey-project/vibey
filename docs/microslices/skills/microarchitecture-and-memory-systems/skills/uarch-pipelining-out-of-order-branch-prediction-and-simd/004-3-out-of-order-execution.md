---
id: skill-3-out-of-order-execution-1711d24fb2
purpose: 3 out of order execution
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-pipelining-out-of-order-branch-prediction-and-simd/SKILL.md
requires: ["skill-2-pipelining-6ffdd3e794"]
links: ["skill-4-branch-prediction-91d71e6dc6"]
---

## §3. ⚠️ Out-of-Order Execution

> **⚠️ The heart of modern high-performance CPUs, and the mechanism whose details matter
> most for both performance and §19 → `uarch-dram-memory-controllers-power-and-security`'s security.**
```
⚠️ THE PRINCIPLE  ⚠️ execute instructions when their OPERANDS are
   ready rather than in program order — then RETIRE them in
   program order so the architectural state stays correct
⚠️ THE STRUCTURES
   ⚠️ REGISTER RENAMING  ⚠️ map architectural registers to a much
      larger physical register file. ⚠️ ELIMINATES WAR and WAW
      hazards entirely, which is why "there are only 16 registers"
      is not the constraint people assume
   ⚠️ REORDER BUFFER (ROB)  ⚠️ holds instructions in program order
      until retirement. ⚠️ ROB SIZE bounds how far ahead the core
      can look — the "instruction window"
   ⚠️ RESERVATION STATIONS / scheduler  hold instructions waiting
      for operands, wake them when ready
   ⚠️ LOAD-STORE QUEUE  ⚠️ tracks memory ordering, does STORE-TO-LOAD
      FORWARDING, and handles memory DISAMBIGUATION — deciding
      whether a load may pass an earlier store whose address isn't
      known yet. ⚠️ Speculating wrongly here costs a replay
⚠️ ⚠️ WHY IT MATTERS: the core needs a deep window to hide a
   ~200-cycle memory latency. ⚠️ But it must also be able to
   UNDO everything speculative — and the fact that it undoes
   architectural state while leaving MICROARCHITECTURAL traces
   is precisely §19
⚠️ THE LIMITS  ⚠️ ILP in real code is finite; window size, rename
   width and scheduler complexity all scale badly in power and
   area, which is why cores stopped getting dramatically wider
```

---
