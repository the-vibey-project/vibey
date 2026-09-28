---
id: skill-11-radiation-environments-and-shielding-36c93afb91
purpose: 11 radiation environments and shielding
source: src/vibey_tools/skills/plugins/space-exploration/skills/space-human-factors-life-support-and-reliability/SKILL.md
requires: ["skill-10-life-support-and-isru-31aaac84dd"]
links: ["skill-12-instrumentation-806bb6e354"]
---

## §11. Radiation Environments and Shielding

**Environments**: **trapped belts** (Van Allen — ⚠️ **Jupiter's are the harshest in the
solar system, and Europa missions must design around a total-dose budget that dominates
the spacecraft**), **GCR**, **SPE**, and **secondary neutrons** from shielding itself.

**Effects on hardware**: **TID** (total ionizing dose, cumulative degradation),
**SEE** — ⚠️ **single-event upsets (bit flips, correctable), latchup (potentially
destructive), and burnout** — and **displacement damage** in detectors and solar cells.

**Mitigation**: **rad-hard parts** (⚠️ **often generations behind commercial silicon,
because qualification takes years — which is why flight computers look antique**),
**shielding**, **EDAC and scrubbing** of memory, **watchdogs**, and **redundancy with
voting**.

> **⚠️ GOTCHA — shielding against GCR is not a matter of adding aluminium.**
> High-energy heavy ions produce **secondary particle showers** in dense material, and
> **modest shielding can increase dose rather than reduce it.** **Hydrogen-rich materials
> (polyethylene, water, and — usefully — the crew's own consumables and waste) are far
> more effective per unit mass** because hydrogen fragments heavy ions without producing
> heavy secondaries. **This is why "just add shielding" is not an answer to §9.1**, and
> why active magnetic shielding keeps being proposed despite its own severe problems.

---
