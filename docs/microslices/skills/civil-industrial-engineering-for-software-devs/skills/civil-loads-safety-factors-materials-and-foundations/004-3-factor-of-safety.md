---
id: skill-3-factor-of-safety-40821c80fa
purpose: 3 factor of safety
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-loads-safety-factors-materials-and-foundations/SKILL.md
requires: ["skill-2-loads-and-structure-67d50f0643"]
links: ["skill-4-materials-7f5a409273"]
---

## §3. ⚠️ Factor of Safety

**⚠️ The idea software people cite most and understand least.**
```
⚠️ FoS = capacity / demand.  Typically ~1.5–2.0 for structures, higher
   where consequences are severe or knowledge is poor
⚠️ IT COVERS IGNORANCE, NOT SLOPPINESS: material variability, workmanship
   tolerance, load uncertainty, model error, degradation over time
⚠️ MODERN PRACTICE has largely moved to LIMIT STATE / LRFD design —
   separate partial factors applied to LOADS and to RESISTANCES,
   calibrated probabilistically, rather than one global fudge factor
```
> **⚠️ GOTCHA — a factor of safety is not "build it twice as strong to be safe," and it is
> not a margin for bad work.** ⚠️ **It's a calibrated allowance for QUANTIFIED
> uncertainty in materials, loads and models.** **⚠️ The reason software can't simply adopt
> it is that software has no equivalent of a characteristic material strength — there is
> no distribution of "code strength" to apply a partial factor to.**
> **⚠️ What software CAN adopt is the underlying logic: identify the specific
> uncertainties, size the margin to each one, and state it.** **Capacity headroom, error
> budgets and rate limits are the real analogues** (§21 → `civil-reliability-safety-and-what-transfers-to-software`).

**⚠️ Redundancy vs margin is a genuine distinction**: ⚠️ **a factor of safety makes one
element stronger; redundancy provides an alternative path when one fails.**
**⚠️ Structural robustness — resistance to DISPROPORTIONATE collapse — is the redundancy
concept, and it entered codes largely because of Ronan Point** (§8 → `civil-codes-licensure-failure-analysis-and-construction`).

---
