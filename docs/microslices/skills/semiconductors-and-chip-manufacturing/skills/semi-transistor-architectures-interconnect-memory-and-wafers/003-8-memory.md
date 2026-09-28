---
id: skill-8-memory-d71cdea313
purpose: 8 memory
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-transistor-architectures-interconnect-memory-and-wafers/SKILL.md
requires: ["skill-7-interconnect-4968b8a435"]
links: ["skill-9-from-sand-to-wafer-f48c6474cc"]
---

## §8. Memory

```
⚠️ SRAM  6 transistors per bit, fast, ⚠️ volatile, ⚠️ EXPENSIVE IN
   AREA. ⚠️ Critically, SRAM HAS SCALED POORLY in recent nodes —
   bitcell area is shrinking much more slowly than logic, which is
   why cache is consuming a growing share of die area and is a
   major driver of chiplet partitioning (§20)
⚠️ DRAM  one transistor + one capacitor. ⚠️ Must be REFRESHED
   because the capacitor leaks. ⚠️ Scaling is limited by the need
   to maintain capacitance in a shrinking footprint — hence deep
   trench and high-aspect-ratio capacitors
   ⚠️ Made on a SEPARATE, specialized process, not logic fabs
⚠️ NAND FLASH  ⚠️ charge trapped on a floating gate or in a charge
   trap. ⚠️ Scaled LATERALLY until it couldn't, then went VERTICAL
   — 3D NAND now stacks hundreds of layers. ⚠️ MLC/TLC/QLC store
   multiple bits per cell by distinguishing charge levels, trading
   density against endurance and retention
   ⚠️ WEAR-OUT IS INTRINSIC — the tunnel oxide degrades with
   program/erase cycles, which is why wear levelling exists
⚠️ HBM  ⚠️ DRAM dies STACKED and connected by through-silicon vias,
   placed adjacent to logic on an interposer. ⚠️ Enormous bandwidth
   via width rather than clock speed — and the central AI
   constraint (§27.2)
⚠️ EMERGING  MRAM, ReRAM, PCM, FeRAM — ⚠️ real products in niches,
   none has displaced the big three
```

---

# PART II — MAKING THE CHIP
