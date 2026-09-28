---
id: skill-4-architecture-33edec0c7e
purpose: 4 architecture
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-architecture-and-resilience/SKILL.md
requires: []
links: ["skill-5-containers-kubernetes-and-serverless-9a666d0878"]
---

## §4. Architecture

**[DURABLE] The Well-Architected framing is genuinely useful, and the six pillars are
consistent across providers** (AWS's naming; Azure and Google have near-equivalents):
**Operational excellence, Security, Reliability, Performance efficiency, Cost
optimization, Sustainability.**

**⚠️ The pillars conflict, and that's the point.** Reliability costs money. Security costs
latency. Cost optimization costs resilience. **A framework that told you they were all
compatible would be useless — its value is in forcing the trade-off into the open.**

**[DURABLE] The principles that carry the most weight:**
- **Design for failure.** Everything fails. Assume it (§6).
- **Loose coupling** — queues and events between components so one failure doesn't
  propagate synchronously.
- **Statelessness at the compute tier** so instances are disposable.
- **⚠️ Immutable infrastructure** — replace rather than patch. **This single practice
  eliminates configuration drift**, which is the root cause of an enormous share of
  incidents.
- **Everything as code** — infrastructure, policy, pipelines. Reviewable, versioned,
  reproducible.
- **Automate everything you'd otherwise do at 3am.**
- **Right-size continuously**, not once at launch.

**Infrastructure as Code**: **Terraform / OpenTofu** (multi-cloud standard),
**Pulumi** (real programming languages), **CloudFormation / ARM / Bicep** (native),
**CDK** (native, in code), **Crossplane** (Kubernetes-native). ⚠️ **State management,
drift detection, and a plan-review discipline matter more than the tool choice.**

---
