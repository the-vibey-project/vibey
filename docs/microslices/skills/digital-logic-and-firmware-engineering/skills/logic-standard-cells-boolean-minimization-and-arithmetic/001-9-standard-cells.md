---
id: skill-9-standard-cells-f81981cf41
purpose: 9 standard cells
source: src/vibey_tools/skills/plugins/digital-logic-and-firmware-engineering/skills/logic-standard-cells-boolean-minimization-and-arithmetic/SKILL.md
requires: []
links: ["skill-10-boolean-algebra-c97637a5eb"]
---

## §9. Standard Cells

**⚠️ The abstraction that makes digital design tractable**: ⚠️ **a library of pre-designed,
pre-characterized gates with a fixed height so they tile into rows.**
**⚠️ What a library contains**: ⚠️ **combinational gates in multiple drive strengths,
flip-flops and latches, buffers and clock cells, level shifters, isolation cells,
fill and decap cells, and I/O cells.**
**⚠️ CHARACTERIZATION** is the valuable part: ⚠️ **timing (delay as a function of input
slew and output load), power, and noise — captured in Liberty files and used by every
downstream tool.**
**⚠️ Cell height in "tracks"** trades density against speed, ⚠️ **which is why a library
comes in tall-cell and short-cell variants for the same process.**
**⚠️ The design flow uses these as atoms** (see a microarchitecture reference §24) —
⚠️ **synthesis maps RTL onto library cells, and place-and-route arranges them.**

---

# PART III — LOGIC DESIGN
