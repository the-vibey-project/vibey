---
id: skill-15-reliability-regions-and-slas-c10ecd7848
purpose: 15 reliability regions and slas
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-cost-reliability-iac-lock-in-and-migration/SKILL.md
requires: ["skill-14-cost-mechanics-a7cbc3e929"]
links: ["skill-16-infrastructure-as-code-4224de5a41"]
---

## §15. Reliability, Regions and SLAs

```
Region        geographic area, ⚠️ independent failure domain
AZ / Zone     ⚠️ isolated DC(s) within a region — separate power, cooling, network
Multi-AZ      ⚠️ THE baseline for production. Cheap insurance, small complexity
Multi-region  ⚠️ expensive, complex, and needed far less often than proposed
```
**⚠️ Design principle**: **assume every individual component fails.** **Health checks,
retries with exponential backoff and jitter, circuit breakers, timeouts on every call,
graceful degradation, and idempotent operations.**
**⚠️ SLAs are refunds, not guarantees.** ⚠️ **A 99.99% SLA does not mean you get 99.99% —
it means you get a service credit worth a small fraction of your bill if you don't.**
**Your composite availability is the product of your dependencies', and it is always lower
than any single component's.**
**⚠️ The real failure modes are correlated ones**: **a regional control-plane outage, a bad
config push, an expired certificate, a DNS mistake, or a dependency on a single global
service.** ⚠️ **Multi-AZ protects against a datacentre; it does not protect against a
control-plane failure or your own bad deploy** — **and historically, control-plane and
config-push failures have caused more large outages than facility failures.**
**⚠️ Test failover, or you don't have failover** (see an IT infrastructure reference §13).

---
