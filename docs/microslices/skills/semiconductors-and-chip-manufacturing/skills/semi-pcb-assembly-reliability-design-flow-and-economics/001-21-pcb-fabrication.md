---
id: skill-21-pcb-fabrication-1cdd35302b
purpose: 21 pcb fabrication
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-pcb-assembly-reliability-design-flow-and-economics/SKILL.md
requires: []
links: ["skill-22-assembly-and-soldering-3f84242c57"]
---

## §21. PCB Fabrication

**⚠️ The other half of "chip and motherboard," and it is a genuinely different industry.**
```
⚠️ THE STACK-UP  copper foil, ⚠️ PREPREG (resin-impregnated glass
   cloth) and cores, laminated under heat and pressure.
   ⚠️ FR-4 is the workhorse; ⚠️ high-speed designs need low-loss
   materials (Megtron, Rogers) because FR-4's loss tangent
   destroys multi-GHz signals
⚠️ THE FLOW  inner layers imaged and etched → lamination →
   ⚠️ DRILLING (mechanical, and LASER for microvias) → desmear →
   ⚠️ ELECTROLESS COPPER to make the hole walls conductive →
   electroplating → outer layer image and etch → solder mask →
   surface finish (ENIG, OSP, HASL) → profiling → electrical test
⚠️ HDI  ⚠️ microvias, blind and buried vias, sequential lamination —
   ⚠️ needed once BGA pitch drops below what through-holes can escape
⚠️ THE DESIGN CONSTRAINTS THAT BITE  ⚠️ CONTROLLED IMPEDANCE (see an
   electromagnetism reference — trace geometry and dielectric set
   Z₀) · ⚠️ RETURN PATH CONTINUITY · via stubs and backdrilling ·
   ⚠️ layer count vs cost · aspect ratio limits on drilling
⚠️ IPC standards govern classes, acceptability and design
```
**⚠️ The substrate for a chip package is a PCB-like product built to far finer rules** —
⚠️ **and ABF substrate capacity has been a real constraint on advanced packaging** (§20 → `semi-integration-yield-metrology-test-and-packaging`).

---
