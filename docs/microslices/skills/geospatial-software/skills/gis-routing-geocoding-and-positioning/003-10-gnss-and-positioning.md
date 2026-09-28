---
id: skill-10-gnss-and-positioning-cf02ec6513
purpose: 10 gnss and positioning
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-routing-geocoding-and-positioning/SKILL.md
requires: ["skill-9-geocoding-7d5fa67ffd"]
links: []
---

## §10. GNSS and Positioning

### 10.1 How it works
**⚠️ Trilateration from satellite signal travel times.** **Four satellites minimum — three
for position, the fourth to solve for receiver clock error**, ⚠️ **which is the part people
miss: the receiver's cheap clock is an unknown, not a given.**
**Constellations**: GPS, GLONASS, Galileo, BeiDou, plus QZSS and NavIC regionally.
⚠️ **Multi-constellation receivers are substantially better in urban environments simply
because more satellites are visible.**

### 10.2 ⚠️ Real accuracy
```
Consumer GNSS, open sky       ⚠️ 3–5 m
Urban canyon                  ⚠️ 10–50 m, sometimes far worse
Indoors                       ⚠️ unusable
SBAS (WAAS/EGNOS)             1–3 m
DGPS                          <1 m
RTK                           ⚠️ 1–2 cm — needs a base station or network
PPP                           cm, after convergence time
```
**⚠️ Error sources**: **ionospheric and tropospheric delay, multipath** (⚠️ **signals
bouncing off buildings — the dominant urban error and the reason accuracy degrades in
exactly the places with the most users**), **satellite geometry (DOP)**, ephemeris and
clock errors.

> **⚠️ GOTCHA — the accuracy number your phone reports is a radius of confidence, not a
> guarantee, and it is frequently optimistic.** ⚠️ **Phones fuse GNSS with WiFi
> positioning, cell towers, and inertial sensors, so the reported figure is a fused
> estimate whose provenance you cannot see.** **Never treat a reported accuracy as
> ground truth, and never assume a position is GNSS-derived just because it's precise.**

### 10.3 ⚠️ Altitude is a trap
**GNSS reports height above the ELLIPSOID; maps and people use height above the GEOID
(mean sea level).** ⚠️ **The difference — geoid undulation — ranges roughly ±100 m
globally.**
**⚠️ Converting requires a geoid model (EGM96, EGM2008).** **Reporting raw GNSS altitude as
"elevation" is simply wrong, and it's a common bug in fitness and aviation-adjacent
software.**

### 10.4 Other positioning
**WiFi** (⚠️ **RSSI fingerprinting against a database of access points — this is what
actually locates you indoors, and it's how phones get a fix so fast**), **cell tower**,
**Bluetooth beacons**, **UWB** (⚠️ **10–30 cm, and the basis of precise indoor
positioning**), **inertial dead reckoning** (⚠️ **drifts, so it's a bridge between fixes,
not a positioning system**), and **visual/SLAM** (see a computer-vision reference).
