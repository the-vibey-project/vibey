---
id: skill-12-gpu-memory-systems-f3c1f929b2
purpose: 12 gpu memory systems
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-gpu-npu-dataflow-and-numeric-formats/SKILL.md
requires: ["skill-11-gpu-microarchitecture-b7d127b156"]
links: ["skill-13-npus-and-dataflow-architectures-2b6c89ea98"]
---

## §12. GPU Memory Systems

**⚠️ GDDR versus HBM**: ⚠️ **GDDR is cheaper with fewer, faster pins; ⚠️ HBM uses stacked
dies and an extremely wide interface (§15 → `uarch-dram-memory-controllers-power-and-security`, and see a semiconductor reference §20) for
far higher bandwidth per watt at much higher cost.**
**⚠️ Bandwidth is the design centre**: ⚠️ **GPUs are usually bandwidth-bound (§23 → `uarch-isa-simulation-measurement-roofline-and-specialization`), so
arithmetic intensity determines whether you can use the compute at all.**
**⚠️ Caches on GPUs behave differently**: ⚠️ **smaller per thread, and used more for
coalescing and reuse across warps than for latency reduction.**
**⚠️ Unified/managed memory** simplifies programming and ⚠️ **can hide expensive migration
— convenience that costs performance silently.**
**⚠️ Multi-GPU**: ⚠️ **NVLink and Infinity Fabric provide far higher bandwidth than PCIe,
and collective operations make the interconnect part of the compute path** (see a
computer-hardware reference §21).

---
