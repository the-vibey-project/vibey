---
id: skill-16-what-actually-moved-verified-august-2026-65fb148eab
purpose: 16 what actually moved verified august 2026
source: src/vibey_tools/skills/plugins/cad-3d-printing/skills/cad-reference/SKILL.md
requires: ["skill-15-books-and-tools-45008b5f12"]
links: ["skill-17-quick-reference-03d1680271"]
---

## §16. What Actually Moved — verified August 2026

### 16.1 ⚠️ OpenSCAD's Manifold backend
**The most significant change to open code-CAD in years, and one worth getting right
because outdated descriptions are everywhere.**

- **OpenSCAD historically used CGAL**, which is exact and ⚠️ **notoriously slow.**
- **Manifold** replaced it as an alternative backend. **Reported speedups:
  5–30× over CGAL's fast-csg**, which was itself **30–150× over baseline CGAL Nef
  routines** — ⚠️ **with a 1,000× improvement reported on at least one model.**
- **⚠️ Since 2024-09-28 the Manifold backend is no longer experimental** — selectable in
  Preferences → Advanced → 3D Rendering → Backend, or `openscad --backend=manifold` on the
  command line. ⚠️ **The old feature-flag method was removed, which broke some
  command-line scripts.**
- **⚠️ At that announcement, CGAL was still the default backend**, with Manifold opt-in.
- **⚠️ That changed on 2025-08-17**, when OpenSCAD maintainer Marius Kintel announced on the
  project mailing list that **Manifold is now the default backend in development
  snapshots**, calling it "battle tested"; CGAL remains selectable via preferences or
  `--backend=cgal`. ⚠️ **The most recent tagged "stable" release is still 2021.01, which
  predates Manifold support entirely** — anyone using Manifold at all is already on a
  development snapshot, where the default has now flipped.

> **⚠️ GOTCHA — two things to be careful about here.**
> **First, many current sources — including reference documentation and comparison
> articles — still describe OpenSCAD's kernel as simply "CGAL."** That was accurate and
> is now at best incomplete. ⚠️ **Check which backend you're actually running before
> attributing behaviour to a kernel.**
> **Second, the backends are not equivalent in output.** A February 2026 bug report shows
> **a model where Manifold produced STL with open edges that PrusaSlicer auto-repaired,
> while CGAL made most of the model vanish entirely** — and ⚠️ **the reporter's fix was
> adding a small overlap, i.e. the §2 → `cad-geometry-kernels-formats-and-code-cad` epsilon problem.** **If a model behaves oddly, try
> the other backend as a diagnostic.**

### 16.2 The slicer landscape
**⚠️ Almost everything descends from Slic3r.** **OrcaSlicer** is a fork of **Bambu
Studio**, which forked **PrusaSlicer**, which began as **Slic3r PE**. **Cura** is the
separate lineage.

**As of 2026**: **OrcaSlicer** is widely described as the strongest for advanced FDM
tuning — ⚠️ **best-in-class calibration workflows (temperature, flow, pressure advance,
retraction, max volumetric speed), the broadest third-party printer support, native
presets for Klipper input-shaping and pressure-advance, no cloud requirement, and leading
tree/organic support generation.** **Bambu Studio** is strongest on Bambu hardware,
**PrusaSlicer** on Prusa hardware and mature multi-material with a 1–3 month-slower
release cadence, and **Cura** remains the broad beginner-friendly standby with the plugin
ecosystem.

**⚠️ Read that as ecosystem fit, not a ranking**: the honest summary from the comparisons
is that **the right slicer depends almost entirely on what you're printing on**, and
**Klipper users in particular have a clear answer.**

### 16.3 Code-CAD and the LLM angle
**CadQuery and build123d** wrap **OCCT**, giving exact B-rep, true fillets and chamfers,
and **STEP import/export that OpenSCAD cannot do.** **build123d** replaces CadQuery's
fluent method-chaining with **context managers, so ordinary Python loops, references and
filtering work naturally.**

⚠️ **One genuinely interesting current finding, reported by more than one party building
LLM-to-CAD tooling**: **language models write OpenSCAD substantially more reliably than
CadQuery or build123d** — one benchmark reports **3–4× fewer code errors** — attributed to
training-data volume and to OCCT's complexity leaking through the Python wrapper.
> **⚠️ GOTCHA — take that with real caution.** ⚠️ **Both sources reporting it are
> companies whose product is built on OpenSCAD**, so they are not disinterested. **The
> underlying reasoning is plausible** (OpenSCAD's language is small and its corpus is
> large), **but this is a vendor-adjacent benchmark, not an independent one.** ⚠️ **And it
> says nothing about which kernel is better for a human** — the same sources concede that
> OCCT is the more capable kernel.

---
