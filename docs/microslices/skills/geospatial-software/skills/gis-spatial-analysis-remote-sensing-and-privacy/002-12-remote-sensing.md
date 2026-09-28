---
id: skill-12-remote-sensing-0c5b3a12bd
purpose: 12 remote sensing
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-spatial-analysis-remote-sensing-and-privacy/SKILL.md
requires: ["skill-11-spatial-analysis-12e2cf65fd"]
links: ["skill-13-data-sources-b53f3c1a1c"]
---

## §12. Remote Sensing

**Resolution has four dimensions** — ⚠️ **spatial, spectral, temporal, radiometric — and
they trade against each other.**
**Platforms**: **Landsat** (⚠️ **30 m, free, and continuous since 1972 — the longest
record**), **Sentinel-1 SAR** and **Sentinel-2** (⚠️ **10 m, 5-day revisit, free**),
**MODIS/VIIRS**, commercial sub-metre.
**⚠️ SAR is the underused one**: **active, so it works at night and sees through cloud** —
and **InSAR measures ground deformation to millimetres** (see a geoscience reference).
**Indices**: **NDVI** `(NIR−Red)/(NIR+Red)` for vegetation, NDWI, NDBI.
**⚠️ Processing levels matter**: **Level-1 is top-of-atmosphere; Level-2 is
surface reflectance after atmospheric correction.** ⚠️ **Comparing TOA across dates is
meaningless — use surface reflectance for any time series.**
**Platforms**: **Google Earth Engine**, **Microsoft Planetary Computer**, **STAC** catalogs.

---
