---
id: skill-6-tiling-bfc76d418b
purpose: 6 tiling
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-indexing-databases-tiling-and-rendering/SKILL.md
requires: ["skill-5-spatial-databases-36767c2936"]
links: ["skill-7-rendering-4e314a674b"]
---

## §6. Tiling

**⚠️ Serve maps as small pre-cut squares, not one giant image.**
**Slippy map scheme**: `z/x/y`, ⚠️ **doubling resolution per zoom level, in Web Mercator
(§1.3 → `gis-coordinate-systems-data-models-and-formats`).** **Zoom 0 is one 256×256 tile of the world; zoom `z` has `4^z` tiles.**
**⚠️ TMS flips the Y axis relative to XYZ/Google convention — a small, recurring source of
upside-down maps.**

**Raster vs vector tiles:**
- **Raster** — pre-rendered images. ⚠️ **Simple; styling is baked in, so restyling means
  re-rendering everything.**
- **Vector (MVT)** — ⚠️ **geometry plus attributes, styled on the client.** **Restyle
  instantly, rotate and tilt, high-DPI for free, smaller.** **The default for new work.**

**⚠️ Generation**: **tippecanoe** (⚠️ **the standard tool; it adaptively simplifies and
drops features per zoom to keep tiles small — that behaviour is a feature and it will
surprise you if you don't expect dropped features at low zoom**), **planetiler** for
planet-scale, **Martin** and **tegola** for dynamic serving from PostGIS.
**⚠️ Overzooming** lets you serve zoom 14 tiles up to zoom 20 by scaling client-side —
**which is why most vector basemaps stop generating at 14.**

---
