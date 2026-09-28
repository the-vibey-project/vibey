---
id: skill-12-scanning-and-reverse-engineering-f28d9d6700
purpose: 12 scanning and reverse engineering
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-generative-automation-and-scanning/SKILL.md
requires: ["skill-11-automation-pipelines-465dce7a9b"]
links: []
---

## §12. Scanning and Reverse Engineering

**Methods**: structured light, laser triangulation, photogrammetry
(⚠️ **cheap — a phone and COLMAP/Meshroom**), CT (⚠️ **captures internal geometry, and
it's the only method that does**), contact probing (CMM).

**Pipeline**: capture → align/register (⚠️ **ICP — iterative closest point**) → merge →
reconstruct surface (Poisson) → clean → **and then the hard part: convert to CAD.**
**⚠️ A scan gives you a mesh, not a model.** Getting a parametric, editable solid means
fitting primitives and surfaces to the scan — semi-automatic at best, and **the actual
work in reverse engineering.**
