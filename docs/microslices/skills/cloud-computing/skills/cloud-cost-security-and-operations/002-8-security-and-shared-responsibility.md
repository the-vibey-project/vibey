---
id: skill-8-security-and-shared-responsibility-2efeb1bbef
purpose: 8 security and shared responsibility
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-cost-security-and-operations/SKILL.md
requires: ["skill-7-cost-engineering-and-finops-47ea9ba516"]
links: ["skill-9-operations-and-observability-097f9fa372"]
---

## §8. Security and Shared Responsibility

**[DURABLE] The shared responsibility model, stated precisely because it's constantly
misread:**

```
                     IaaS        PaaS        SaaS
Data & access     ─ YOU ──────── YOU ──────── YOU ──►  ⚠️ ALWAYS YOU
Application       ─ YOU ──────── YOU ──────── provider
Runtime/OS        ─ YOU ──────── provider ─── provider
Virtualization    ─ provider ─── provider ─── provider
Physical          ─ provider ─── provider ─── provider
```

**⚠️ "Security *of* the cloud" is theirs; "security *in* the cloud" is yours — and the
overwhelming majority of cloud breaches are on the customer side of that line.**

**The recurring failure modes**, roughly by frequency: **public storage buckets**,
**over-permissive IAM** (⚠️ **wildcard policies that were "temporary"**), **long-lived
access keys** (⚠️ **use workload identity/OIDC federation instead — this single change
removes the most common breach vector**), **secrets in code or environment variables**
(use a managed secret store), **unencrypted data**, **open security groups**, **no MFA on
privileged accounts**, **unpatched images**, and **⚠️ no logging, which turns an incident
into an unanswerable question.**

**The practices that matter**: **least privilege, enforced** (start deny-all, add
specifically); **defense in depth**; **zero trust** (⚠️ **network location is not
authorization** — an internal VPC is not a trust boundary); **encryption at rest and in
transit** with **customer-managed keys where it's warranted** (§11 → `cloud-migration-sovereignty-and-ai-workloads`); **network
segmentation and private endpoints**; **policy as code** (Sentinel, OPA, Azure Policy,
SCPs) to make misconfiguration structurally impossible rather than merely discouraged;
and **CSPM/CNAPP tooling** for continuous posture assessment.

**Compliance**: SOC 2, ISO 27001, PCI DSS, HIPAA, FedRAMP, DORA. **⚠️ Provider
certification does not make you compliant** — it means the underlying platform can support
a compliant deployment. The configuration is yours.

---
