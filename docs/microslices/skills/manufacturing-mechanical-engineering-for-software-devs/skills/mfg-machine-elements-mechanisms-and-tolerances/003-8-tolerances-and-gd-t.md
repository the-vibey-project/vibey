---
id: skill-8-tolerances-and-gd-t-8f6da48d18
purpose: 8 tolerances and gd t
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-machine-elements-mechanisms-and-tolerances/SKILL.md
requires: ["skill-7-mechanisms-and-kinematics-f0bafc02d5"]
links: []
---

## §8. ⚠️ Tolerances and GD&T

> **⚠️ THE conceptual shift for software people. In the physical world there is no
> equality — only distributions.** ⚠️ **A "10 mm" hole is never 10 mm; it is 10 mm ± something,
> and the design must work across the whole range.**
```
⚠️ TOLERANCE  the permitted variation. ⚠️ TIGHTER TOLERANCE COSTS
   MORE, often NON-LINEARLY — halving a tolerance can multiply cost
   several-fold by forcing a different process (§9) or added
   inspection. ⚠️ Over-tolerancing is the most common and most
   expensive novice error in mechanical design
⚠️ FITS  clearance · transition · interference (⚠️ press fits, where
   the parts are deliberately the "wrong" size)
⚠️ STACK-UP  ⚠️ tolerances ACCUMULATE across an assembly
   ⚠️ WORST CASE  sum of all tolerances — safe, expensive, and
      astronomically unlikely
   ⚠️ STATISTICAL (RSS)  root-sum-square — realistic, and it
      ASSUMES independence and centred distributions, which
      real processes often violate
⚠️ GD&T (ASME Y14.5 / ISO GPS)  ⚠️ specifies FUNCTION rather than
   just dimensions: form (flatness, straightness), orientation
   (perpendicularity, angularity), location (⚠️ TRUE POSITION),
   and runout — all relative to explicitly declared DATUMS
⚠️ MMC / BONUS TOLERANCE  ⚠️ as a feature departs from maximum
   material condition, extra positional tolerance becomes
   available — because the ASSEMBLY still works. This is
   tolerancing the FUNCTION, not the number
```
**⚠️ Why GD&T exists at all**: ⚠️ **plus/minus dimensioning is ambiguous about what matters
and creates square tolerance zones where the function wants round ones.** **⚠️ GD&T states
the design intent unambiguously, which is exactly what a specification should do.**
**⚠️ DATUMS are the key idea**: ⚠️ **they define how the part is referenced and therefore how
it is measured and fixtured — and inconsistent datums between design, manufacture and
inspection is a recurring source of parts that "measure fine" and don't fit.**

---

# PART II — MAKING THINGS
