---
id: skill-7-design-for-additive-manufacturing-2a4a5d36f5
purpose: 7 design for additive manufacturing
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-design-tolerances-and-materials/SKILL.md
requires: []
links: ["skill-8-tolerances-and-fits-4f36ab2e4d"]
---

## §7. Design for Additive Manufacturing

**⚠️ The constraint list, and each one has a physical reason:**
- **Overhangs** — ⚠️ **45° is the classic threshold for FDM**, and it comes from each layer
  needing roughly half its width supported by the one below. **Design chamfers instead of
  overhangs where you can.**
- **Bridges** — flat over a gap beats an unsupported curve.
- **⚠️ Hole shape**: horizontal circular holes print with a sagging top.
  **A teardrop or diamond profile prints cleanly without support** — a genuinely useful
  trick.
- **Minimum wall thickness** — ⚠️ **relate it to nozzle width**: a wall should be a whole
  multiple of extrusion width (e.g. 0.8 mm or 1.2 mm for a 0.4 mm nozzle), or the slicer
  leaves a gap or over-extrudes to fill it.
- **⚠️ First layer and elephant's foot** — chamfer the bottom edge by 0.5 mm.
- **Orientation** — §6.1 → `cad-slicing-pipeline-and-processes`. **Strength, surface finish, support requirement and print time
  are all decided by it, and they conflict.**
- **⚠️ Escape holes** for SLA resin and SLS powder (§6.2 → `cad-slicing-pipeline-and-processes`).
- **Print-in-place mechanisms** — ⚠️ **need a clearance of roughly 0.3–0.5 mm on FDM to
  avoid fusing.**
- **Consolidate assemblies** — the classic AM win, ⚠️ **but check you can still service it.**

---
