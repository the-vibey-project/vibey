---
id: skill-5-spatial-databases-36767c2936
purpose: 5 spatial databases
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-indexing-databases-tiling-and-rendering/SKILL.md
requires: ["skill-4-spatial-indexing-1504c38831"]
links: ["skill-6-tiling-bfc76d418b"]
---

## §5. Spatial Databases

**PostGIS** is the reference implementation and the default choice.
```sql
-- ⚠️ Always index, always use && or ST_DWithin to hit it
CREATE INDEX idx ON t USING GIST (geom);

ST_Intersects, ST_Contains, ST_Within, ST_DWithin   -- ⚠️ these use the index
ST_Distance, ST_Area, ST_Length, ST_Buffer
ST_Transform(geom, 3857)     -- ⚠️ reproject
ST_MakeValid(geom)           -- §2
```
> **⚠️ GOTCHA — `geometry` vs `geography` is the type decision that matters.**
> ⚠️ **`geometry` is planar and fast; distances and areas are in the CRS's units, so
> using it with EPSG:4326 gives you answers in DEGREES, which are meaningless as
> distance.** **`geography` computes on the spheroid and returns metres, correctly, and is
> slower with fewer functions.**
> **⚠️ The pragmatic pattern: store `geometry` in a suitable projected CRS, or use
> `geography` for global data where correctness beats speed, and cast where needed.**
> **`ST_Distance` on 4326 geometry returning "0.0043" is the classic symptom.**

**⚠️ `ST_DWithin` beats `ST_Distance(...) < x`** — the former uses the index, the latter
computes distance for every row first.
**Others**: **SpatiaLite**, **DuckDB spatial** (⚠️ **increasingly the analytics choice, and
it reads GeoParquet directly**), **BigQuery GIS**, **Snowflake**, **Elasticsearch geo**,
**MongoDB 2dsphere**, **Apache Sedona** for distributed work.

---
