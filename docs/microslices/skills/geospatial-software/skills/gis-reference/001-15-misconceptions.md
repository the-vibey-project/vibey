---
id: skill-15-misconceptions-014a617bc3
purpose: 15 misconceptions
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-reference/SKILL.md
requires: []
links: ["skill-16-what-moved-verified-august-2026-f534542668"]
---

## §15. Misconceptions

| Misconception | Correction |
|---|---|
| A lat/lon pair is a location | ⚠️ **Not without a CRS and epoch** (§1 → `gis-coordinate-systems-data-models-and-formats`) |
| EPSG:4326 is (lon, lat) | ⚠️ **Formally (lat, lon). GeoJSON is (lon, lat). Check every boundary** (§1.2 → `gis-coordinate-systems-data-models-and-formats`) |
| Web Mercator is fine for analysis | ⚠️ **Never compute area or distance in it** (§1.3 → `gis-coordinate-systems-data-models-and-formats`) |
| WGS84 and NAD83 are the same | ⚠️ **1–2 m apart and diverging** (§1.1 → `gis-coordinate-systems-data-models-and-formats`) |
| Datums are static | ⚠️ **Continents move; modern datums carry an epoch** (§1.1 → `gis-coordinate-systems-data-models-and-formats`) |
| Haversine is accurate | ⚠️ **Spherical — up to ~0.5% off. Use Vincenty/Karney for precision** (§17) |
| GNSS altitude is elevation | ⚠️ **Ellipsoidal vs geoid — up to ±100 m** (§10.3 → `gis-routing-geocoding-and-positioning`) |
| Reported GPS accuracy is real accuracy | ⚠️ **A fused confidence estimate, often optimistic** (§10.2 → `gis-routing-geocoding-and-positioning`) |
| Buffer in degrees | ⚠️ **111 m at the equator, ~40 m at 70°. Project first** (§11 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| A centroid is inside its polygon | ⚠️ **Not for concave shapes. Use ST_PointOnSurface** (§11 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| `ST_Distance` on 4326 gives metres | ⚠️ **It gives degrees. Use geography or project** (§5 → `gis-indexing-databases-tiling-and-rendering`) |
| Geohash prefixes solve proximity | ⚠️ **Edge problem — check neighbouring cells** (§4 → `gis-indexing-databases-tiling-and-rendering`) |
| Spatial data can use ordinary regression | ⚠️ **Autocorrelation violates independence** (§11 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| Aggregation boundaries don't affect results | ⚠️ **MAUP. They do, fundamentally** (§11 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| Shapefile is a reasonable modern choice | ⚠️ **2 GB, 10-char fields, encoding issues** (§3 → `gis-coordinate-systems-data-models-and-formats`) |
| Nearest-road snapping is map matching | ⚠️ **Use an HMM; parallel roads and overpasses break naive snapping** (§8 → `gis-routing-geocoding-and-positioning`) |
| Comparing TOA imagery across dates is valid | ⚠️ **Use surface reflectance** (§12 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| Anonymized location data is anonymous | ⚠️ **~4 points identify an individual** (§14 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| OSM data is free to use however you like | ⚠️ **ODbL is share-alike with real obligations** (§13 → `gis-spatial-analysis-remote-sensing-and-privacy`) |
| Overture replaces OpenStreetMap | ⚠️ **It's largely built FROM OSM — ~40% of records** (§16.1) |

---
