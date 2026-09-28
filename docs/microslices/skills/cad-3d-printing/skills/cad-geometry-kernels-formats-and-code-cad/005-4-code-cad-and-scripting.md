---
id: skill-4-code-cad-and-scripting-a3254bd0fb
purpose: 4 code cad and scripting
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-geometry-kernels-formats-and-code-cad/SKILL.md
requires: ["skill-3-file-formats-and-what-each-one-loses-5c85d515ca"]
links: []
---

## §4. Code-CAD and Scripting

### 4.1 The landscape

| Tool | Language | Kernel | ⚠️ Character |
|---|---|---|---|
| **OpenSCAD** | Own C-like DSL | CGAL / Manifold | ⚠️ **CSG-first, declarative, no fillets on arbitrary edges. Simple and predictable** |
| **CadQuery** | Python | OCCT | ⚠️ **Fluent/method-chaining API; exports STEP** |
| **build123d** | Python | OCCT | ⚠️ **Successor-in-spirit to CadQuery; context managers instead of chaining, so full Python control flow works naturally** |
| **FreeCAD scripting** | Python | OCCT | Full application automation |
| **JSCAD** | JavaScript | own | Browser-native |
| **Grasshopper** | Visual + C#/Python | Rhino | ⚠️ **Dominant in architecture and computational design** |
| **Fusion/SolidWorks/Onshape APIs** | Python / VBA / JS | vendor | Automating a commercial tool |
| **Blender (bpy)** | Python | mesh | ⚠️ **Mesh/organic modelling, not engineering CAD** |

### 4.2 ⚠️ OpenSCAD vs the OCCT-based tools — the real trade

**⚠️ OpenSCAD's language is functional and declarative, and this surprises people**:
variables are **set at compile time, not assignment** — ⚠️ **assigning twice in the same
scope does not do what an imperative programmer expects; the last value wins for the whole
scope.** There are no loops with mutation; you use recursion and list comprehensions.

**The kernel difference is the substantive one:**
- **OpenSCAD is mesh/CSG**: ⚠️ **it cannot fillet an arbitrary edge, because it has no
  concept of an edge — only the boolean result.** You design fillets in by construction
  (`minkowski`, `hull`, or explicit geometry).
- **CadQuery/build123d are B-rep on OCCT**: ⚠️ **exact curved surfaces, and `fillet()` and
  `chamfer()` on selected edges — plus STEP export, which OpenSCAD cannot do.**

**⚠️ The honest counterweight**: OCCT's complexity leaks through the Python wrapper.
**Operations that look simple — "fillet this edge" — fail in surprising ways depending on
surrounding geometry**, and diagnosing that requires understanding the kernel. **OpenSCAD
fails more predictably.**

### 4.3 Writing good parametric models
```
⚠️ Parameterize intent, not dimensions:  wall_thickness, clearance, screw_size
   — not magic numbers scattered through the file
Named constants at the top; derive everything else
⚠️ Build a library of your own fasteners, clearances, and joints — reuse compounds
Assertions on parameters (⚠️ OpenSCAD's assert(); Python's naturally)
⚠️ $fn / tessellation: coarse while iterating, fine only for final export —
   this is usually the difference between 2 seconds and 2 minutes
Version-control the source, not the STL     ⚠️ this is the whole point of code-CAD
```
**⚠️ The genuine advantage of code-CAD over GUI CAD**: **diffable, reviewable,
version-controlled, and generatable.** A single script produces a family of parts. **You
can put it in CI.**

**⚠️ The genuine disadvantage**: **spatial reasoning in text is hard**, iteration is
slower than direct manipulation for organic shapes, and **there is no constraint solver** —
if you want "this face always tangent to that cylinder," you compute it yourself.

### 4.4 Vendor API automation
**Fusion (Python/C++), SolidWorks (VBA/C#), Onshape (REST + FeatureScript), NX, CATIA.**
⚠️ **Onshape is architecturally the outlier — a genuine REST API over a cloud document
model, which makes it the easiest commercial CAD to automate against** and the only one
where "CAD in CI" is straightforward.

**Common automation tasks**: batch parameter sweeps and export, drawing generation, BOM
extraction, design-rule checking, and **PLM integration.**

### 4.5 Mesh processing and repair
**⚠️ The properties that determine whether a mesh is printable:**
```
Manifold      ⚠️ every edge shared by exactly 2 faces
Watertight    closed, no holes — encloses a definite volume
Orientable    consistent normals (outward)
Non-self-intersecting   ⚠️ the one that repair tools handle worst
```
**⚠️ The Euler characteristic `V − E + F = 2 − 2g` is a fast sanity check** — for a closed
surface of genus `g`. A result that isn't an even integer means the mesh is broken.

**Common defects**: holes, non-manifold edges (⚠️ **3+ faces on one edge**), non-manifold
vertices (two shells touching at a point), flipped normals, duplicate/degenerate faces,
self-intersection, **and internal geometry left inside a solid** (⚠️ **invisible, and it
confuses slicers**).

**Repair**: **Meshmixer** (legacy but effective), **Netfabb**, **Blender 3D-Print
Toolbox**, **MeshLab**, **trimesh** and **pymeshlab** in Python, **Manifold** for
guaranteed-valid booleans. ⚠️ **Automatic repair is heuristic and can silently change your
geometry — inspect the result.**

**Algorithms worth knowing**: **marching cubes** (implicit → mesh), **Poisson surface
reconstruction** (points → mesh), **quadric edge-collapse decimation** (⚠️ **the standard
simplification method**), **Laplacian smoothing** (⚠️ **shrinks the model — use
taubin smoothing if that matters**), **voxel remeshing** (⚠️ **the nuclear option for
repair: voxelize and re-surface. Guarantees manifold output, destroys sharp features**).
