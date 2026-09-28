---
id: skill-12-multi-cloud-and-lock-in-45b76b10cb
purpose: 12 multi cloud and lock in
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-migration-sovereignty-and-ai-workloads/SKILL.md
requires: ["skill-11-sovereignty-the-eu-data-act-and-egress-2a3eecc79a"]
links: ["skill-13-ai-workloads-8cb59c9637"]
---

## §12. Multi-Cloud and Lock-In

**[CONTESTED, and worth stating both cases properly.]**

**⚠️ Multi-cloud reported adoption is high — around 87% by one 2026 count — but the term
covers three very different things**, and conflating them causes most of the confusion:

| Meaning | Reality |
|---|---|
| **Different workloads on different clouds** | ⚠️ **This is what most "multi-cloud" actually is.** Common, sensible, often the residue of acquisitions |
| **The same workload portable across clouds** | Expensive. Constrains you to the lowest common denominator |
| **The same workload running actively on several** | Rare, genuinely hard, occasionally justified |

**The case for**: negotiating leverage, regulatory requirement, resilience against
provider failure (§6 → `cloud-architecture-and-resilience`), best-of-breed service selection, avoiding concentration risk.
**The case against**: **you multiply operational surface, split your team's expertise,
forgo deep managed services, lose volume discounts, and pay inter-cloud egress** — and the
2025 outages showed that **cross-provider failover is much harder than owning it is.**

**[DURABLE] The pragmatic position most practitioners land on**: **develop against open
standards and abstract where it's cheap** — Kubernetes, OpenTelemetry, Terraform,
Postgres-compatible databases, S3-compatible object storage. **If a provider offers a
proprietary service with genuine business value, use it — but understand the trade-off
explicitly** and document the exit path. **⚠️ The worst outcome is accidental lock-in: you
paid the abstraction cost, and you're still locked in via IAM, data formats, and
operational habit.**

**[VERSIONED] And note the regulatory shift**: from January 2027 the EU removes the
*financial* barrier to switching (§11.2) — **which makes the technical and contractual
lock-in the whole of the problem** rather than one part of it.

---
