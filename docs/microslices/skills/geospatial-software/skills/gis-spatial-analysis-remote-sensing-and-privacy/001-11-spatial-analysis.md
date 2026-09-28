---
id: skill-11-spatial-analysis-12e2cf65fd
purpose: 11 spatial analysis
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-spatial-analysis-remote-sensing-and-privacy/SKILL.md
requires: []
links: ["skill-12-remote-sensing-0c5b3a12bd"]
---

## §11. Spatial Analysis

**Overlay** — intersection, union, difference, symmetric difference.
**Buffer** — ⚠️ **and buffering in degrees is a classic error; a 0.001° buffer is ~111 m at
the equator and ~40 m at 70° latitude. Project first.**
**Spatial joins**, **dissolve/aggregate**, **centroid** (⚠️ **which can fall outside a
concave polygon — use `ST_PointOnSurface` when you need a point that's actually inside**),
**convex and concave hulls**, **Voronoi and Delaunay**, **simplification**
(⚠️ **Douglas-Peucker is standard; Visvalingam-Whyatt often looks better**).

**⚠️ Spatial statistics has its own pitfalls, and they're substantive:**
- **Spatial autocorrelation** — ⚠️ **Tobler's first law: near things are more related.**
  **This violates the independence assumption of ordinary regression**, so **Moran's I,
  Geary's C, and spatially-explicit models exist for a reason.**
- **⚠️ MAUP (modifiable areal unit problem)** — **results change with the size and shape of
  your aggregation units.** ⚠️ **This is not a nuisance, it's a fundamental limitation of
  areal data, and gerrymandering is its most famous exploitation.**
- **⚠️ Ecological fallacy** — **area-level correlations do not transfer to individuals.**
- **Interpolation**: IDW, ⚠️ **kriging (which uniquely gives you an uncertainty estimate
  alongside the prediction)**, splines.

---
