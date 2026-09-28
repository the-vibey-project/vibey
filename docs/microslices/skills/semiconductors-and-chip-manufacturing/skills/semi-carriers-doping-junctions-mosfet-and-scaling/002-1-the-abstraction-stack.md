---
id: skill-1-the-abstraction-stack-85e546c595
purpose: 1 the abstraction stack
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-carriers-doping-junctions-mosfet-and-scaling/SKILL.md
requires: ["skill-0-routing-b06595423a"]
links: ["skill-2-carriers-doping-and-silicon-aac4d413b4"]
---

## §1. The Abstraction Stack

```
⚠️ Application → OS → ISA → microarchitecture → RTL → logic gates →
   ⚠️ STANDARD CELLS → transistors → ⚠️ DEVICE PHYSICS → materials
⚠️ EVERY LAYER IS A LEAKY ABSTRACTION AND THE LEAKS ARE THE
   INTERESTING PART — timing, power, thermals, variability and
   reliability all propagate upward from physics
⚠️ THE PARALLEL SUPPLY CHAIN
   design (fabless) → IP and EDA → mask making → ⚠️ FAB →
   ⚠️ TEST → ⚠️ PACKAGING (OSAT) → board assembly → system
⚠️ Each of these is a distinct industry with distinct economics,
   and ⚠️ several have effective monopolies (§26)
```
**⚠️ The scale that makes it hard**: ⚠️ **a modern fab prints features far smaller than the
wavelength of the light used to print them (§11 → `semi-cleanroom-lithography-deposition-etch-and-cmp`), across 300 mm wafers, with defect
densities low enough that a die with billions of transistors works at all.**

---

# PART I — DEVICE PHYSICS
