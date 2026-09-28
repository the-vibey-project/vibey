---
id: skill-25-quick-reference-e7e814c791
purpose: 25 quick reference
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-reference/SKILL.md
requires: ["skill-24-resources-4326d8d739"]
links: ["skill-26-method-f82251813d"]
---

## §25. Quick Reference

### 25.1 Picker
| Question | Answer |
|---|---|
| Which cloud? | ⚠️ **Existing agreements + team skills, unless §1 → `hyperscaler-framing-responsibility-identity-and-hierarchy`'s exceptions apply** |
| Large-scale analytics? | ⚠️ **BigQuery is the strongest argument for GCP** (§11 → `hyperscaler-storage-databases-analytics-and-observability`) |
| Windows/AD-heavy estate? | ⚠️ **Azure, and it's not close** (§1 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Broadest service catalogue? | AWS (§1 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Kubernetes at scale? | ⚠️ **GKE** (§7 → `hyperscaler-networking-compute-containers-and-serverless`) |
| Do I need Kubernetes? | ⚠️ **Probably not below many-teams scale** (§7 → `hyperscaler-networking-compute-containers-and-serverless`) |
| I have a Dockerfile and want it live | ⚠️ **Cloud Run / Container Apps / App Runner** (§8 → `hyperscaler-networking-compute-containers-and-serverless`) |
| Environment separation? | ⚠️ **Separate accounts / subscriptions / projects** (§4 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| How do I avoid static credentials? | ⚠️ **Roles, managed identities, workload identity federation** (§3 → `hyperscaler-framing-responsibility-identity-and-hierarchy`) |
| Why is the bill high? | ⚠️ **Transfer, idle resources, log ingestion — not compute** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Cheapest easy saving? | ⚠️ **Kill non-prod overnight; move to ARM; right-size** (§6 → `hyperscaler-networking-compute-containers-and-serverless`, §14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Multi-region? | ⚠️ **Only after multi-AZ is solid AND failover is tested** (§15 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Multi-cloud? | ⚠️ **Best-of-breed per workload, or leverage. Not resilience** (§17 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`) |
| Can I leave without paying egress? | ⚠️ **Narrow full-exit terms today; EU ban Jan 2027** (§21.1) |

### 25.2 New-environment checklist
- [ ] ⚠️ **Separate account/subscription/project per environment** (§4 → `hyperscaler-framing-responsibility-identity-and-hierarchy`)
- [ ] ⚠️ **Org-level guardrails: SCPs / Azure Policy / Org Policy** (§4 → `hyperscaler-framing-responsibility-identity-and-hierarchy`)
- [ ] ⚠️ **Audit logging on, org-wide, written where operators can't alter it** (§13 → `hyperscaler-storage-databases-analytics-and-observability`)
- [ ] ⚠️ **No static keys — roles / managed identities / federation** (§3 → `hyperscaler-framing-responsibility-identity-and-hierarchy`)
- [ ] MFA (phishing-resistant) on all human production access (§3 → `hyperscaler-framing-responsibility-identity-and-hierarchy`)
- [ ] ⚠️ **Tagging enforced by policy from day one** (§4 → `hyperscaler-framing-responsibility-identity-and-hierarchy`, §14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`)
- [ ] ⚠️ **Budgets and anomaly alerts before anything is deployed** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`)
- [ ] IaC with remote locked state; state treated as secret (§16 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`)
- [ ] Multi-AZ for anything production (§15 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`)
- [ ] ⚠️ **Private endpoints for managed services** (§5 → `hyperscaler-networking-compute-containers-and-serverless`)
- [ ] Storage lifecycle policies and log TTLs (§9 → `hyperscaler-storage-databases-analytics-and-observability`, §14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`)
- [ ] ⚠️ **Know your egress paths before the architecture is fixed** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`, §21.1)

---
