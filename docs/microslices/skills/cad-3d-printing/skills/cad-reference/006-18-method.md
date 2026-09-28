---
id: skill-18-method-4bd06f0dfe
purpose: 18 method
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-reference/SKILL.md
requires: ["skill-17-quick-reference-03d1680271"]
links: []
---

## §18. Method

**§1–§12 → `cad-geometry-kernels-formats-and-code-cad`, `cad-slicing-pipeline-and-processes`, `cad-design-tolerances-and-materials`, `cad-generative-automation-and-scanning` rest on stable material** — NURBS and B-rep mathematics, computational geometry,
mesh processing, and additive manufacturing process physics — sourced from the references
in §15, chiefly **Piegl & Tiller**, **Botsch et al.**, and **Gibson, Rosen & Stucker**,
plus the file-format specifications. ⚠️ **None of that needed web verification; the
geometry math is decades old and the process physics is thermodynamics.**

**Two searches were run in August 2026**, confined to the tooling: **the code-CAD
ecosystem** and **the OpenSCAD kernel and slicer landscape.**

**⚠️ The second search materially corrected the first.** Several sources returned by the
code-CAD search — **including CadQuery's own documentation and multiple 2026
comparison articles** — describe OpenSCAD's kernel as CGAL and contrast it unfavourably
with OCCT on that basis. **That framing predates the Manifold work.** I followed up
specifically and found the **OpenSCAD mailing list announcement (2024-09-28) that Manifold
is no longer experimental**, a **later mailing list post (2025-08-17) from the same
maintainer confirming Manifold became the default backend in development snapshots**, plus
**the Manifold project's own performance discussion** for the speedup figures. ⚠️ **§16.1
reflects that; the widely-repeated "OpenSCAD uses CGAL" line is now incomplete.**

**Confidence.** **High** in §1–§12 → `cad-geometry-kernels-formats-and-code-cad`, `cad-slicing-pipeline-and-processes`, `cad-design-tolerances-and-materials`, `cad-generative-automation-and-scanning` — established mathematics and process physics, with
numbers stated as representative ranges that vary by machine and material. **High** in
§16.1's Manifold facts, which come from the project and the OpenSCAD maintainers directly,
including that **CGAL remained the default backend at the time of the 2024-09-28
announcement, and that Manifold became the default in development snapshots as of
2025-08-17** — ⚠️ **verify which snapshot and backend you are actually running rather than
assuming, since the tagged "stable" release (2021.01) predates either backend option.**

⚠️ **Two explicit hedges.** **§16.2's slicer assessment is drawn from comparison articles,
which are opinion-shaped and frequently affiliate-monetized**; I have framed it as
ecosystem fit rather than a ranking, and the technical lineage (Slic3r → PrusaSlicer →
Bambu Studio → OrcaSlicer) is the part that is unambiguous. And ⚠️ **§16.3's LLM benchmark
is flagged in place as vendor-adjacent** — **both parties reporting it build products on
OpenSCAD.** The mechanism they propose is plausible and the finding may well be right, but
**it is not an independent evaluation and I have not treated it as one.**

**§14's tolerance and clearance figures are starting points, not specifications** —
⚠️ **the §8 → `cad-design-tolerances-and-materials` advice to run a calibration print is the actual recommendation, and it
supersedes any table including mine.**
