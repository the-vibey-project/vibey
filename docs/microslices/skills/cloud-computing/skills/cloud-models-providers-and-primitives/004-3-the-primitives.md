---
id: skill-3-the-primitives-6e343867d6
purpose: 3 the primitives
source: src/vibey_tools/skills/plugins/cloud-computing/skills/cloud-models-providers-and-primitives/SKILL.md
requires: ["skill-2-the-provider-landscape-aaf38a3bc3"]
links: []
---

## §3. The Primitives

**[DURABLE] Every provider has these under different names. Learn the primitive, map the
name.**

**Compute**: VMs (⚠️ **still the majority of cloud spend**), containers (§5 → `cloud-architecture-and-resilience`), serverless
functions, GPU/accelerator instances (§13 → `cloud-migration-sovereignty-and-ai-workloads`), bare metal. **Pricing modes matter more than
instance choice**: on-demand, reserved/committed (1–3 year, **large discounts**), savings
plans, **spot/preemptible** (⚠️ **60–90% cheaper and interruptible — enormously underused
for batch, CI, and fault-tolerant work**), dedicated hosts.

**Storage**, and **⚠️ picking the wrong class is one of the most common cost errors**:

| Type | Use | ⚠️ Watch |
|---|---|---|
| **Object** (S3, Blob, GCS) | The default for almost everything: static assets, data lakes, backups | Request costs at high volume; egress (§11 → `cloud-migration-sovereignty-and-ai-workloads`) |
| **Block** (EBS, Managed Disks) | Filesystem for a VM | ⚠️ **Provisioned, not consumed — you pay for the size you asked for, idle or not** |
| **File** (EFS, Azure Files) | Shared POSIX access | Expensive per GB |
| **Archive** (Glacier, Archive tier) | Long-term retention | ⚠️ **Retrieval time and retrieval cost — and early-deletion fees** |

**⚠️ Lifecycle policies are free money and routinely unconfigured.** Object storage tiering
from hot → cool → archive on an age rule takes minutes to set and runs forever.

**Networking**: VPC/VNet, subnets, security groups/NSGs, load balancers (L4 and L7),
DNS, CDN, private endpoints, peering, transit gateway/hub-spoke, NAT gateways
(⚠️ **a surprisingly large and invisible line item at volume**).

**Identity** — **[DURABLE] the most important primitive and the most commonly
misconfigured** (§8 → `cloud-cost-security-and-operations`): workload identity (⚠️ **use it — long-lived access keys are the
single most common cloud breach vector**), roles and policies, federation, and
**least privilege as an actual practice rather than an aspiration**.

**Managed data services**: relational, NoSQL, cache, search, queues and streams, data
warehouse. **⚠️ Each is a lock-in decision as well as an architecture decision** (§12 → `cloud-migration-sovereignty-and-ai-workloads`).
