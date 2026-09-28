---
id: skill-cost-optimization-35c90c4630
purpose: cost optimization
source: src/vibey_tools/skills/plugins/azure-cloud-infra/skills/azure-services-catalog/SKILL.md
requires: ["skill-ai-microsoft-foundry-145aa80e22"]
links: ["skill-iac-bicep-vs-terraform-ad7efc1807"]
---

## Cost Optimization

**Layered commitment strategy:**

| Tool | Discount | Best For |
|---|---|---|
| **Reservations** | Up to 72% vs pay-as-you-go | Stable steady-state compute; locked to VM family + region |
| **Savings Plans** | Up to 65% vs pay-as-you-go | Evolving compute; $/hour commitment flexible across families/regions/services |
| **Spot VMs** | Up to 90% vs pay-as-you-go | Fault-tolerant/batch; no SLA, ~30-second eviction notice |

- Reservations apply before Savings Plans when both match
- Stack **Azure Hybrid Benefit** for Windows/SQL licensing on top of Reservations
- Start with 30–60 days of usage data, then use Azure Cost Management recommendations

---
