---
id: skill-1-geometry-representations-5ccb3c3ff3
purpose: 1 geometry representations
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-geometry-kernels-formats-and-code-cad/SKILL.md
requires: ["skill-0-routing-8fb9182b3c"]
links: ["skill-2-kernels-12a8cd9ef7"]
---

## §1. Geometry Representations

**⚠️ This is the decision everything else follows from.**

| Representation | Stores | Good at | ⚠️ Bad at |
|---|---|---|---|
| **B-rep** | Faces, edges, vertices; each face an exact surface | ⚠️ **Exact curves, fillets, chamfers, STEP interchange, machining** | Organic shapes; robustness of booleans |
| **CSG** | A tree of primitives + boolean ops | ⚠️ **Parametric intent, compact, always "valid"** | Fillets on arbitrary edges; export fidelity |
| **Mesh (B-rep's poor cousin)** | Triangles | Rendering, printing, scanning, simulation | ⚠️ **Approximation only; no exact curves; repair burden** |
| **Implicit / SDF** | A function `f(x,y,z)` | ⚠️ **Booleans are trivial and always valid; lattices, blends, infinite detail** | Exact dimensions, sharp features, CAD interchange |
| **Voxel** | A 3D grid | Simple booleans, topology optimization, medical | Memory (`O(n³)`), no exact surfaces |
| **Point cloud** | Points, maybe normals | Scanning output | Not a solid at all until reconstructed |

**⚠️ NURBS** underpin B-rep surfaces: a rational B-spline with control points, knot vector,
and weights. **The rational part is what lets them represent conic sections exactly** —
a circle is not a spline approximation in NURBS, it's exact. **Degree, continuity (`C⁰`
positional, `C¹` tangent, `C²` curvature — ⚠️ `G²` curvature-continuous is what makes a
surface look right in reflection), and knot multiplicity are the parameters that matter.**

> **⚠️ GOTCHA — the representation determines which operations are even possible.**
> **"Fillet this edge by 3 mm" is natural in B-rep, awkward in CSG, and meaningless on a
> mesh** (you can only approximate it). **"Union these two shapes reliably" is trivial for
> implicits, routine for meshes, and a well-known source of failure in B-rep.** ⚠️ **When
> a CAD operation fails inexplicably, the question is usually whether you're asking the
> representation to do something it isn't built for.**

---
