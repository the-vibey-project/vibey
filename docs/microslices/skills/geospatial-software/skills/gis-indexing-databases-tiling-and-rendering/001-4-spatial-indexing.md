---
id: skill-4-spatial-indexing-1504c38831
purpose: 4 spatial indexing
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-indexing-databases-tiling-and-rendering/SKILL.md
requires: []
links: ["skill-5-spatial-databases-36767c2936"]
---

## §4. Spatial Indexing

**⚠️ Spatial queries without an index are table scans, and the whole field exists to avoid
that.**
```
R-tree            ⚠️ hierarchical bounding boxes; THE standard for vector data
                  (PostGIS GiST, SQLite, GeoPackage)
Quadtree          recursive quadrant subdivision; rasters, tiles
k-d tree          point data, nearest-neighbour
Grid / geohash    ⚠️ base32 string; PREFIX = containment, which makes it work in
                  any plain key-value store
S2 (Google)       ⚠️ sphere → cube → Hilbert curve. No projection distortion; excellent
                  for global spherical work
H3 (Uber)         ⚠️ HEXAGONAL global grid. Uniform neighbour distance — better for
                  flow, aggregation and movement analysis
```
> **⚠️ GOTCHA — geohash has an edge problem people trip over.** ⚠️ **Two points a metre
> apart can have completely different prefixes if they straddle a cell boundary.**
> **Proximity search must check neighbouring cells, not just the shared prefix.** **S2 and
> H3 handle adjacency explicitly and are better for anything doing neighbourhood
> queries.**
>
> ⚠️ **And hexagons aren't a gimmick**: **a hexagon's six neighbours are all equidistant
> from its centre; a square's eight are not.** **That matters for anything modelling
> spread, flow or movement.** **The trade is that hexagons don't subdivide perfectly, so
> H3's hierarchy is approximate.**

**⚠️ The two-phase query pattern** underlies essentially all spatial querying: **filter by
bounding box using the index (cheap), then refine with exact geometry (expensive).**
**Getting this wrong — doing exact tests first — is a common performance bug.**

---
