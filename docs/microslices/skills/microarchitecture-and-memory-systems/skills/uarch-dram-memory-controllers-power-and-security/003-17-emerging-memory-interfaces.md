---
id: skill-17-emerging-memory-interfaces-a711ebe857
purpose: 17 emerging memory interfaces
source: src/vibey_tools/skills/plugins/microarchitecture-and-memory-systems/skills/uarch-dram-memory-controllers-power-and-security/SKILL.md
requires: ["skill-16-memory-controllers-f61118b65c"]
links: ["skill-18-power-and-clocking-48545d57bd"]
---

## §17. Emerging Memory Interfaces

**⚠️ HBM** (see a semiconductor reference §20): ⚠️ **stacked dies, TSVs, a very wide slow
interface — bandwidth through WIDTH rather than frequency, which is far more energy
efficient per bit.**
**⚠️ CXL** — ⚠️ **cache-coherent attach over PCIe, enabling memory EXPANSION, POOLING
across hosts, and tiering.** ⚠️ **The catch is latency: CXL memory is meaningfully slower
than direct-attached, so it is a tier, not a replacement.**
**⚠️ Processing-in-memory** — ⚠️ **real research and some commercial products, attacking
§13 → `uarch-gpu-npu-dataflow-and-numeric-formats`'s data movement cost directly.**
**⚠️ Persistent memory** — ⚠️ **Optane's discontinuation is a cautionary tale about a
technically interesting tier that couldn't find a durable economic niche between DRAM and
NAND.**
**⚠️ See §25.2 → `uarch-reference` for where standard DRAM interfaces are going.**

---

# PART IV — CROSS-CUTTING
