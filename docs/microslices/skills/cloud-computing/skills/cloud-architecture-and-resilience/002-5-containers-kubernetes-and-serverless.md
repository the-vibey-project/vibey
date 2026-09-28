---
id: skill-5-containers-kubernetes-and-serverless-9a666d0878
purpose: 5 containers kubernetes and serverless
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-architecture-and-resilience/SKILL.md
requires: ["skill-4-architecture-33edec0c7e"]
links: ["skill-6-resilience-and-the-2025-lessons-c861a8eb2a"]
---

## §5. Containers, Kubernetes, and Serverless

**Containers** package the app and its dependencies. **[DURABLE] The genuine win is
environment parity** — the same artifact runs everywhere.

**Kubernetes** is the orchestration standard and **⚠️ the most over-adopted technology in
this document.** It is genuinely excellent at multi-team, multi-service platforms at scale;
it is genuinely a poor fit for a team of five running three services. **The honest test:
do you have the operational capacity to run it, or are you adopting a platform team's
problem without the platform team?** Managed control planes (EKS/AKS/GKE) remove some but
not most of the burden.

**The lighter options are underrated**: **Cloud Run, ECS/Fargate, Container Apps,
App Runner, Fly.io** — containers without cluster operations. **For most workloads this is
the right answer**, and the fact that it's less impressive is not an argument.

**Serverless / FaaS** — event-driven, scale-to-zero, per-invocation billing.
**⚠️ The constraints are design forces, not details**: cold starts, execution time limits,
statelessness, **local development friction**, vendor coupling in the event model, and
**⚠️ cost that inverts at sustained high volume** — serverless is cheap when idle and
expensive when busy, which is exactly backwards from a VM. **Model both curves before
committing.**

---
