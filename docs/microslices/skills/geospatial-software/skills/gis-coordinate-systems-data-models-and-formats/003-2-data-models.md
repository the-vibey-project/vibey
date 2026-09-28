---
id: skill-2-data-models-772243b077
purpose: 2 data models
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-coordinate-systems-data-models-and-formats/SKILL.md
requires: ["skill-1-coordinate-systems-read-this-first-12c8733c5a"]
links: ["skill-3-file-formats-85ad4ea723"]
---

## §2. Data Models

**Vector** — points, lines, polygons with attributes. ⚠️ **Discrete features with sharp
boundaries.**
**Raster** — a grid of cells. ⚠️ **Continuous phenomena: elevation, imagery, temperature.**
**⚠️ The choice is about the phenomenon, not preference**: a road is a line; elevation is a
surface. **Forcing one into the other is where bad models start.**

**Geometry types (OGC Simple Features)**: Point, LineString, Polygon, and the Multi-
variants, GeometryCollection. **Polygons have an exterior ring and optional interior rings
(holes)**, ⚠️ **with ring winding order conventions that differ between specifications —
and GeoJSON's right-hand rule is widely violated in the wild.**

**⚠️ Validity is a real and under-checked property**: self-intersections, unclosed rings,
duplicate points, holes outside their shell. ⚠️ **Invalid geometry causes downstream
operations to fail or, worse, to silently return nonsense.** **`ST_IsValid` /
`ST_MakeValid` in PostGIS; check on ingest, not on error.**

**Topology** — ⚠️ **shared boundaries between adjacent polygons.** **Storing them
independently means they drift apart under editing, producing slivers and gaps.**
**Topological models store the shared edge once.**

---
