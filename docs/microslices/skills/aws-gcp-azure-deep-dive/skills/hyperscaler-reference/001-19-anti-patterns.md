---
id: skill-19-anti-patterns-758bf8cf72
purpose: 19 anti patterns
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-reference/SKILL.md
requires: []
links: ["skill-20-service-equivalence-f4861e878c"]
---

## §19. Anti-Patterns

```
⚠️ Lift-and-shift and stop — datacentre architecture at cloud prices (§18)
⚠️ One giant account/subscription/project for everything — no blast radius control (§4)
⚠️ Long-lived static access keys instead of roles/managed identities/federation (§3)
⚠️ Broad grants high in the hierarchy "temporarily" (§3.3)
⚠️ Public object storage buckets for internal convenience (§2)
⚠️ Kubernetes for three services (§7)
⚠️ Serverless for steady high-volume traffic (§8)
⚠️ Multi-region before multi-AZ is solid — or before failover is tested (§15)
⚠️ Untagged resources, no budgets, no anomaly alerts (§14)
⚠️ Buying reservations for over-provisioned instances (§14)
⚠️ SELECT * on unpartitioned analytics tables (§11)
⚠️ Console-driven infrastructure with IaC "coming later" (§16)
⚠️ Multi-cloud for resilience with untested failover (§17)
⚠️ Ignoring egress in the architecture, then discovering it in the invoice (§14, §21.1)
⚠️ Treating the SLA as a guarantee (§15)
```

---
