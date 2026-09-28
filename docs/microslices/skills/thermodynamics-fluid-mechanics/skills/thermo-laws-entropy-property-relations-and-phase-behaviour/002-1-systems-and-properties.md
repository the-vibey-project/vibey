---
id: skill-1-systems-and-properties-3dcd1cfeaf
purpose: 1 systems and properties
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-laws-entropy-property-relations-and-phase-behaviour/SKILL.md
requires: ["skill-0-routing-ae8b7261d3"]
links: ["skill-2-the-zeroth-law-and-temperature-856a74221e"]
---

## §1. Systems and Properties

```
SYSTEM      ⚠️ what you draw the boundary around. CLOSED (no mass crossing),
            OPEN/control volume (mass crosses), ISOLATED (nothing crosses)
PROPERTY    ⚠️ INTENSIVE (independent of amount: T, P, ρ, v) vs
            EXTENSIVE (scales with amount: V, m, U, S)
STATE       ⚠️ fixed by a sufficient number of independent intensive
            properties. For a simple compressible substance, TWO
PROCESS     the path between states. ⚠️ Properties are path-independent;
            WORK AND HEAT ARE NOT
EQUILIBRIUM ⚠️ thermal, mechanical, chemical, phase — all required
```
> **⚠️ GOTCHA — heat and work are not properties, and this is the deepest bookkeeping point
> in the subject.** ⚠️ **A system does not "contain heat."** **It contains internal energy;
> heat and work are ENERGY IN TRANSIT across the boundary.** **⚠️ That's why we write
> δQ and δW (inexact differentials, path-dependent) but dU and dS (exact, state
> functions).** **Nearly every confused thermodynamics argument traces to treating heat as
> a stored quantity.**

**⚠️ Quasi-static vs real processes**: ⚠️ **the reversible idealization requires infinitely
slow change through equilibrium states — it never happens, and it's the benchmark
everything real is measured against** (§10 → `thermo-cycles-exergy-combustion-and-psychrometrics`).

---
