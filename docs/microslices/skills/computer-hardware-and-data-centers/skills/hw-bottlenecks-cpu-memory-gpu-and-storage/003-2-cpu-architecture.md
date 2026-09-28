---
id: skill-2-cpu-architecture-ce51bc2c95
purpose: 2 cpu architecture
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-bottlenecks-cpu-memory-gpu-and-storage/SKILL.md
requires: ["skill-1-where-the-bottleneck-actually-lives-99d9be43b9"]
links: ["skill-3-the-memory-hierarchy-acc9d0e180"]
---

## §2. CPU Architecture

```
⚠️ THE PIPELINE  fetch → decode → execute → memory → writeback
⚠️ THE PERFORMANCE EQUATION  ⚠️ time = instructions × CPI × cycle
   time. ⚠️ THREE independent levers, which is why "GHz" alone
   tells you almost nothing across architectures
⚠️ ILP TECHNIQUES  superscalar (multiple instructions per cycle) ·
   out-of-order execution · ⚠️ BRANCH PREDICTION (⚠️ a mispredict
   flushes the pipeline and costs tens of cycles) · speculation ·
   SMT/hyperthreading
⚠️ SIMD  AVX, NEON, SVE — data parallelism within a core
⚠️ HETEROGENEOUS CORES  ⚠️ performance and efficiency cores, which
   makes SCHEDULING a first-order problem and is why OS scheduler
   quality now visibly affects benchmarks
⚠️ ISA  x86-64 · ⚠️ ARM (now genuinely competitive in servers and
   dominant in mobile) · RISC-V (open, growing)
⚠️ THE POWER REALITY (see a semiconductor reference §5)
   ⚠️ Frequency scaling stopped; ⚠️ boost behaviour is now
   thermally and power-limited, so SUSTAINED performance can
   differ enormously from peak
⚠️ SPECULATIVE EXECUTION SIDE CHANNELS  ⚠️ Spectre/Meltdown class —
   ⚠️ the mitigations cost real performance, which is why old
   benchmarks are not comparable to patched systems
```

---
