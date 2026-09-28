---
id: skill-13-data-sources-b53f3c1a1c
purpose: 13 data sources
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-spatial-analysis-remote-sensing-and-privacy/SKILL.md
requires: ["skill-12-remote-sensing-0c5b3a12bd"]
links: ["skill-14-privacy-4a9ac42790"]
---

## §13. Data Sources

**OpenStreetMap** — ⚠️ **the foundational open dataset; ODbL licensed, which is share-alike
and has real obligations for derived databases.** **Extracts via Geofabrik, Overpass API
for queries, planet.osm for the whole thing.**
**Overture Maps** — §16.1 → `gis-reference`.
**Government and open data**: **US Census TIGER**, **USGS 3DEP** (elevation), **Natural
Earth** (⚠️ **the right choice for small-scale cartography — clean, public domain,
generalized**), **Copernicus**, **national mapping agencies** (⚠️ **licensing varies
enormously — Ordnance Survey is largely commercial, many EU agencies are open**).
**Elevation**: SRTM (30 m global), Copernicus DEM, national lidar.
**Commercial**: Google, HERE, TomTom, Esri, Mapbox.

**⚠️ Licensing is the part that catches engineering teams, and it is not optional
reading**: **ODbL's share-alike applies to derived databases and is genuinely restrictive
for commercial products; Google Maps terms prohibit storing results, using them with
non-Google basemaps, and much else; Natural Earth and most US federal data are public
domain.** ⚠️ **Check before you build, because "we'll swap the data source later" is
rarely cheap.**

---
