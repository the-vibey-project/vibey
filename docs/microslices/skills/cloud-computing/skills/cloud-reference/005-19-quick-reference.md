---
id: skill-19-quick-reference-5a6fcfd895
purpose: 19 quick reference
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-reference/SKILL.md
requires: ["skill-18-the-canon-20375dd3b9"]
links: ["skill-20-sources-and-method-c43fb684f6"]
---

## §19. Quick Reference

### 19.1 Design checklist
- [ ] RTO and RPO defined **per workload**, not globally (§6.3 → `cloud-architecture-and-resilience`)
- [ ] **Dependency map including SaaS and their underlying providers** (§6.3 → `cloud-architecture-and-resilience`)
- [ ] ⚠️ Does anything silently depend on a single region — including IAM, DNS, CI/CD, or
      monitoring? (§6.2 → `cloud-architecture-and-resilience`)
- [ ] Degraded mode designed, not just up/down (§6.3 → `cloud-architecture-and-resilience`)
- [ ] Failover **tested**, not documented (§6.3 → `cloud-architecture-and-resilience`)
- [ ] Tagging strategy enforced before spend scales (§7 → `cloud-cost-security-and-operations`)
- [ ] Commitment and spot mix modelled (§7.2 → `cloud-cost-security-and-operations`)
- [ ] Egress and cross-AZ paths deliberate (§11.3 → `cloud-migration-sovereignty-and-ai-workloads`)
- [ ] Workload identity, not long-lived keys (§8 → `cloud-cost-security-and-operations`)
- [ ] Least privilege from deny-all (§8 → `cloud-cost-security-and-operations`)
- [ ] Logging on, retained, and outside the failure domain (§8 → `cloud-cost-security-and-operations`, §9 → `cloud-cost-security-and-operations`)
- [ ] SLOs from user-visible behaviour; alerts on symptoms (§9 → `cloud-cost-security-and-operations`)
- [ ] IaC for everything; no console changes in prod (§4 → `cloud-architecture-and-resilience`)
- [ ] ⚠️ EU contracts reviewed against the **12 Jan 2027** ban (§11.2 → `cloud-migration-sovereignty-and-ai-workloads`)
- [ ] Exit path documented — data formats, APIs, IAM, not just egress cost (§12 → `cloud-migration-sovereignty-and-ai-workloads`)

### 19.2 Numbers worth remembering
- **~29%** of IaaS/PaaS spend wasted (Flexera 2026) — **up, not down**
- **Fewer than half** of orgs use any one commitment discount
- **Spot: 60–90% cheaper** for interruptible work
- **GPUs ~18%** of AI-forward spend; **30–40% utilization** when statically provisioned
- **AI ~19%** of cloud spend, from ~8% in 2023
- **~21%** of workloads repatriated; cloud still growing
- **AWS us-east-1 outage: ~14–15 hours**, October 2025
- **⚠️ 12 January 2027** — EU egress and switching fee ban

### 19.3 Triage
| Symptom | First look |
|---|---|
| Bill jumped and nobody knows why | Untagged resources; egress; a new AI workload (§7 → `cloud-cost-security-and-operations`) |
| Bill high but usage flat | Idle resources, orphaned storage, no commitments (§7.2 → `cloud-cost-security-and-operations`) |
| Outage despite multi-AZ | ⚠️ Regional control-plane dependency (§6.2 → `cloud-architecture-and-resilience`) |
| Failed over but still down | Data tier, CI/CD, or monitoring in the failed region (§6.2 → `cloud-architecture-and-resilience`) |
| Serverless costs more than expected | Sustained volume — the curve inverted (§5 → `cloud-architecture-and-resilience`) |
| Kubernetes consuming the team | You may not need it (§5 → `cloud-architecture-and-resilience`) |
| Cross-AZ charges surprising | Chatty services spanning zones (§11.3 → `cloud-migration-sovereignty-and-ai-workloads`) |
| "We're multi-cloud" but can't fail over | You have workload distribution, not portability (§12 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Compliance auditor unsatisfied despite EU region | ⚠️ Residency ≠ sovereignty (§11.1 → `cloud-migration-sovereignty-and-ai-workloads`) |

---
