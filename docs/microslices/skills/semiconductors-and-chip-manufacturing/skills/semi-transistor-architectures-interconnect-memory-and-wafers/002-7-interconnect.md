---
id: skill-7-interconnect-4968b8a435
purpose: 7 interconnect
source: src/vibey_tools/skills/plugins/semiconductors-and-chip-manufacturing/skills/semi-transistor-architectures-interconnect-memory-and-wafers/SKILL.md
requires: ["skill-6-transistor-architectures-a07aa81560"]
links: ["skill-8-memory-d71cdea313"]
---

## §7. Interconnect

**⚠️ The wires became the problem.** ⚠️ **Transistors got faster as they shrank; wires got
SLOWER, because resistance rises as cross-section falls while capacitance doesn't fall
proportionally.**
```
⚠️ RC DELAY now dominates at the leading edge, and ⚠️ a large
   fraction of chip power goes into charging and discharging
   interconnect capacitance rather than into switching devices
⚠️ THE MATERIALS RESPONSE  ⚠️ aluminium → COPPER (lower resistivity,
   requiring the DAMASCENE process because copper is hard to etch,
   §13) · ⚠️ LOW-k DIELECTRICS to cut capacitance (⚠️ and they are
   mechanically weak and porous, which causes real integration
   problems)
⚠️ BARRIER LAYERS  ⚠️ copper poisons silicon, so it must be fully
   encapsulated — and the barrier takes an increasing fraction of
   the shrinking wire cross-section, which is a fundamental squeeze
⚠️ ⚠️ ELECTROMIGRATION  ⚠️ momentum transfer from electrons physically
   moves metal atoms, causing voids and eventual open circuits.
   ⚠️ Sets a hard CURRENT DENSITY limit, and it is a wear-out
   mechanism, not a defect (§23)
⚠️ ALTERNATIVES  cobalt and ruthenium for the finest lines;
   ⚠️ and optical interconnect for chip-to-chip (§27.2's CPO)
```

---
