---
id: skill-24-design-flow-f1f08e3935
purpose: 24 design flow
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-pcb-assembly-reliability-design-flow-and-economics/SKILL.md
requires: ["skill-23-reliability-ddf00744e0"]
links: ["skill-25-economics-7d519aa5d1"]
---

## §24. Design Flow

**⚠️ Specification → RTL (Verilog/VHDL) → ⚠️ VERIFICATION (⚠️ typically the largest single
effort, and formal methods plus constrained-random simulation plus emulation) → logic
synthesis → floorplanning → place and route → clock tree synthesis → timing closure →
physical verification (DRC, LVS) → sign-off → tapeout.**
**⚠️ EDA is an effective oligopoly** — ⚠️ **Synopsys, Cadence and Siemens EDA — and the
tools are as much a chokepoint as the fab equipment** (§26).
**⚠️ IP reuse dominates**: ⚠️ **almost no one designs their own standard cells, memory
compilers, PHYs or CPU cores from scratch; Arm and RISC-V are the ISA options, and PDKs
come from the foundry.**
**⚠️ Timing closure and signoff** are where schedules die — ⚠️ **and the abstraction leaks
of §1 → `semi-carriers-doping-junctions-mosfet-and-scaling` all show up here as setup/hold violations, IR drop, crosstalk and thermal
hotspots.**

---
