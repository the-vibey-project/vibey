---
id: skill-2-stress-strain-and-deflection-461c8cf06e
purpose: 2 stress strain and deflection
source: src/vibey_tools/skills/plugins/manufacturing-mechanical-engineering-for-software-devs/skills/mfg-mechanics-stress-fatigue-and-materials/SKILL.md
requires: ["skill-1-what-mechanical-engineers-actually-do-518a698d4d"]
links: ["skill-3-failure-theories-and-safety-factors-28590d72c6"]
---

## §2. Stress, Strain and Deflection

```
⚠️ STRESS σ = F/A (Pa) — ⚠️ INTENSITY of load, not load
⚠️ STRAIN ε = ΔL/L — dimensionless deformation
⚠️ YOUNG'S MODULUS E = σ/ε — ⚠️ STIFFNESS, and it is NOT strength.
   ⚠️ Steel and stainless have nearly the same E; their strengths
   differ enormously. Confusing the two is the classic beginner error
⚠️ POISSON'S RATIO — lateral contraction under axial load
⚠️ YIELD strength (permanent deformation begins) vs ULTIMATE (fracture)
⚠️ MODES  tension · compression · shear · bending · torsion ·
   ⚠️ BUCKLING (a STABILITY failure — a slender column fails long
   before it crushes, and the load depends on LENGTH SQUARED)
```
**⚠️ Stress concentration is the practical one**: ⚠️ **holes, notches, sharp internal corners
and abrupt section changes multiply local stress by a factor Kt, often 2–3×.**
**⚠️ This is why fillets exist, and why a sharp internal corner is a crack waiting to
start** (§4). **⚠️ "Add a radius" is one of the most common review comments in mechanical
design.**
**⚠️ Deflection often governs before strength** — ⚠️ **a beam that is strong enough may
still bend too much to work, and stiffness scales differently from strength (for a beam,
with the CUBE of depth), which is why I-beams and ribs exist.**

---
