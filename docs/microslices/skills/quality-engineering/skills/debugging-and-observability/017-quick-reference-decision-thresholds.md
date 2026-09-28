---
id: skill-quick-reference-decision-thresholds-1b12b8a372
purpose: quick reference decision thresholds
source: src/vibey_tools/skills/plugins/quality-engineering/skills/debugging-and-observability/SKILL.md
requires: ["skill-part-15-observability-2-0-23a0133a38"]
links: ["skill-caveats-on-sources-4a67fc72c3"]
---

## Quick Reference: Decision Thresholds

| Situation | Action |
|-----------|--------|
| Cannot reliably reproduce a bug | Stop fixing; invest in reproduction infrastructure (record/replay, better logging) |
| Burn rate >14.4 on 1-hour window | Page immediately — treat as active incident |
| AI fix touches auth/crypto/input handling/data access | Mandatory human security review regardless of confidence |
| Solo debugging >30–60 minutes | Rubber-duck or pair (Agans' Rule 8) |
| Error rate 1% on 99.9% SLO | That's 10× burn rate — active incident |

---
