---
id: skill-22-turbulence-294ce32103
purpose: 22 turbulence
source: src/vibey_tools/skills/plugins/thermodynamics-fluid-mechanics/skills/thermo-dimensional-analysis-flows-turbulence-and-turbomachinery/SKILL.md
requires: ["skill-21-external-flow-and-drag-ab5dfc5de8"]
links: ["skill-23-compressible-flow-e6a1406c98"]
---

## §22. ⚠️ Turbulence

**⚠️ "The last great unsolved problem of classical physics," and the honest framing is
that we have statistics rather than solutions.**
```
⚠️ CHARACTERISTICS  irregular, diffusive, rotational, dissipative, 3D,
   ⚠️ and a continuous range of scales
⚠️ ENERGY CASCADE   energy enters at large scales, transfers to smaller
   eddies, dissipates at the KOLMOGOROV SCALE η = (ν³/ε)^¼
⚠️ K41 SCALING      E(k) ∝ ε^(2/3)k^(−5/3) in the inertial subrange.
   ⚠️ Remarkably robust experimentally, with known intermittency corrections
⚠️ THE COST OF DNS  resolving all scales needs grid points ~Re^(9/4) and
   total work ~Re³. ⚠️ THIS is why DNS is infeasible for industrial
   Reynolds numbers and will remain so for decades (§29.1)
⚠️ CLOSURE PROBLEM  averaging Navier-Stokes creates the Reynolds stress
   term, which introduces more unknowns than equations. ⚠️ Every RANS
   model is a guess at closing it — and none is universal
```
**⚠️ Reynolds decomposition, the Boussinesq eddy-viscosity hypothesis** (⚠️ **which assumes
Reynolds stress aligns with mean strain rate — demonstrably false in flows with strong
curvature, rotation or separation, and it's the root of RANS's known failure modes**),
**and the model hierarchy: mixing length → k-ε → k-ω → SST → Reynolds stress models.**

---
