---
id: skill-11-gpu-microarchitecture-b7d127b156
purpose: 11 gpu microarchitecture
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-gpu-npu-dataflow-and-numeric-formats/SKILL.md
requires: []
links: ["skill-12-gpu-memory-systems-f3c1f929b2"]
---

## §11. GPU Microarchitecture

```
⚠️ THE ORGANIZING PRINCIPLE  ⚠️ hide latency with PARALLELISM
   rather than with caches and speculation. ⚠️ When a warp stalls
   on memory, the scheduler switches to another — so latency is
   tolerated rather than reduced
⚠️ THE HIERARCHY  ⚠️ SM / CU containing warp schedulers, register
   file, SIMD lanes, ⚠️ SHARED MEMORY / LDS (⚠️ software-managed
   scratchpad — the key GPU-specific resource), L1, tensor units
⚠️ SIMT  ⚠️ threads grouped into warps (32) or wavefronts (32/64)
   executing in lockstep
   ⚠️ WARP DIVERGENCE — ⚠️ if threads in a warp take different
   branch paths, the hardware SERIALIZES them. ⚠️ Worst case a
   32-way divergent branch costs 32× — the single biggest GPU
   performance trap
⚠️ ⚠️ OCCUPANCY  active warps per SM, limited by ⚠️ REGISTERS PER
   THREAD, ⚠️ SHARED MEMORY PER BLOCK, and block size.
   ⚠️ GOTCHA: higher occupancy is NOT automatically better —
   beyond the point where latency is hidden, more warps just
   thrash cache. ⚠️ Register-heavy kernels with low occupancy
   frequently outperform "optimized" high-occupancy versions
⚠️ MEMORY COALESCING  ⚠️ consecutive threads accessing consecutive
   addresses combine into one transaction; ⚠️ scattered access
   multiplies the transaction count and is the second big trap
⚠️ BANK CONFLICTS in shared memory ⚠️ serialize access
⚠️ THE REGISTER FILE IS HUGE  ⚠️ larger than the L1 cache — because
   thousands of resident threads each need private state
```

---
