---
id: skill-18-books-and-tools-ed79645aac
purpose: 18 books and tools
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-reference/SKILL.md
requires: ["skill-17-numbers-71efa8cf31"]
links: ["skill-19-quick-reference-8a8f7dff43"]
---

## §18. Books and Tools

| Source | Why |
|---|---|
| **Iliffe & Lott, *Datums and Map Projections*** | ⚠️ **§1 → `gis-coordinate-systems-data-models-and-formats` properly. The book that prevents the expensive bugs** |
| **Snyder, *Map Projections: A Working Manual*** (USGS) | ⚠️ **Free, canonical, has the actual formulas** |
| **Longley et al., *Geographic Information Systems and Science*** | The broad textbook |
| **Obe & Hsu, *PostGIS in Action*** | ⚠️ **§5 → `gis-indexing-databases-tiling-and-rendering`, and genuinely practical** |
| **de Smith, Goodchild & Longley, *Geospatial Analysis*** | ⚠️ **Free online, encyclopaedic on §11 → `gis-spatial-analysis-remote-sensing-and-privacy`** |
| **Brovelli et al. / *Open Source Geospatial* materials** | The FOSS4G ecosystem |
| **Tyner, *Principles of Map Design*** | ⚠️ **Cartography — the part engineers skip and shouldn't** |
| **Tufte / Brewer (ColorBrewer)** | ⚠️ **ColorBrewer for map colour schemes — use it rather than inventing** |

**Tools**: **QGIS** (⚠️ **desktop, free, excellent**), **GDAL/OGR** (⚠️ **the universal
translator; `ogr2ogr` and `gdalwarp` will do most conversions you need**), **PROJ**,
**PostGIS**, **GeoPandas/Shapely/Rasterio/Xarray**, **DuckDB spatial**, **Turf.js**,
**tippecanoe**, **planetiler**, **MapLibre**, **Leaflet**, **OpenLayers**, **deck.gl**,
**OSRM/Valhalla**, **Nominatim/Pelias**, **libpostal**.
**Communities**: **FOSS4G**, **Cloud-Native Geospatial Forum**, **OSM community**,
**GIS StackExchange** (⚠️ **unusually high quality**).

---
