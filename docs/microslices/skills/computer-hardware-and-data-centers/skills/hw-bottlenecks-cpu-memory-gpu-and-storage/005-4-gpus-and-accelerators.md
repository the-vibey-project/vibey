---
id: skill-4-gpus-and-accelerators-74f38901dd
purpose: 4 gpus and accelerators
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-bottlenecks-cpu-memory-gpu-and-storage/SKILL.md
requires: ["skill-3-the-memory-hierarchy-acc9d0e180"]
links: ["skill-5-storage-eb804f9ff8"]
---

## §4. GPUs and Accelerators

**⚠️ The architectural difference is throughput versus latency**: ⚠️ **a CPU minimizes the
latency of one thread; a GPU maximizes aggregate throughput by running enormous numbers of
threads and HIDING memory latency by switching between them.**
```
⚠️ SIMT execution · ⚠️ WARP/wavefront divergence (⚠️ branches within
   a warp serialize — the main GPU performance trap)
⚠️ MEMORY IS USUALLY THE LIMIT  ⚠️ GDDR or HBM bandwidth, and
   ⚠️ VRAM CAPACITY is the hard wall for AI work — a model that
   doesn't fit doesn't run, regardless of compute
⚠️ TENSOR/MATRIX UNITS  ⚠️ and reduced precision (FP16, BF16, FP8,
   INT8) is where the headline TOPS numbers come from —
   ⚠️ always check WHICH precision a quoted figure refers to
⚠️ ARITHMETIC INTENSITY and the ROOFLINE MODEL  ⚠️ FLOPs per byte
   moved determines whether you are compute-bound or
   memory-bandwidth-bound. ⚠️ Most real kernels are bandwidth-bound
⚠️ OTHER ACCELERATORS  NPUs · TPUs and custom ASICs · FPGAs
   (⚠️ reconfigurable, good for low latency and evolving protocols,
   hard to program) · DPUs/SmartNICs
```

---
