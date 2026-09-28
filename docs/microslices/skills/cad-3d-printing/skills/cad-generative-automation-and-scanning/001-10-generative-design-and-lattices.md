---
id: skill-10-generative-design-and-lattices-e6c3d068a1
purpose: 10 generative design and lattices
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-generative-automation-and-scanning/SKILL.md
requires: []
links: ["skill-11-automation-pipelines-465dce7a9b"]
---

## §10. Generative Design and Lattices

**Topology optimization**: ⚠️ **SIMP (Solid Isotropic Material with Penalization) is the
standard method** — treat density as a continuous field per element, penalize intermediate
values, and iterate an FEA to minimize compliance under a mass constraint. **Level-set
methods** are the main alternative. **Output is organic-looking and typically needs
smoothing and interpretation before manufacture.**

**Lattices**: **strut-based (BCC, FCC, octet)** and **TPMS (gyroid, Schwarz)** —
⚠️ **TPMS are defined implicitly, self-supporting, and have no sharp junctions, which is
why they dominate in AM.** Applications: lightweighting, energy absorption, heat exchange,
and **osseointegration in medical implants.**

**⚠️ Implicit modelling is the natural representation here** (§1 → `cad-geometry-kernels-formats-and-code-cad`), because a lattice with
millions of struts is intractable as B-rep and enormous as a mesh, **but trivial as a
function you evaluate at the point of slicing.** **nTop is the prominent commercial tool;
open equivalents are improving.**

**⚠️ The honest caveat**: generative results are only as good as the load cases you
specified. **A part optimized for a single load case is often fragile in every other
direction**, and manufacturability constraints must be in the optimization, not applied
afterward.

---
