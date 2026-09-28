---
id: skill-13-anti-patterns-21e072011a
purpose: 13 anti patterns
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-reference/SKILL.md
requires: []
links: ["skill-14-numbers-fb12d9e49e"]
---

## §13. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Choosing the tool before the representation | ⚠️ **Most CAD frustration is a representation mismatch** (§1 → `cad-geometry-kernels-formats-and-code-cad`) |
| Expecting arbitrary-edge fillets in OpenSCAD | ⚠️ **CSG has no edges to select** (§4.2 → `cad-geometry-kernels-formats-and-code-cad`) |
| Coplanar faces in a boolean | ⚠️ **Numerically ambiguous. Overlap by an epsilon** (§2 → `cad-geometry-kernels-formats-and-code-cad`) |
| STL as an interchange format between CAD tools | ⚠️ **Lossy and unit-less. Use STEP** (§3 → `cad-geometry-kernels-formats-and-code-cad`) |
| STL to the printer when 3MF is available | 3MF carries units, colour, settings (§3 → `cad-geometry-kernels-formats-and-code-cad`) |
| Assuming an STL's units | ⚠️ **There are none. 25.4× errors are real** (§3 → `cad-geometry-kernels-formats-and-code-cad`) |
| Round-tripping CAD → STL → CAD | You get an uneditable mesh back (§3 → `cad-geometry-kernels-formats-and-code-cad`) |
| High `$fn` / fine tessellation while iterating | ⚠️ **2 seconds becomes 2 minutes** (§4.3 → `cad-geometry-kernels-formats-and-code-cad`) |
| Magic numbers instead of named parameters | Defeats the point of code-CAD (§4.3 → `cad-geometry-kernels-formats-and-code-cad`) |
| Version-controlling the STL instead of the source | ⚠️ **Same** (§4.3 → `cad-geometry-kernels-formats-and-code-cad`) |
| Trusting automatic mesh repair blindly | ⚠️ **Heuristic; silently changes geometry** (§4.5 → `cad-geometry-kernels-formats-and-code-cad`) |
| Laplacian smoothing on a dimensioned part | ⚠️ **It shrinks the model** (§4.5 → `cad-geometry-kernels-formats-and-code-cad`) |
| Ignoring print orientation for structural parts | ⚠️ **Z is 20–50% weaker. Orientation is a design decision** (§6.1 → `cad-slicing-pipeline-and-processes`) |
| Horizontal circular holes on FDM | ⚠️ **Sagging top. Use a teardrop** (§7 → `cad-design-tolerances-and-materials`) |
| Wall thickness not a multiple of extrusion width | Gaps or over-extrusion (§7 → `cad-design-tolerances-and-materials`) |
| Fully enclosed voids in SLS or SLA | ⚠️ **Trapped powder / resin, permanently** (§6.2 → `cad-slicing-pipeline-and-processes`, §7 → `cad-design-tolerances-and-materials`) |
| Modelling holes at nominal size for FDM | ⚠️ **They print undersize** (§8 → `cad-design-tolerances-and-materials`) |
| Trusting a clearance table over a test print | Calibrate your machine and material (§8 → `cad-design-tolerances-and-materials`) |
| Printed threads for load-bearing joints | ⚠️ **Use heat-set inserts** (§8 → `cad-design-tolerances-and-materials`) |
| Printing hygroscopic filament without drying | ⚠️ **The most common invisible cause of bad prints** (§9 → `cad-design-tolerances-and-materials`) |
| Infill density as the strength lever | ⚠️ **Perimeters do more above ~40%** (§5.3 → `cad-slicing-pipeline-and-processes`) |
| Topology optimization on one load case | Fragile in every other direction (§10 → `cad-generative-automation-and-scanning`) |
| Manual slicing in a repeatable workflow | ⚠️ **Every slicer has a CLI** (§11 → `cad-generative-automation-and-scanning`) |
| Treating a scan as a model | ⚠️ **A mesh is not CAD** (§12 → `cad-generative-automation-and-scanning`) |

---
