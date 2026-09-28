---
id: skill-9-geocoding-7d5fa67ffd
purpose: 9 geocoding
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-routing-geocoding-and-positioning/SKILL.md
requires: ["skill-8-routing-b4fb25541a"]
links: ["skill-10-gnss-and-positioning-cf02ec6513"]
---

## §9. Geocoding

**Forward** (address → coordinate) and **reverse** (coordinate → address).
**⚠️ The reason it's hard is that addresses are human artifacts, not a coordinate system**:
inconsistent formats, abbreviations, misspellings, multilingual and transliterated forms,
ambiguous names (⚠️ **there are dozens of Springfields**), buildings without numbers, and
countries where addressing is informal or absent.

**⚠️ Pipeline**: **parse** (⚠️ **libpostal is the standard for international address
parsing and it's genuinely hard to beat**) → **normalize** → **match** (fuzzy, hierarchical)
→ **rank by confidence**.
**Engines**: **Nominatim** (OSM), **Pelias**, **Photon**, commercial APIs.
**⚠️ Quality varies enormously by region**, and ⚠️ **always propagate a confidence score
and match type (rooftop / interpolated / street / city) rather than returning a bare
coordinate — an interpolated street-level match presented as exact is a real source of
downstream error.**

---
