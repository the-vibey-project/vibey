---
id: skill-4-materials-7f5a409273
purpose: 4 materials
source: src/vibey_tools/skills/plugins/civil-industrial-engineering-for-software-devs/skills/civil-loads-safety-factors-materials-and-foundations/SKILL.md
requires: ["skill-3-factor-of-safety-40821c80fa"]
links: ["skill-5-foundations-and-soil-40f065b793"]
---

## §4. Materials

```
STEEL      ⚠️ strong in tension AND compression, DUCTILE (⚠️ it yields
   visibly before failing — a warning), predictable, corrodes, loses
   strength in fire
CONCRETE   ⚠️ strong in compression, WEAK in tension, BRITTLE, cheap,
   durable. ⚠️ Reinforced concrete puts steel where the tension is —
   which is the single most important composite idea in construction
TIMBER     ⚠️ anisotropic (properties depend on grain direction), renewable;
   mass timber (CLT) is the modern engineered form
SOIL       ⚠️ the most variable "material" and rarely fully characterized (§5)
```
**⚠️ Properties that matter**: **strength, stiffness (⚠️ Young's modulus — a stiff
structure and a strong one are different things, and serviceability failures are stiffness
failures), ductility, toughness, fatigue resistance, creep.**
> **⚠️ GOTCHA — DUCTILE vs BRITTLE failure is the concept most worth stealing.**
> ⚠️ **Ductile materials deform visibly and progressively before failing, giving warning
> and time to evacuate; brittle materials fail suddenly and completely.** **Seismic design
> deliberately engineers ductility so buildings bend rather than shatter.**
> **⚠️ The software translation is exact and underused: design systems to DEGRADE
> GRACEFULLY rather than fail suddenly.** **Load shedding, backpressure, circuit breakers
> and feature degradation are ductility. A system that runs perfectly until it falls over
> completely is brittle.**

---
