---
id: skill-6-interconnect-348ceebf77
purpose: 6 interconnect
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-interconnect-power-thermals-and-networking/SKILL.md
requires: []
links: ["skill-7-power-supplies-a2ed6be438"]
---

## §6. Interconnect

**⚠️ PCIe** — ⚠️ **lanes and generations, with bandwidth roughly doubling per generation;
⚠️ lane ALLOCATION is the practical constraint on a consumer board, where the CPU provides
a fixed number and the chipset multiplexes the rest.**
**⚠️ Check whether a slot is CPU-attached or chipset-attached** — ⚠️ **it matters for
latency and for contention.**
**⚠️ CXL** builds on PCIe to provide cache-coherent access to attached memory —
⚠️ **enabling memory expansion, pooling and disaggregation, which is genuinely significant
for servers.**
**⚠️ Chipset, DMI/Infinity Fabric, and the SoC trend** — ⚠️ **integrating memory controller,
I/O and increasingly memory itself onto the package, which improves latency and reduces
upgradeability.**
**⚠️ Signal integrity** (see an electromagnetism reference) — ⚠️ **at PCIe 5 and 6 speeds,
trace length, via stubs and connector quality genuinely matter, and RETIMERS exist because
of it.**

---
