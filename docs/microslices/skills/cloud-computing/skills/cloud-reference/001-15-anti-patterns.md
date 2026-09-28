---
id: skill-15-anti-patterns-e8cb9db57b
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-reference/SKILL.md
requires: []
links: ["skill-16-contested-questions-e5029064d0"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| Lift-and-shift everything, then be surprised by the bill | Fixed-capacity design on per-hour billing (§10 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Treating cost as an ops problem | ⚠️ **It's set at design time** (§7 → `cloud-cost-security-and-operations`) |
| No tagging strategy | **You can't allocate what you can't attribute** (§7 → `cloud-cost-security-and-operations`) |
| Ignoring commitment discounts | **Fewer than half of orgs use any** — free money (§7.1 → `cloud-cost-security-and-operations`) |
| Never using spot for interruptible work | 60–90% cheaper (§3 → `cloud-models-providers-and-primitives`, §13 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Provisioned block storage sized for peak, forever | You pay for the ask, not the use (§3 → `cloud-models-providers-and-primitives`) |
| No storage lifecycle policy | Minutes to set, runs forever (§3 → `cloud-models-providers-and-primitives`) |
| **Assuming multi-AZ protects against regional failure** | ⚠️ **The single most expensive lesson of 2025** (§6 → `cloud-architecture-and-resilience`) |
| Multi-region compute with single-region data | The dependency that actually took people down (§6.2 → `cloud-architecture-and-resilience`) |
| Not auditing whether failover routes through us-east-1 | Global services anchor there (§6.2 → `cloud-architecture-and-resilience`) |
| Monitoring and alerting behind the same provider you're monitoring | ⚠️ **Failed exactly this way in 2025** (§6.2 → `cloud-architecture-and-resilience`) |
| CI/CD and IaC state in the region you'd fail over *from* | Can't deploy the fix (§6.3 → `cloud-architecture-and-resilience`) |
| Untested failover runbook | It's a hypothesis, not a plan (§6.3 → `cloud-architecture-and-resilience`) |
| Binary up/down with no degraded mode | Read-only beats down, and costs far less (§6.3 → `cloud-architecture-and-resilience`) |
| Long-lived access keys | ⚠️ **The most common breach vector.** Use workload identity (§8 → `cloud-cost-security-and-operations`) |
| Wildcard IAM policies that were "temporary" | They never are (§8 → `cloud-cost-security-and-operations`) |
| Treating a VPC as a trust boundary | Network location ≠ authorization (§8 → `cloud-cost-security-and-operations`) |
| Assuming provider compliance certification = your compliance | It enables it; config is yours (§8 → `cloud-cost-security-and-operations`) |
| Alerting on CPU instead of user-visible symptoms | Alert fatigue is a reliability problem (§9 → `cloud-cost-security-and-operations`) |
| **Assuming data residency equals sovereignty** | ⚠️ **The "residency illusion"** — CLOUD Act reach (§11.1 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Signing or auto-renewing EU cloud contracts without the 2027 ban in view | ⚠️ **Locks in an outdated fee structure** (§11.2 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Thinking egress fees were the whole of lock-in | APIs, formats and IAM outlast the invoice line (§11.2 → `cloud-migration-sovereignty-and-ai-workloads`, §12 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Chatty service mesh spanning AZs | Cross-AZ transfer is a real, invisible cost (§11.3 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Kubernetes for three services and five engineers | ⚠️ **Adopting a platform team's problem without the platform team** (§5 → `cloud-architecture-and-resilience`) |
| Serverless for sustained high-volume load | The cost curve inverts (§5 → `cloud-architecture-and-resilience`) |
| Multi-cloud portability as a default goal | Lowest common denominator, multiplied ops (§12 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Accidental lock-in | ⚠️ **You paid the abstraction cost and got locked in anyway** (§12 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Statically provisioned GPU fleets | **30–40% utilization; fastest-growing waste** (§13 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Training on on-demand instead of spot with checkpointing | Bursty and interruption-tolerant by nature (§13 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Retrofitting AI cost attribution later | **What the 2026 waste reversal is measuring** (§7.1 → `cloud-cost-security-and-operations`, §13 → `cloud-migration-sovereignty-and-ai-workloads`) |
| Quoting a cloud market share figure without its source | ⚠️ **They differ by 4+ points on methodology** (§2 → `cloud-models-providers-and-primitives`) |

---
