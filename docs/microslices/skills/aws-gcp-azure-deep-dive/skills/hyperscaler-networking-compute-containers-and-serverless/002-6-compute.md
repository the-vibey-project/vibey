---
id: skill-6-compute-ebfbe0e368
purpose: 6 compute
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-networking-compute-containers-and-serverless/SKILL.md
requires: ["skill-5-networking-d0d3745678"]
links: ["skill-7-containers-and-kubernetes-5a6b6757bd"]
---

## §6. Compute

```
VMs             EC2              Azure VMs        Compute Engine
Autoscale       ASG              VMSS             MIG
Discounted      ⚠️ Savings Plans / RIs   Reserved / Savings Plans   ⚠️ CUDs +
                                                   AUTOMATIC sustained-use discounts
Interruptible   ⚠️ Spot (bid, 2min warning)  Spot VMs   ⚠️ Spot/preemptible (24h cap)
Own silicon     ⚠️ Graviton (ARM)  Cobalt (ARM)    ⚠️ Axion (ARM); TPUs for ML
```
**⚠️ ARM instances are the most reliable easy win available**: **Graviton and equivalents
typically offer materially better price-performance for workloads that recompile
cleanly** — **which is most interpreted and JVM/Go workloads, and container images that
have arm64 variants.** ⚠️ **Check your dependencies for native extensions first.**
**⚠️ Spot/preemptible is genuinely large savings for fault-tolerant work** — **batch, CI,
stateless web behind a queue** — ⚠️ **and catastrophic for anything that can't be
interrupted mid-operation.** **GCP's flavour has a hard 24-hour cap; AWS's runs until
capacity is reclaimed.**
**⚠️ Commitment discounts**: **GCP's sustained-use discounts apply automatically, which is
a real usability advantage; AWS and Azure require you to actively buy commitments, and
unpurchased commitment is the single most common source of overspend on those two.**

---
