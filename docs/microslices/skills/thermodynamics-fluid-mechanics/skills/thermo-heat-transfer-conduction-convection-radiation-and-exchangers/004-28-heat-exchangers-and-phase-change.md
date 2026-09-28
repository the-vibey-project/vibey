---
id: skill-28-heat-exchangers-and-phase-change-634e193424
purpose: 28 heat exchangers and phase change
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-heat-transfer-conduction-convection-radiation-and-exchangers/SKILL.md
requires: ["skill-27-radiation-f6ae1c492d"]
links: []
---

## §28. Heat Exchangers and Phase Change

```
⚠️ LMTD method     Q = UA·ΔT_lm·F     ⚠️ counterflow beats parallel flow
⚠️ ε-NTU method    for when outlet temperatures are unknown
FOULING            ⚠️ resistance grows in service; designers add a fouling
   factor, and fouling is the usual cause of degraded performance in practice
```
**⚠️ BOILING is the highest-flux mode available and it has a cliff:**
```
⚠️ THE BOILING CURVE — natural convection → NUCLEATE boiling (⚠️ excellent,
   where you want to operate) → CRITICAL HEAT FLUX → transition →
   FILM boiling
⚠️ CHF / BURNOUT   past the peak, a vapour blanket forms and the surface
   temperature JUMPS dramatically at the same heat flux. ⚠️ In a
   flux-controlled system this destroys the surface — the failure mode
   behind nuclear fuel cladding limits and power electronics burnout
```
**⚠️ The Leidenfrost effect is film boiling you can see** — **a droplet on a very hot plate
levitating on its own vapour, and taking LONGER to evaporate than on a cooler plate.**
**⚠️ Condensation**: **dropwise gives far higher coefficients than filmwise, and ⚠️ is hard
to sustain because surfaces revert to filmwise as they age.**
