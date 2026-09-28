---
id: skill-22-measuring-it-407fbb402b
purpose: 22 measuring it
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-isa-simulation-measurement-roofline-and-specialization/SKILL.md
requires: ["skill-21-simulation-and-modelling-82074833cc"]
links: ["skill-23-roofline-and-fundamental-limits-abf5a4bc78"]
---

## §22. ⚠️ Measuring It

> **⚠️ The practical skill that makes everything above actionable.**
```
⚠️ HARDWARE PERFORMANCE COUNTERS  ⚠️ cycles, instructions, cache
   misses at each level, branch mispredicts, TLB misses, stall
   cycles by reason
   ⚠️ perf, VTune, uProf, Nsight, and vendor equivalents
⚠️ ⚠️ TOP-DOWN MICROARCHITECTURE ANALYSIS is the right method:
   classify each issue slot as ⚠️ RETIRING · BAD SPECULATION ·
   ⚠️ FRONTEND BOUND · ⚠️ BACKEND BOUND, then drill down.
   ⚠️ This tells you WHICH of §3, §4, §6 or §15 is your problem,
   rather than guessing
⚠️ IPC ALONE IS MISLEADING  ⚠️ high IPC on wasted work is not
   good, and low IPC on a memory-bound kernel may be optimal
⚠️ THE PITFALLS  ⚠️ frequency scaling during measurement (§18) ·
   ⚠️ cold caches and TLBs · ⚠️ counter multiplexing when you ask
   for too many events · ⚠️ observer effect · NUMA placement ·
   ⚠️ and comparing across mitigation states (§19)
⚠️ ROOFLINE (§23) tells you the CEILING; counters tell you where
   you actually are
```

---
