---
id: skill-16-what-moved-verified-august-2026-f534542668
purpose: 16 what moved verified august 2026
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-reference/SKILL.md
requires: ["skill-15-misconceptions-014a617bc3"]
links: ["skill-17-numbers-71efa8cf31"]
---

## §16. What Moved — verified August 2026

### 16.1 ⚠️ The open basemap landscape
**Overture Maps Foundation** — under the **Linux Foundation**, announced December 2022,
backed by **Amazon, Meta, Microsoft and TomTom**, with **Esri** participating.
**Data assembled from ~200 sources into six themes**, distributed primarily as
**GeoParquet** (and PMTiles), under **CDLA-Permissive v2 where licensing allows.**
**The GA release included 2.3 billion building footprints**, and Overture data
⚠️ **already powers Microsoft's Bing Maps and Esri's ArcGIS Living Atlas**, with Esri
using it to fill coverage gaps in its 3D Buildings layer.

**⚠️ GERS (Global Entity Reference System) is the actual point of Overture**, not the data
volume: **persistent unique IDs attached to real-world entities so datasets can be joined
without re-conflation.** ⚠️ **The stated problem it solves is the "conflation tax" — the
recurring cost of re-matching your data to a new map release.** **As one Overture figure
put it, reality doesn't change, so the IDs shouldn't either.**

> **⚠️ GOTCHA — there is a live and genuinely unresolved governance dispute here, and you
> should know about it before building on GERS.**
> **In early 2026 the OGC considered adopting GERS as a community standard, and the
> proposal drew a sharp reaction from parts of the OpenStreetMap community.** ⚠️ **The
> objections reported are corporate enclosure, opaque governance, a membership model
> cited at $300,000, and a technical criticism of roughly 20% ID churn** — **which, if
> accurate, undercuts the persistence claim that is GERS's entire value proposition.**
>
> ⚠️ **I could not independently verify the churn figure, and it comes from a source
> arguing one side.** **Treat it as a claim to check rather than an established number.**
> **But the dispute itself is real and worth tracking.**

**⚠️ The relationship to OSM is the thing most often got wrong**: ⚠️ **Overture is not a
fork or a competitor — roughly 40% of Overture records come from OpenStreetMap**, the
foundation encourages members to contribute back to OSM, and ⚠️ **Overture data derived
from OSM carries ODbL obligations regardless of Overture's own licence.** **Check the
attribution documentation rather than assuming CDLA covers everything.**

**Also note**: **Esri moved its OpenStreetMap Vector Basemap to mature support in December
2024** after Meta moved the Daylight Distribution to mature support — ⚠️ **a quiet but
real consolidation of the open basemap supply chain toward Overture.**

### 16.2 The cloud-native format stack
**⚠️ The unifying principle is simple and it changed the economics of serving geodata:
put a deterministic layout and a front-loaded index in a single file on object storage,
and let clients fetch only the bytes they need via HTTP range requests.** **No server
process.**
```
COG          raster    ⚠️ internal tiling + overviews — the pattern all the others copied
GeoParquet   vector    columnar analytics; ⚠️ partition by region for large datasets
FlatGeobuf   vector    streamable, bbox-filtered over HTTP
PMTiles      tiles     ⚠️ single-file pyramid; replaces MBTiles, which needed a server
                       because SQLite can't be range-read efficiently
Zarr         N-d       data cubes
COPC         lidar     cloud-optimized point clouds
STAC         metadata  ⚠️ the discovery layer that ties them together
```
**⚠️ Tooling has caught up, which is what makes this practical now**: **tippecanoe
(maintained by Felt since v2.0)** for tile generation, **MapLibre plugins reading COG,
Zarr, PMTiles, FlatGeobuf, GeoParquet and STAC directly in the browser**, **Martin serving
tiles from GeoParquet**, and **DuckDB, Sedona, BigQuery, Snowflake and Databricks all
reading GeoParquet from cloud storage.**

**⚠️ Reported cost effects are large** — one write-up describes moving from GeoServer to
serverless PMTiles on object storage with a **~90% cost reduction** — ⚠️ **though that is a
vendor-adjacent figure and your mileage depends heavily on traffic pattern and egress
pricing.** **The architectural claim (no server process) is solid; treat the percentage as
illustrative.**

**⚠️ When NOT to use these**: **small datasets (<1 MB) where GeoJSON is simpler; interchange
with legacy tools where Shapefile or GeoPackage still wins; and editing workflows needing
row-level mutation, where PostGIS or GeoPackage are the right answer.** **Cloud-native
formats are read-optimized and immutable by design.**

---
