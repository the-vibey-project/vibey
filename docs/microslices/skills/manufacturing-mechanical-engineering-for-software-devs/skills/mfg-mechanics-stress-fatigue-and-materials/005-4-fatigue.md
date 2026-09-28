---
id: skill-4-fatigue-0774e72a3e
purpose: 4 fatigue
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-mechanics-stress-fatigue-and-materials/SKILL.md
requires: ["skill-3-failure-theories-and-safety-factors-28590d72c6"]
links: ["skill-5-materials-selection-26499488da"]
---

## §4. ⚠️ Fatigue

> **⚠️ The single most important failure mode, and the one software intuition has no
> analogue for.** ⚠️ **Components fail after many cycles at stresses FAR BELOW the static
> strength — sometimes below the yield point entirely.**
```
⚠️ S-N CURVE  stress amplitude vs cycles to failure
   ⚠️ Some steels show an ENDURANCE LIMIT — below it, effectively
   infinite life. ⚠️ ALUMINIUM DOES NOT. Aluminium accumulates
   damage at any stress amplitude, which is why aircraft have
   finite lives measured in cycles
⚠️ CRACK INITIATION then PROPAGATION then fast fracture
⚠️ MOST OF THE LIFE IS INITIATION, which is why SURFACE matters
   enormously — ⚠️ finish, scratches, tool marks, corrosion pits
   and stress concentrations (§2) all start cracks
⚠️ MEAN STRESS matters (Goodman/Gerber); ⚠️ COMPRESSIVE residual
   stress HELPS, which is why shot peening works
```
**⚠️ Related time-dependent failures**: ⚠️ **CREEP (slow deformation under sustained load at
high temperature — the limit on turbine blades), stress corrosion cracking, hydrogen
embrittlement, and fretting.**
**⚠️ The software translation, and it's genuinely useful**: ⚠️ **fatigue is the physical
analogue of a defect that only manifests after prolonged operation** — **memory
fragmentation, connection pool exhaustion, log disk filling, certificate expiry.**
**⚠️ Both are invisible in a short test, and both require thinking in CYCLES or TIME rather
than in single events.**

---
