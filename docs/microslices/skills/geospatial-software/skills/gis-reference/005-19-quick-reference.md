---
id: skill-19-quick-reference-8a8f7dff43
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-reference/SKILL.md
requires: ["skill-18-books-and-tools-ed79645aac"]
links: ["skill-20-method-2c703cdce7"]
---

## §19. Quick Reference

### 19.1 Picker
| Need | Use |
|---|---|
| Store vector data in a file | ⚠️ **GeoPackage or FlatGeobuf — not Shapefile** (§3 → `gis-coordinate-systems-data-models-and-formats`) |
| Analytics on huge vector data | ⚠️ **GeoParquet + DuckDB** (§3 → `gis-coordinate-systems-data-models-and-formats`, §16.2) |
| Serve a basemap with no server | ⚠️ **PMTiles on object storage** (§6 → `gis-indexing-databases-tiling-and-rendering`, §16.2) |
| Serve imagery | **COG** (§3 → `gis-coordinate-systems-data-models-and-formats`) |
| Spatial queries with attributes | **PostGIS** (§5 → `gis-indexing-databases-tiling-and-rendering`) |
| Global point index in a KV store | **Geohash — ⚠️ handle edges** (§4 → `gis-indexing-databases-tiling-and-rendering`) |
| Neighbourhood/flow analysis | ⚠️ **H3 — equidistant neighbours** (§4 → `gis-indexing-databases-tiling-and-rendering`) |
| Spherical indexing without projection distortion | **S2** (§4 → `gis-indexing-databases-tiling-and-rendering`) |
| Compute area | ⚠️ **Equal-area projection, or `geography`** (§1.3 → `gis-coordinate-systems-data-models-and-formats`, §5 → `gis-indexing-databases-tiling-and-rendering`) |
| Accurate distance between two points | ⚠️ **Karney/GeographicLib** (§17) |
| Web map, vector, open | **MapLibre GL JS** (§7 → `gis-indexing-databases-tiling-and-rendering`) |
| Web map where CRS matters | ⚠️ **OpenLayers** (§7 → `gis-indexing-databases-tiling-and-rendering`) |
| Millions of points on a map | **deck.gl, or tile it** (§7 → `gis-indexing-databases-tiling-and-rendering`) |
| Routing, static costs | **OSRM (CH)** (§8 → `gis-routing-geocoding-and-positioning`) |
| Routing with traffic | ⚠️ **Valhalla (MLD)** (§8 → `gis-routing-geocoding-and-positioning`) |
| Snap GPS traces to roads | ⚠️ **HMM map matching, not nearest-neighbour** (§8 → `gis-routing-geocoding-and-positioning`) |
| Parse international addresses | **libpostal** (§9 → `gis-routing-geocoding-and-positioning`) |
| Convert anything to anything | **`ogr2ogr`** (§18) |

### 19.2 Debugging checklist
- [ ] Do I know the CRS of every input, and do they match? (§1 → `gis-coordinate-systems-data-models-and-formats`)
- [ ] Axis order — is my data in the Gulf of Guinea? (§1.2 → `gis-coordinate-systems-data-models-and-formats`)
- [ ] Am I computing area or distance in Web Mercator? (§1.3 → `gis-coordinate-systems-data-models-and-formats`)
- [ ] Am I buffering in degrees? (§11 → `gis-spatial-analysis-remote-sensing-and-privacy`)
- [ ] Is `ST_Distance` returning suspiciously small numbers? ⚠️ **Degrees** (§5 → `gis-indexing-databases-tiling-and-rendering`)
- [ ] Are my geometries valid? (§2 → `gis-coordinate-systems-data-models-and-formats`)
- [ ] Is the spatial index actually being used — check the query plan (§5 → `gis-indexing-databases-tiling-and-rendering`)
- [ ] Ellipsoidal or geoid height? (§10.3 → `gis-routing-geocoding-and-positioning`)
- [ ] Is that reported accuracy fused or GNSS? (§10.2 → `gis-routing-geocoding-and-positioning`)
- [ ] Have I checked the licence of every data source? (§13 → `gis-spatial-analysis-remote-sensing-and-privacy`)
- [ ] Am I collecting more location precision than the product needs? (§14 → `gis-spatial-analysis-remote-sensing-and-privacy`)

---
