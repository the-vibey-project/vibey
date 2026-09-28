---
id: skill-14-cost-mechanics-a7cbc3e929
purpose: 14 cost mechanics
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-cost-reliability-iac-lock-in-and-migration/SKILL.md
requires: []
links: ["skill-15-reliability-regions-and-slas-c10ecd7848"]
---

## §14. ⚠️ Cost Mechanics

**⚠️ Compute is almost never the surprise. These are:**
```
1. ⚠️ DATA TRANSFER — egress to internet, cross-region, cross-AZ, NAT processing.
   ⚠️ Ingress is free everywhere; egress is billed everywhere (§21.1)
2. ⚠️ IDLE PROVISIONED RESOURCES — unattached disks, idle load balancers,
   forgotten dev environments, over-provisioned databases, ⚠️ and unattached
   public IPv4 addresses, which AWS now charges hourly for
3. ⚠️ PER-REQUEST CHARGES — API calls, object operations, function invocations,
   ⚠️ and BigQuery bytes scanned. Individually trivial, collectively enormous
4. ⚠️ LOG AND METRIC INGESTION — often the second-largest line after compute
5. ⚠️ UNUSED COMMITMENTS — reservations bought for capacity you no longer run
6. ⚠️ SUPPORT PLANS — a percentage of spend, and it scales with your bill
```
**⚠️ The discipline (FinOps) that actually works:**
- ⚠️ **Tag/label everything and enforce it by policy** — **unattributable spend never gets
  cleaned up, because nobody owns it.**
- **Budgets and anomaly alerts** — ⚠️ **an alert at 50% of monthly budget on day 8 is what
  catches a runaway job before it costs five figures.**
- ⚠️ **Right-size before you commit.** **Buying a three-year reservation for an
  over-provisioned instance locks in the waste.**
- **Lifecycle policies on storage; TTLs on logs.**
- ⚠️ **Kill non-prod outside working hours** — **often 60–70% of non-prod cost, and it's
  the easiest large saving available.**
- ⚠️ **Showback/chargeback changes behaviour more than any technical control**, because it
  puts the cost in front of the team creating it.
> **⚠️ GOTCHA — cross-AZ traffic is billed on AWS and it catches people building
> "highly available" architectures.** ⚠️ **A chatty microservice mesh spread across three
> AZs pays per GB in both directions for internal traffic**, and **the same architecture
> that improves availability can multiply the network bill.** **Zone-aware routing helps;
> knowing it exists helps more.**

---
