---
id: skill-17-numbers-71efa8cf31
purpose: 17 numbers
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-reference/SKILL.md
requires: ["skill-16-what-moved-verified-august-2026-f534542668"]
links: ["skill-18-books-and-tools-ed79645aac"]
---

## §17. Numbers

```
EARTH
Equatorial radius 6,378,137 m · polar 6,356,752 m · ⚠️ flattening 1/298.257223563
Mean radius 6,371,008 m · 1° latitude ≈ 111.32 km
⚠️ 1° longitude = 111.32 km × cos(latitude) — 0 at the poles

COORDINATE PRECISION ⚠️
1 decimal place  ~11 km      4 places  ~11 m
2 places         ~1.1 km     5 places  ~1.1 m
3 places         ~110 m      6 places  ~0.11 m  ⚠️ beyond GNSS accuracy — and a privacy risk
7+ places        ⚠️ false precision. Truncate

EPSG
4326 WGS84 lat/lon · 3857 Web Mercator · 4269 NAD83
UTM north 326xx · UTM south 327xx (xx = zone 01–60)

TILES
Zoom 0 = 1 tile · zoom z = 4^z tiles · tile 256×256 (or 512)
⚠️ Web Mercator clipped at ±85.05113°
Resolution at z: ~156543 × cos(lat) / 2^z metres/pixel
⚠️ Vector basemaps typically stop at z14 and overzoom

GNSS ⚠️
Consumer 3–5 m open sky · 10–50 m urban · RTK 1–2 cm
⚠️ 4 satellites minimum (the 4th solves clock error)
Geoid–ellipsoid separation ±100 m

DISTANCE METHODS
Haversine ⚠️ spherical, ~0.5% error · Vincenty ellipsoidal, ~mm, can fail to converge
⚠️ Karney (GeographicLib) — accurate and always converges. Use it

REMOTE SENSING
Landsat 30 m, 16-day · Sentinel-2 10 m, 5-day · SRTM 30 m
```

---
