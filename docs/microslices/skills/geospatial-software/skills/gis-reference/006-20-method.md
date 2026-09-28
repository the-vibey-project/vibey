---
id: skill-20-method-2c703cdce7
purpose: 20 method
source: src/vibey_tools/skills/plugins/geospatial-software/skills/gis-reference/SKILL.md
requires: ["skill-19-quick-reference-8a8f7dff43"]
links: []
---

## §20. Method

**§1–§12 → `gis-coordinate-systems-data-models-and-formats`, `gis-indexing-databases-tiling-and-rendering`, `gis-routing-geocoding-and-positioning`, `gis-spatial-analysis-remote-sensing-and-privacy`, §14 → `gis-spatial-analysis-remote-sensing-and-privacy`, §15 and §17 rest on settled material** — **geodesy, projection mathematics
(Snyder's USGS manual is still the reference), OGC Simple Features, and standard
algorithms** — plus the references in §18. ⚠️ **Projection math has not changed since
Snyder, and the CRS bugs in §1 → `gis-coordinate-systems-data-models-and-formats` and §15 are the same ones people have made for thirty
years.**

**Two searches were run in August 2026**, on the two things that genuinely moved: **the
open basemap data landscape** and **the cloud-native format stack.**

**Confidence.** **High** in §1–§12 → `gis-coordinate-systems-data-models-and-formats`, `gis-indexing-databases-tiling-and-rendering`, `gis-routing-geocoding-and-positioning`, `gis-spatial-analysis-remote-sensing-and-privacy` and §14 → `gis-spatial-analysis-remote-sensing-and-privacy`. ⚠️ **§1 → `gis-coordinate-systems-data-models-and-formats` and §15 are where I'd put the emphasis
regardless of anything else in this document — the axis-order bug and Web Mercator area
calculation are responsible for an enormous share of real-world geospatial errors, and
both are trivially preventable once named.**

**High** in §16.2, which is well-corroborated across the Cloud-Native Geospatial Forum,
tooling documentation, and multiple independent practitioners. ⚠️ **The one figure I've
flagged is the "90% cost reduction" claim, which is vendor-adjacent — the architectural
claim underneath it (no server process, range reads from object storage) is solid and
uncontroversial.**

⚠️ **§16.1 needs a specific caution and I've built it into the section.** **The factual
core is well attested from Overture's own materials, the Linux Foundation, Esri, and the
OSM wiki**: the membership, the themes, GeoParquet distribution, GERS's purpose, the
2.3 billion buildings, the Bing and ArcGIS integrations, and ⚠️ **the ~40% OSM
derivation, which is the single most important fact for correctly understanding the
relationship.**

⚠️ **The governance dispute I have reported as a dispute rather than resolving it.** **The
$300,000 membership figure and the 20% ID churn claim come from a source explicitly
arguing one side of an OGC standardization fight, and I could not corroborate the churn
number independently.** **I've included it because if it's accurate it directly undermines
GERS's core value proposition and you'd want to check before building on it** — ⚠️ **but
it is a claim to verify, not a fact I'm asserting.** **The existence and shape of the
disagreement is not in doubt.**

**§14 → `gis-spatial-analysis-remote-sensing-and-privacy` I have treated as an engineering obligation rather than a legal footnote.** ⚠️ **The
result that a handful of spatiotemporal points uniquely identifies individuals is
foundational and well-replicated**, and it means **"we anonymized it" is not a defensible
claim for trajectory data without genuine aggregation or formal privacy guarantees.**
