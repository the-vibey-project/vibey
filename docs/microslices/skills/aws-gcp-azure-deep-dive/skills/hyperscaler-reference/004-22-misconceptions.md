---
id: skill-22-misconceptions-0fcd67b324
purpose: 22 misconceptions
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-reference/SKILL.md
requires: ["skill-21-what-moved-verified-august-2026-88c6f1660d"]
links: ["skill-23-numbers-09cc6570a0"]
---

## §22. Misconceptions

| Misconception | Correction |
|---|---|
| The clouds are broadly interchangeable | ⚠️ **IAM, hierarchy and networking differ deeply** (§1 → `hyperscaler-framing-responsibility-identity-and-hierarchy`, §3 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Comparison matrices tell you which to pick | ⚠️ **Existing agreements and team skills usually dominate** (§1 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Cloud is cheaper than on-prem | ⚠️ **For variable workloads. Steady high volume often isn't** (§18 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Lift-and-shift delivers cloud savings | ⚠️ **Datacentre architecture at cloud prices** (§18 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Entra Global Admin can manage Azure resources | ⚠️ **Different authorization systems** (§3.2 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| An IAM Allow means the permission works | ⚠️ **It's an intersection, and any Deny wins** (§3.1 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Project-level policy can restrict an inherited GCP role | ⚠️ **Inheritance is additive** (§3.3 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Tags are an isolation boundary | ⚠️ **They're a convention. Use accounts/subs/projects** (§4 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| S3 is eventually consistent | ⚠️ **Strongly consistent since 2020** (§9 → `hyperscaler-storage-databases-analytics-and-observability`) |
| Serverless is always cheaper | ⚠️ **There's a crossover point; steady traffic is dearer** (§8 → `hyperscaler-networking-compute-containers-and-serverless`) |
| You need Kubernetes | ⚠️ **Below organizational scale it's a tax** (§7 → `hyperscaler-networking-compute-containers-and-serverless`) |
| A 99.99% SLA means 99.99% uptime | ⚠️ **It means a service credit if not** (§15 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Multi-AZ protects against outages | ⚠️ **Not control-plane failures or your own bad deploy** (§15 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Multi-cloud improves resilience | ⚠️ **Usually the opposite, with untested failover** (§17 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Compute is the big cost | ⚠️ **Transfer, idle resources and per-request charges** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Internal traffic is free | ⚠️ **Cross-AZ and cross-region are billed** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Egress fees are gone now | ⚠️ **Only for narrow full-exit cases until Jan 2027 in the EU** (§21.1) |
| Google is a distant third | ⚠️ **Reported 82% YoY growth and a $514B backlog** (§21.2) |
| GPU capacity is available on demand | ⚠️ **Constrained; quotas and commitments are real** (§21.2) |

---
