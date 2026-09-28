---
id: skill-1-where-the-bottleneck-actually-lives-99d9be43b9
purpose: 1 where the bottleneck actually lives
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-bottlenecks-cpu-memory-gpu-and-storage/SKILL.md
requires: ["skill-0-routing-da43b3b0b4"]
links: ["skill-2-cpu-architecture-ce51bc2c95"]
---

## §1. Where the Bottleneck Actually Lives

```
⚠️ THE HISTORICAL MIGRATION — and each shift invalidated the
   previous generation's optimization instincts
   ⚠️ 1990s   CPU clock speed
   ⚠️ 2000s   ⚠️ MEMORY LATENCY (§3) and then thermal/power limits
   ⚠️ 2010s   I/O and storage, until NVMe largely solved it
   ⚠️ Early 2020s  ⚠️ chip supply, then advanced PACKAGING and HBM
   ⚠️ NOW     ⚠️ GRID POWER AND INTERCONNECTION (§26.1)
⚠️ AMDAHL'S LAW  ⚠️ speedup is capped by the fraction you DIDN'T
   parallelize. ⚠️ Optimizing an already-fast component gains
   nothing — this is the formal version of the whole section
⚠️ THE DIAGNOSTIC DISCIPLINE  ⚠️ MEASURE before optimizing.
   ⚠️ Is it CPU-bound, memory-bound, I/O-bound, network-bound,
   or thermally throttled? (§14, §15). ⚠️ These have completely
   different fixes and people routinely guess wrong
```

---

# PART I — COMPONENTS
