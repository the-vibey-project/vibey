---
id: skill-5-networking-d0d3745678
purpose: 5 networking
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-networking-compute-containers-and-serverless/SKILL.md
requires: []
links: ["skill-6-compute-ebfbe0e368"]
---

## §5. Networking

```
                AWS              Azure            GCP
Virtual net     VPC              VNet             ⚠️ VPC (GLOBAL, not regional)
Subnets         ⚠️ AZ-scoped      regional         ⚠️ regional
Peering         VPC Peering      VNet Peering     VPC Peering
Hub/transit     Transit Gateway  vWAN / hub-spoke  Network Connectivity Center
Private access  PrivateLink      Private Link      Private Service Connect
On-prem         Direct Connect   ExpressRoute      Cloud Interconnect
LB              ALB/NLB          Azure LB/App GW   ⚠️ Global LB (anycast, single IP)
DNS             Route 53         Azure DNS         Cloud DNS
```
> **⚠️ GOTCHA — GCP's VPC is global and this is a real architectural difference, not a
> marketing point.** ⚠️ **A single GCP VPC spans regions with subnets in each; AWS and
> Azure networks are regional and multi-region requires explicit peering or transit.**
> **GCP's global load balancer similarly gives you one anycast IP worldwide.** ⚠️ **For
> genuinely global applications this meaningfully reduces architectural complexity, and
> it's GCP's strongest structural advantage after BigQuery.**

**⚠️ Private connectivity to managed services is the pattern to internalize**: **PrivateLink
/ Private Link / Private Service Connect keep traffic off the public internet and are
increasingly a compliance requirement.**
**⚠️ NAT gateways are a classic cost trap** — **they charge per hour AND per GB processed,
and a chatty workload egressing through NAT can cost more in NAT processing than in the
transfer itself** (§14 → `hyperscaler-cost-reliability-iac-lock-in-and-migration`).

---
