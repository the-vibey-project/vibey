---
id: skill-1-models-a7ef649f53
purpose: 1 models
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-models-providers-and-primitives/SKILL.md
requires: ["skill-0-routing-021e214561"]
links: ["skill-2-the-provider-landscape-aaf38a3bc3"]
---

## §1. Models

### 1.1 Service models

```
On-prem  →  IaaS  →  CaaS  →  PaaS  →  FaaS  →  SaaS
◄─────────── you manage more        you manage less ───────────►
◄─────────── more control           less operational burden ───►
◄─────────── more lock-in risk?     ⚠️ see §12 — it's not that simple
```

**[DURABLE] The trade-off is real in both directions**, and the common mistake is
optimizing only one end. Managed services cost more per unit and less in engineering time;
raw IaaS is cheaper per unit and you pay for it in people. **⚠️ The comparison people skip
is the fully-loaded one** — a managed database's premium is frequently less than one
engineer's fraction of time keeping a self-hosted one patched, backed up, and monitored.

### 1.2 Deployment models
**Public**, **private**, **hybrid** (⚠️ **the actual state of most large enterprises**,
whatever the strategy deck says), **multi-cloud** (§12 → `cloud-migration-sovereignty-and-ai-workloads`), and **edge**. **Sovereign cloud**
is now a distinct category with regulatory meaning rather than a marketing label (§11 → `cloud-migration-sovereignty-and-ai-workloads`).

### 1.3 The five NIST characteristics
On-demand self-service, broad network access, resource pooling, rapid elasticity,
measured service. **[DURABLE] Dated 2011 and still the cleanest definition** — and
"measured service" is the one that quietly determines your architecture (§7 → `cloud-cost-security-and-operations`).

---
