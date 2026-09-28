---
id: skill-3-file-formats-85ad4ea723
purpose: 3 file formats
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-coordinate-systems-data-models-and-formats/SKILL.md
requires: ["skill-2-data-models-772243b077"]
links: []
---

## §3. File Formats

| Format | Type | ⚠️ Notes |
|---|---|---|
| **GeoJSON** | Vector, text | ⚠️ **Simple and universal; WGS84 only by spec; verbose; no index** |
| **Shapefile** | Vector | ⚠️ **Ancient, multi-file, 2 GB limit, 10-char field names, no UTF-8 guarantee. Still everywhere. Avoid for new work** |
| **GeoPackage** | Vector + raster | ⚠️ **SQLite-based; the right modern replacement for Shapefile** |
| **FlatGeobuf** | Vector, binary | ⚠️ **Streamable, spatially indexed, HTTP-range readable** |
| **GeoParquet** | Vector, columnar | ⚠️ **Cloud-native analytics; the §16 → `gis-reference` format** |
| **PMTiles** | Tiles, single file | ⚠️ **Serverless tile pyramid via range requests** |
| **GeoTIFF / COG** | Raster | ⚠️ **COG adds internal tiling + overviews for partial reads** |
| **Zarr** | N-d arrays | Multidimensional cubes; climate and time series |
| **COPC** | Point cloud | Cloud-optimized LAZ |
| **KML** | Vector | Google-origin; display-oriented |
| **WKT / WKB** | Geometry encoding | ⚠️ **WKT is text, WKB binary; the database interchange pair** |
| **MVT** | Vector tile | ⚠️ **Protobuf; the web vector tile standard** |

**⚠️ The rule for choosing**: **GeoPackage or FlatGeobuf for files, GeoParquet for
analytics at scale, PMTiles for serving map tiles, COG for imagery, GeoJSON only for small
data and interchange.** ⚠️ **Shapefile only when something old demands it — and its
limitations will bite you eventually.**
