---
id: skill-7-rendering-4e314a674b
purpose: 7 rendering
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-indexing-databases-tiling-and-rendering/SKILL.md
requires: ["skill-6-tiling-bfc76d418b"]
links: []
---

## §7. Rendering

| Library | ⚠️ Character |
|---|---|
| **MapLibre GL JS** | ⚠️ **The open fork of Mapbox GL JS. WebGL vector rendering; the default for new open work** |
| **Leaflet** | ⚠️ **Simple, tiny, huge plugin ecosystem. Raster-first** |
| **OpenLayers** | ⚠️ **Most feature-complete; handles projections properly — the pick when CRS matters** |
| **deck.gl** | ⚠️ **Large-scale data visualization; GPU layers** |
| **Cesium** | 3D globe, terrain, time |
| **Mapbox GL JS** | Proprietary since v2 |
| **QGIS** | ⚠️ **Desktop GIS; free, excellent, and the tool for actually looking at your data** |

**⚠️ Style specification** (MapLibre/Mapbox style JSON) — declarative layers, sources,
paint and layout properties, **data-driven styling and expressions.** ⚠️ **This is the
piece that makes vector tiles worth it: the same tiles support unlimited cartography.**

**⚠️ Performance**: **simplify by zoom, cluster points, use the GPU rather than DOM,
avoid re-creating sources, and watch that "just add a GeoJSON layer" with 100k features
will destroy your frame rate.** **Put it in a tile pipeline instead.**
