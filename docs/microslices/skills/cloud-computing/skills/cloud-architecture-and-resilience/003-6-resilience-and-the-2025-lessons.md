---
id: skill-6-resilience-and-the-2025-lessons-c861a8eb2a
purpose: 6 resilience and the 2025 lessons
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-architecture-and-resilience/SKILL.md
requires: ["skill-5-containers-kubernetes-and-serverless-9a666d0878"]
links: []
---

## §6. Resilience — and the 2025 Lessons

**[VERSIONED in the specifics, DURABLE in the lesson. This section is the most important
practical material in the document.]**

### 6.1 What happened

**October–November 2025 delivered three object lessons within weeks:**

- **20 October 2025 — AWS us-east-1**, roughly **14–15 hours**. Root cause: **a latent race
  condition in DynamoDB's DNS management system** that **wiped out DNS records for critical
  endpoints**, cascading into failures across dozens of AWS services and the long tail of
  applications depending on them.
- **29 October 2025 — Azure**, tied to **Azure Front Door** (its CDN and routing layer)
  and reported as involving global identity management, degrading a broad set of
  Azure-fronted services.
- **18 November 2025 — Cloudflare**: a **Bot Management configuration change doubled the
  size of a feature file, exceeding a hard-coded limit in the traffic proxy**, crashing
  and restarting processes across the global network. Widespread 5xx errors across major
  services. ⚠️ **For two hours Cloudflare's own engineers believed they were under
  DDoS attack** — the wave pattern looked like one — and only identified it by correlating
  with their rollout timing.

### 6.2 What it actually taught

> **⚠️ GOTCHA — the lesson that cost the most money: many engineers had done everything
> "right."** They deployed across multiple availability zones, implemented health checks,
> and followed the Well-Architected Framework. **None of it mattered when the region
> failed.**
>
> **The durable principle: the failure domain of a cloud service is almost always larger
> than the region boundary your architecture diagram implies.**

**The specific structural findings worth carrying:**
- **⚠️ Multi-AZ is not multi-region.** AZ redundancy protects against a datacenter
  failure, not a regional control-plane failure.
- **⚠️ us-east-1 is a global single point of failure**, not merely a region. It is AWS's
  oldest, largest, and usually cheapest region, attracting a disproportionate share of
  workloads — one analysis put it at **~69%** of AWS usage and another measured
  **44%+ of AWS requests**. **Certain global operations (parts of IAM, Route 53,
  global-service control operations) are anchored there.** Audit whether your failover
  path silently routes through it.
- **⚠️ Control-plane dependencies are the hidden coupling.** Many organizations with
  multi-region deployments still failed because their **databases, queues, or functions**
  remained single-region.
- **⚠️ The supporting cast takes you down, not the primary infrastructure.** As one
  analysis of the 2025 incidents put it: what took organizations down **wasn't their
  primary infrastructure — it was the supporting mechanisms.** When Docker Hub went
  offline, teams couldn't pull containers; **third-party monitoring and alerting failed
  because it sat behind Cloudflare.**
- **⚠️ Shared bottleneck layers.** DNS, CDN, identity, and security have become chokepoints
  where a single misconfiguration disrupts huge portions of the internet.
- **The common pattern across all three: a subtle defect in one subsystem triggering
  global cascading failure** — and the diagnosis offered by practitioners is not "human
  error" but **immature blast-radius modelling**: teams push changes without understanding
  their dependency surface.

### 6.3 What to actually do

**[DURABLE] In order of value per unit of effort:**
1. **Map your real dependency graph**, including SaaS tools and their underlying
   providers. **⚠️ If your team uses Jira, you have an AWS dependency** — treat those as
   Tier-1 dependencies in BCP/DR planning.
2. **Define RTO and RPO per workload**, and be honest that not everything needs the same
   ones.
3. **Design degraded modes.** ⚠️ **Read-only from a standby, feature toggles disabling
   non-critical paths, and graceful degradation beat a binary up/down** — and they're far
   cheaper than full active-active.
4. **Harden DNS**: dual providers with health checks, sensible TTLs, regional endpoints,
   and **no hidden dependency on one region for control traffic.**
5. **Decouple control plane from data plane** — CI/CD, IaC state, artifact registries and
   runbooks must stay reachable when your primary provider is down.
6. **Choose replication mode per workload deliberately** — async, sync/quorum, or log
   shipping, with an RPO per domain (orders ≈ 0, analytics tolerates minutes).
7. **Application-level resilience**: timeouts everywhere, exponential backoff with jitter,
   circuit breakers.
8. **⚠️ Test the failover.** An untested runbook is a hypothesis. **Game days and chaos
   engineering exist because the failover path is itself a system that can be broken.**
9. **The framing to aim for**: when the provider fails, you want to be asking **"should we
   fail over?"** against agreed parameters — **not "can we?"**

**⚠️ And be honest about the cost.** Multi-region roughly doubles infrastructure cost and
substantially increases complexity. **Single-region is a legitimate choice for
non-critical workloads with clear stakeholder expectations** — what's not legitimate is
making it by accident.
