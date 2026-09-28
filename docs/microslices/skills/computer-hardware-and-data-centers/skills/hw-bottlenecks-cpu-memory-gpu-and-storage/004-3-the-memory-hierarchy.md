---
id: skill-3-the-memory-hierarchy-acc9d0e180
purpose: 3 the memory hierarchy
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-bottlenecks-cpu-memory-gpu-and-storage/SKILL.md
requires: ["skill-2-cpu-architecture-ce51bc2c95"]
links: ["skill-4-gpus-and-accelerators-74f38901dd"]
---

## §3. ⚠️ The Memory Hierarchy

> **⚠️ The most important section for understanding real performance. The processor-memory
> gap is the defining problem of modern computer architecture.**
```
⚠️ THE LATENCY LADDER, in rough cycle counts — ⚠️ the ORDERS OF
   MAGNITUDE are the point, not the exact numbers
   ⚠️ Register        ~1 cycle
   ⚠️ L1 cache        ~4 cycles
   ⚠️ L2              ~12 cycles
   ⚠️ L3              ~40 cycles
   ⚠️ MAIN MEMORY     ⚠️ ~200-300 cycles
   ⚠️ NVMe SSD        ⚠️ ~100,000+ cycles
   ⚠️ Network/disk    millions
⚠️ ⚠️ A MAIN MEMORY ACCESS COSTS HUNDREDS OF CYCLES. A modern core
   can execute HUNDREDS OF INSTRUCTIONS in the time one cache miss
   takes. ⚠️ This is why cache behaviour dominates real performance
⚠️ WHY CACHES WORK  ⚠️ LOCALITY — temporal (reuse soon) and spatial
   (nearby addresses soon). ⚠️ Programs that violate locality get
   no benefit and run at memory speed
⚠️ CACHE LINES  ⚠️ typically 64 bytes — you always fetch a whole
   line. ⚠️ Hence FALSE SHARING, where two threads writing
   different variables in the SAME LINE destroy performance
   through cache coherence traffic
⚠️ DRAM  ⚠️ latency has improved remarkably little across
   generations; BANDWIDTH has improved enormously. ⚠️ DDR5 and
   channel count matter more than raw MT/s for many workloads
⚠️ NUMA  ⚠️ on multi-socket systems, memory attached to another
   socket is substantially slower. ⚠️ Ignoring NUMA placement is
   a classic and large performance loss
⚠️ VIRTUAL MEMORY and the TLB  ⚠️ TLB misses are their own penalty;
   huge pages exist to reduce them
```
> **⚠️ GOTCHA — "add more RAM" and "get faster RAM" solve different problems.** ⚠️ **Running
> out of capacity causes swapping and is catastrophic; once you have enough, more capacity
> does nothing.** **⚠️ Latency and bandwidth improvements are usually single-digit-percent
> gains outside specific workloads — and integrated GPUs, which share system memory, are
> the notable exception where bandwidth genuinely matters.**

---
