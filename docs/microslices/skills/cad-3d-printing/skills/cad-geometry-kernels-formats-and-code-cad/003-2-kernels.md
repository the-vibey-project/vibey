---
id: skill-2-kernels-12a8cd9ef7
purpose: 2 kernels
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-geometry-kernels-formats-and-code-cad/SKILL.md
requires: ["skill-1-geometry-representations-5ccb3c3ff3"]
links: ["skill-3-file-formats-and-what-each-one-loses-5c85d515ca"]
---

## §2. Kernels

| Kernel | Type | Used by | ⚠️ Notes |
|---|---|---|---|
| **OCCT (Open CASCADE)** | B-rep | FreeCAD, CadQuery, build123d | ⚠️ **>1M lines of C++; the open B-rep kernel. Steep, and failures are surprising** |
| **Parasolid** | B-rep | SolidWorks, NX, Onshape | Commercial, robust |
| **ACIS** | B-rep | AutoCAD, others | Commercial |
| **CGAL** | Exact-arithmetic geometry | OpenSCAD (historically), research | ⚠️ **Exact and correct, and slow** |
| **Manifold** | Mesh booleans | OpenSCAD (modern), others | ⚠️ **Fast, guarantees manifold output** (§16.1 → `cad-reference`) |
| **libigl / Open3D / VTK / trimesh** | Mesh processing | Research, pipelines | §4.5 |
| **OpenVDB** | Sparse voxel/level set | VFX, implicit modelling | Excellent for offsets and thickening |

**⚠️ The exact-vs-floating-point trade is the core engineering problem in geometry
kernels.** Exact arithmetic (CGAL) gives provably correct results and is slow; floating
point is fast and produces **robustness failures — coincident faces, near-degenerate
triangles, and booleans that fail on geometry that "should" work.**

**⚠️ Which is why coplanar faces are the classic CSG failure**: subtracting a box whose face
sits exactly on another face is numerically ambiguous. **The universal workaround is to
overlap by a small epsilon** — `0.01 mm` or so — and it appears in every OpenSCAD codebase
for exactly this reason.

---
