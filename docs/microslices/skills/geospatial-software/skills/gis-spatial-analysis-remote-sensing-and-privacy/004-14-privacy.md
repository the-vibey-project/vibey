---
id: skill-14-privacy-4a9ac42790
purpose: 14 privacy
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-spatial-analysis-remote-sensing-and-privacy/SKILL.md
requires: ["skill-13-data-sources-b53f3c1a1c"]
links: []
---

## §14. Privacy

> **⚠️ GOTCHA — location data is among the most sensitive categories that exists, and
> "anonymized" location data usually isn't.** ⚠️ **Four spatiotemporal points are
> typically enough to uniquely identify an individual in a mobility dataset** — the
> foundational result here — **because human movement patterns are extraordinarily
> distinctive.** **Home and work locations fall out of a trace almost immediately.**

**⚠️ What location data reveals directly**: home, workplace, religious attendance, medical
facility visits, protest attendance, relationships (co-location), and routine — ⚠️ **which
means it functions as a proxy for several protected categories at once.**

**Regulation**: **GDPR treats location as personal data** (⚠️ **and inferences from it can
be special-category data**), **CCPA/CPRA names precise geolocation as sensitive personal
information**, and platform rules (iOS/Android permission models, background location
restrictions) are tightening independently.

**⚠️ Engineering practices that actually help:**
- **Collect the coarsest granularity that works.** ⚠️ **City-level often suffices for what
  the product actually does.**
- **Truncate precision** — ⚠️ **a 5th decimal place is ~1 m; you almost never need it.**
- **Aggregate and apply k-anonymity thresholds before release**; consider **differential
  privacy** for published statistics.
- **⚠️ Redact around sensitive POIs** — clinics, places of worship, shelters.
- **Short retention.** **Fuzz or exclude home locations.** **On-device processing where
  possible.**
- **⚠️ Be honest in the permission prompt** — "while using the app" versus background is a
  meaningfully different ask and users understand the difference.
