---
id: skill-dora-metrics-2024-benchmarks-816dddc4e1
purpose: dora metrics 2024 benchmarks
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-ai-coding-governance-in-agile-64833efdea"]
links: ["skill-owasp-samm-integration-7057e84fe8"]
---

## DORA Metrics (2024 Benchmarks)

The four key DevOps metrics from the DORA research program (*Accelerate*, Forsgren, Humble, Kim, 2018):

| Metric | Elite | High | Medium | Low |
|---|---|---|---|---|
| **Deployment Frequency** | Multiple per day | Daily to weekly | Weekly to monthly | Monthly to 6 months |
| **Lead Time for Changes** | < 1 day | 1 day – 1 week | 1 week – 1 month | 1–6 months |
| **Change Failure Rate** | 0–5% | ~10% | ~15% | 16–30%+ |
| **Failed Deployment Recovery Time** | < 1 hour | < 1 day | < 1 day | 1 week – 1 month |

**Important nuances:**
- Performance tiers are derived via cluster analysis from annual survey data — they shift year to year, not fixed benchmarks
- DORA renamed MTTR to "Failed Deployment Recovery Time" (FDRT) in recent releases
- The 2024 report found AI tools boost individual productivity but correlate with **worsened** software delivery performance at the team level — second consecutive year of this finding
- 19% of respondents reached Elite, 22% High in 2024

**Instrument in CI/CD:** Deployment Frequency via pipeline run data; Lead Time via commit-to-production timestamps; Change Failure Rate by tagging failed deployments; FDRT by measuring incident creation to resolution.

---
