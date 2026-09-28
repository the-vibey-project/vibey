---
id: skill-storage-redundancy-decision-matrix-a79219fb84
purpose: storage redundancy decision matrix
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-the-four-highest-leverage-decision-clusters-454da6b97d"]
links: ["skill-ai-microsoft-foundry-145aa80e22"]
---

## Storage Redundancy Decision Matrix

| Tier | Durability | Notes |
|---|---|---|
| LRS | 11 nines | Dev/test only; lowest cost |
| ZRS | 12 nines | **Production minimum**; ~25% premium over LRS |
| GRS/GZRS | ~16 nines | Geo-redundant backup |
| RA-GZRS | 16 nines | Business-critical; adds read access to secondary |

**Critical:** archive tier is not supported on ZRS, GZRS, or RA-GZRS — only LRS/GRS/RA-GRS.

**Access tiers:** Hot → Cool (30-day min) → Cold (90-day min) → Archive (180-day min, hours to rehydrate)

**Action:** set lifecycle management policies to auto-tier aging data from day one — this is the primary cost lever.

---
