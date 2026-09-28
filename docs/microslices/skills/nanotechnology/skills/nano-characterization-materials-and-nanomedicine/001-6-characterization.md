---
id: skill-6-characterization-7661f2935c
purpose: 6 characterization
source: src/vibey_tools/skills/plugins/nanotechnology/skills/nano-characterization-materials-and-nanomedicine/SKILL.md
requires: []
links: ["skill-7-nanomaterials-7a28b3b587"]
---

## §6. Characterization

**⚠️ The fundamental constraint: you cannot see a nanostructure with light.** Abbe's limit
is `d = λ/(2·NA)` ≈ 200 nm for visible. **Everything below uses electrons, physical probes,
or clever tricks.**

| Method | Resolution | What it gives | ⚠️ Limitation |
|---|---|---|---|
| **SEM** | ~1 nm | Surface topography | ⚠️ **Needs conductive coating; vacuum** |
| **TEM** | ⚠️ **<0.1 nm** | Internal structure, lattice | ⚠️ **Sample must be <100 nm thin — destructive prep** |
| **STEM-EDS/EELS** | atomic | Composition mapped to structure | Beam damage |
| **AFM** | ~0.1 nm vertical | Topography, force, mechanics | ⚠️ **Tip convolution broadens lateral features** |
| **STM** | atomic | Electronic structure | ⚠️ **Conductive samples only** |
| **XRD** | — | Crystal structure, ⚠️ **Scherrer for size** | Needs crystallinity |
| **XPS** | — | ⚠️ **Surface composition and oxidation state, top ~10 nm** | Surface only |
| **DLS** | — | Hydrodynamic size in suspension | ⚠️ **Intensity-weighted — biased toward large particles** |
| **Raman** | ~1 µm | Bonding; ⚠️ **graphene layer count from 2D peak** | Weak signal |
| **Super-resolution optical** (STED, PALM/STORM) | 20–50 nm | ⚠️ **Optical, in living cells** | Needs fluorophores |

**⚠️ Metrology is a genuine bottleneck in manufacturing**, not just a lab concern: you must
measure critical dimensions on billions of features nondestructively and fast. **Optical
scatterometry plus modelling is what's actually used inline** — ⚠️ **which is an inverse
problem, and therefore a computational one.**

**⚠️ The characterization rule**: no single technique is sufficient. **DLS says 50 nm, TEM
says 30 nm — and both are right**, because DLS measures the hydrodynamic diameter including
the solvation shell and ligands, and weights by intensity (`∝ r⁶`). **Report the method
with the number.**

---
