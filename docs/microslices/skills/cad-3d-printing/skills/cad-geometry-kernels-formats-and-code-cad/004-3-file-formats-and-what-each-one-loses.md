---
id: skill-3-file-formats-and-what-each-one-loses-5c85d515ca
purpose: 3 file formats and what each one loses
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-geometry-kernels-formats-and-code-cad/SKILL.md
requires: ["skill-2-kernels-12a8cd9ef7"]
links: ["skill-4-code-cad-and-scripting-a3254bd0fb"]
---

## §3. File Formats — and what each one loses

| Format | Carries | ⚠️ Loses |
|---|---|---|
| **STL** | Triangles only | ⚠️ **Units, colour, topology (it's a "triangle soup"), materials, ALL parametric intent** |
| **OBJ** | Triangles, UVs, materials | Solid topology |
| **3MF** | ⚠️ **Mesh + units + colour + materials + print settings, zipped XML** | Parametric history |
| **AMF** | Similar intent to 3MF | ⚠️ **Largely superseded by 3MF** |
| **STEP (AP203/214/242)** | ⚠️ **Exact B-rep solids, assemblies; AP242 adds PMI** | Feature tree, parametric history |
| **IGES** | Surfaces | ⚠️ **Legacy, often no solid topology. Avoid if STEP is available** |
| **native (.sldprt, .f3d, .FCStd)** | Everything including history | ⚠️ **Portability** |
| **glTF** | Rendering-oriented | Engineering data |

> **⚠️ GOTCHA — STL has no units.** The file contains bare numbers. **"Is this
> millimetres or inches?" is resolved by convention and hope**, which is why parts
> occasionally arrive 25.4× wrong. **3MF fixes this and should be your default mesh
> format** — it carries units, and modern slicers all read it.
>
> **⚠️ And STL is a triangle soup, not a mesh**: each triangle independently lists three
> vertices with no shared-vertex indexing. **Adjacency has to be reconstructed by
> position-matching, which is where floating-point tolerance decides whether your model
> is watertight.**

**⚠️ The pipeline rule**: **STEP between CAD tools, 3MF to the printer, STL only when
something old demands it.** Going CAD → STL → CAD is a lossy round trip that leaves you
with a mesh you cannot parametrically edit.

---
