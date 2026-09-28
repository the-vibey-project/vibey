---
id: skill-17-quick-reference-03d1680271
purpose: 17 quick reference
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-reference/SKILL.md
requires: ["skill-16-what-actually-moved-verified-august-2026-65fb148eab"]
links: ["skill-18-method-4bd06f0dfe"]
---

## §17. Quick Reference

### 17.1 Picker
| Need | Use |
|---|---|
| Parametric part, simple geometry, scriptable | **OpenSCAD** (§4.1 → `cad-geometry-kernels-formats-and-code-cad`) |
| Same, but needs fillets/chamfers and STEP | ⚠️ **CadQuery or build123d** (§4.2 → `cad-geometry-kernels-formats-and-code-cad`) |
| Full CAD app automation | **FreeCAD Python**, or **Onshape REST** (§4.4 → `cad-geometry-kernels-formats-and-code-cad`) |
| Constraint-based parametric, lightweight GUI | **SolveSpace** (§15) |
| Organic/artistic modelling | Blender (⚠️ not engineering CAD) (§4.1 → `cad-geometry-kernels-formats-and-code-cad`) |
| Lattices, implicit geometry, millions of features | ⚠️ **Implicit/SDF representation** (§1 → `cad-geometry-kernels-formats-and-code-cad`, §10 → `cad-generative-automation-and-scanning`) |
| Reliable booleans on messy meshes | **Manifold** (§2 → `cad-geometry-kernels-formats-and-code-cad`) |
| Repair a broken mesh | trimesh / pymeshlab / Netfabb; ⚠️ **voxel remesh as last resort** (§4.5 → `cad-geometry-kernels-formats-and-code-cad`) |
| CAD → CAD interchange | ⚠️ **STEP** (§3 → `cad-geometry-kernels-formats-and-code-cad`) |
| CAD → printer | ⚠️ **3MF** (§3 → `cad-geometry-kernels-formats-and-code-cad`) |
| Batch/CI generation | ⚠️ **Headless CLI — all of them have one** (§11 → `cad-generative-automation-and-scanning`) |
| Klipper printer | **OrcaSlicer** (§16.2) |
| Strong part, FDM | ⚠️ **Orient for load along layers; add perimeters, not infill** (§5.3 → `cad-slicing-pipeline-and-processes`, §6.1 → `cad-slicing-pipeline-and-processes`) |
| Load-bearing threaded joint, FDM | **Heat-set insert** (§8 → `cad-design-tolerances-and-materials`) |
| Complex geometry, no supports | ⚠️ **SLS/MJF — the powder bed supports it** (§6 → `cad-slicing-pipeline-and-processes`) |
| Fine detail | SLA/MSLA (§6 → `cad-slicing-pipeline-and-processes`) |

### 17.2 Pre-print checklist
- [ ] Mesh manifold, watertight, correct normals? (§4.5 → `cad-geometry-kernels-formats-and-code-cad`)
- [ ] Units correct — and is it 3MF rather than STL? (§3 → `cad-geometry-kernels-formats-and-code-cad`)
- [ ] Oriented for the load path, not just for print time? (§6.1 → `cad-slicing-pipeline-and-processes`)
- [ ] Overhangs under ~45°, or supported, or redesigned as chamfers? (§7 → `cad-design-tolerances-and-materials`)
- [ ] Horizontal holes teardropped? (§7 → `cad-design-tolerances-and-materials`)
- [ ] Walls a whole multiple of extrusion width? (§7 → `cad-design-tolerances-and-materials`)
- [ ] Clearances calibrated for *this* machine and material? (§8 → `cad-design-tolerances-and-materials`)
- [ ] Escape holes for powder/resin if applicable? (§6.2 → `cad-slicing-pipeline-and-processes`)
- [ ] Filament dried if hygroscopic? (§9 → `cad-design-tolerances-and-materials`)
- [ ] Perimeters increased before infill for strength? (§5.3 → `cad-slicing-pipeline-and-processes`)

---
