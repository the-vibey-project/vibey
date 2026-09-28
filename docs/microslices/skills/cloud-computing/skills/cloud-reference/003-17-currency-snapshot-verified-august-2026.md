---
id: skill-17-currency-snapshot-verified-august-2026-1ee5929748
purpose: 17 currency snapshot verified august 2026
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-reference/SKILL.md
requires: ["skill-16-contested-questions-e5029064d0"]
links: ["skill-18-the-canon-20375dd3b9"]
---

## §17. Currency Snapshot — verified August 2026

| Thing | Status as of Aug 2026 | Decay risk |
|---|---|---|
| **Market structure** | Q1 2026 cloud infrastructure spend **~$129B, +35% YoY**, ninth consecutive quarter of accelerating YoY growth. Big Three **~60–68%** depending on methodology. ⚠️ **Synergy: AWS 28% / Azure 21% / GCP 14%. Other sources: 30/24–25/13 or 32/23/11** — **cite source and scope** (§2 → `cloud-models-providers-and-primitives`). Azure and GCP growing faster off smaller bases; **Microsoft doesn't break out Azure revenue, only growth rate** | **High** |
| **Capex** | 2026 guidance: **Amazon ~$200B, Microsoft ~$190B, Alphabet ~$180–190B.** Guidance, not actuals | **High** |
| **AI share of cloud spend** | **~19% in 2026, up from ~8% in 2023** | **High** |
| **⚠️ Cloud waste** | **Flexera 2026: 29% of IaaS/PaaS wasted, up from 27% — reversing a five-year decline**, attributed to **AI adoption outpacing tagging/attribution/governance**. n=753. **Managing cloud spend now the #1 priority (84%), above security** | Medium |
| **FinOps adoption** | **FinOps teams ~63%, CCoE ~71%.** ⚠️ **Fewer than half use any one commitment discount per provider.** **AI cost management the top future priority (98%)** and most-wanted skillset. **FOCUS** standardizing cross-provider cost data. Practitioners report **the easy waste is gone** — remaining savings are smaller and harder | Medium |
| **Repatriation** | **~21% of workloads repatriated**, but **new cloud workloads outstrip exits — cloud continues to grow** | Medium |
| **GPU economics** | **GPUs ~18% of spend at AI-forward orgs (up from ~4% in 2023); statically provisioned fleets at 30–40% utilization.** Idle accelerators = fastest-growing waste category | **High** |
| **⚠️ Oct–Nov 2025 outages** | **AWS us-east-1, 20 Oct, ~14–15h** — latent **race condition in DynamoDB's DNS management** wiped DNS records, cascading across dozens of services. **Azure, 29 Oct** — **Azure Front Door** / global identity. **Cloudflare, 18 Nov** — Bot Management config **doubled a feature file past a hard-coded limit**, crashing proxies globally; **engineers spent ~2h believing it was a DDoS**. Common pattern: **subtle single-subsystem defect → global cascade**; diagnosis is **immature blast-radius modelling**, not human error | Low (historical) |
| **us-east-1 concentration** | Reported at **~69% of AWS usage** by one analysis and **44%+ of AWS requests** by another. **Global operations (parts of IAM, Route 53) anchor there** | Medium |
| **⚠️ EU Data Act** | Reg. (EU) 2023/2854. In force 11 Jan 2024. **Switching rights enforceable 12 Sept 2025.** **12 Sept 2026: products released after must have user data accessible by default.** **⚠️ 12 January 2027: all switching charges including egress fees banned outright** — IaaS, PaaS and SaaS, **for every provider serving EU customers**. Transition allows only direct, transparent, pre-agreed cost. Enforcement by **national authorities**, penalties set in **local legislation**. AWS/Azure/Google waived full-exit egress in 2024 (narrower than 2027 requires) | **High** |
| **DMA / sovereignty** | **DMA investigating AWS and Azure as potential gatekeepers**; ⚠️ **analysts flag genuine friction with the Data Act** — conflicting timelines, split enforcement (member states vs. Commission). **3 June 2026: Commission proposed the Cloud and AI Development Act** (Tech Sovereignty Package) to define **graded sovereignty levels** — ⚠️ **not yet passed; details will change** | **High** |
| **Sustainability** | Well-Architected pillar; **>half of orgs have or plan a sustainability initiative including cloud carbon tracking** | Medium |

**Goes stale fastest:** §2 → `cloud-models-providers-and-primitives`, §13 → `cloud-migration-sovereignty-and-ai-workloads`, and the market figures throughout. **Essentially never
stale:** §1 → `cloud-models-providers-and-primitives`, §4 → `cloud-architecture-and-resilience`, §6.2 → `cloud-architecture-and-resilience`–6.3's principles, §8 → `cloud-cost-security-and-operations`, §9 → `cloud-cost-security-and-operations`, §10 → `cloud-migration-sovereignty-and-ai-workloads`, §15.

---
