---
id: skill-23-roofline-and-fundamental-limits-abf5a4bc78
purpose: 23 roofline and fundamental limits
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-isa-simulation-measurement-roofline-and-specialization/SKILL.md
requires: ["skill-22-measuring-it-407fbb402b"]
links: ["skill-24-specialization-9433486afc"]
---

## §23. Roofline and Fundamental Limits

**⚠️ ARITHMETIC INTENSITY = FLOPs performed per byte moved from memory.**
⚠️ **Plot achievable performance against it: a sloped region where you're
BANDWIDTH-BOUND, and a flat region where you're COMPUTE-BOUND.**
**⚠️ The uncomfortable truth**: ⚠️ **most real kernels sit in the bandwidth-bound region,
which means peak FLOPS numbers are irrelevant to them and adding compute units does
nothing.**
**⚠️ The levers, in order of usefulness**: ⚠️ **raise arithmetic intensity through blocking
and fusion; reduce bytes moved through quantization (§14 → `uarch-gpu-npu-dataflow-and-numeric-formats`) and compression; improve locality
(§6 → `uarch-caches-coherence-consistency-and-virtual-memory`); and only then worry about compute.**
**⚠️ Amdahl and Gustafson** bound parallel speedup from opposite directions — ⚠️ **fixed
problem versus fixed time — and both are worth having in mind because they answer different
questions.**
**⚠️ The energy roofline** matters increasingly, given §18 → `uarch-dram-memory-controllers-power-and-security`.

---
