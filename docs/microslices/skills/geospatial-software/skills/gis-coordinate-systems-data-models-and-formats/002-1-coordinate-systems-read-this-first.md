---
id: skill-1-coordinate-systems-read-this-first-12c8733c5a
purpose: 1 coordinate systems read this first
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-coordinate-systems-data-models-and-formats/SKILL.md
requires: ["skill-0-routing-a7bcc3627a"]
links: ["skill-2-data-models-772243b077"]
---

## §1. Coordinate Systems — Read This First

### 1.1 The layered model
```
GEOID       ⚠️ the actual equipotential surface — lumpy, ±100 m from the ellipsoid
ELLIPSOID   a smooth mathematical approximation (e.g. GRS80, WGS84)
DATUM       ⚠️ an ellipsoid ANCHORED to the Earth — this is what makes coordinates mean
            something physical
CRS         datum + coordinate system (geographic lat/lon, or projected x/y)
```
**⚠️ Geographic CRS** — angular latitude/longitude on an ellipsoid. **Projected CRS** —
planar metres, produced by a projection.

**⚠️ Datums differ, and the differences are large enough to matter:**
- **WGS84** — the GPS datum, global.
- **NAD83** — North American; ⚠️ **differs from WGS84 by roughly 1–2 metres and growing.**
- **ETRS89** — European, ⚠️ **fixed to the Eurasian plate, so it diverges from WGS84 at
  plate-motion rates (~2.5 cm/year).**
- **GDA2020** — Australian; ⚠️ **Australia moves ~7 cm/year, which is why the datum was
  re-realized at all.**
> **⚠️ GOTCHA — datums drift because continents move.** ⚠️ **A coordinate captured in 1994
> and one captured today in a plate-fixed datum describe different physical points even
> with identical numbers.** **For centimetre work you need an *epoch*, not just a datum.**
> **This is why modern datums carry a year in the name.**

**EPSG codes** identify CRSs: **4326** (WGS84 lat/lon), **3857** (Web Mercator),
**UTM zones 32601–32660 N / 32701–32760 S**, **4269** (NAD83).

### 1.2 ⚠️ The axis order problem
> **⚠️ GOTCHA — this causes more geospatial bugs than any other single issue.**
> ⚠️ **EPSG:4326 is formally defined as (latitude, longitude). GeoJSON, most web APIs, and
> most JavaScript libraries use (longitude, latitude).** **PostGIS uses (x, y) = (lon,
> lat).** **Some WMS versions swapped between 1.1.1 and 1.3.0.**
>
> **⚠️ The symptom is diagnostic: your data appears off the coast of West Africa** —
> near (0,0) in the Gulf of Guinea — **or lands in the wrong hemisphere.** **Whenever
> anything looks like that, check axis order first.**
>
> **The defence**: name your variables `lon`/`lat`, never `x`/`y`; **assert plausible
> ranges (`|lat| ≤ 90`) at every boundary**; and ⚠️ **note that latitudes above 90 are
> impossible while longitudes above 90 are fine, which is what makes the assertion
> asymmetric and useful.**

### 1.3 Projections
**⚠️ Every projection distorts; you choose what to preserve.**
```
CONFORMAL      preserves ANGLES locally  ⚠️ distorts area
               Mercator, Web Mercator, Lambert Conformal Conic, UTM
EQUAL-AREA     preserves AREA            ⚠️ distorts shape
               Albers, Mollweide, Equal Earth
EQUIDISTANT    preserves distance from a point or along lines
COMPROMISE     Robinson, Winkel Tripel — ⚠️ preserves nothing exactly, looks reasonable
```
**⚠️ Web Mercator (EPSG:3857) deserves specific warnings**, because it's the default of the
entire web:
- **Massive area distortion toward the poles** — ⚠️ **Greenland appears comparable to
  Africa and is about 14× smaller.**
- **⚠️ It uses a SPHERICAL model with ellipsoidal coordinates, which is mathematically
  inconsistent** and is why it has no proper EPSG standing for surveying.
- **Clipped around ±85.05°** to keep the map square.
- ⚠️ **NEVER compute areas or distances in Web Mercator.** **Reproject to an equal-area or
  local projection first.** **This is a common and silent source of wrong analysis.**

**Choosing**: ⚠️ **local/national grid for national work; UTM for regional metric work
(6° zones — and beware working across a zone boundary); equal-area for any statistic
involving area; Web Mercator for display only.**

**⚠️ PROJ is the library that does this** (via GDAL, PostGIS, and nearly everything else).
**Datum transformations need grid shift files for accuracy** — ⚠️ **and a missing grid
silently falls back to a lower-accuracy method rather than erroring, which is exactly the
kind of failure you don't notice.**

---
