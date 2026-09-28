---
id: skill-18-migration-7bae3ab2fc
purpose: 18 migration
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-cost-reliability-iac-lock-in-and-migration/SKILL.md
requires: ["skill-17-lock-in-and-multi-cloud-honestly-c1fde39884"]
links: []
---

## §18. Migration

**⚠️ The 7 Rs**: **rehost (lift-and-shift), replatform, repurchase, refactor, retire,
retain, relocate.**
**⚠️ Retire first.** **A meaningful share of any legacy estate is running things nobody
uses, and migrating them costs money forever.**
**⚠️ Rehost is underrated by architects and correctly rated by people with deadlines** —
**it's fast, low-risk, and gets you a position from which to modernize.** ⚠️ **The failure
mode is stopping there and paying cloud prices for datacentre architecture, which is the
single most common reason cloud migrations don't deliver the promised savings.**
**⚠️ Data migration dominates the timeline**: **bulk transfer appliances (Snowball, Data
Box, Transfer Appliance) for large volumes, then ongoing sync, then cutover.** ⚠️ **The
network is almost always the constraint, and moving petabytes over the internet is not a
plan.**
**⚠️ Repatriation is a real and growing pattern** — **predictable, steady, high-volume
workloads can be genuinely cheaper on owned hardware, and §21.1 → `hyperscaler-reference` removes one of the
barriers to acting on that.** **The cloud's economics favour variable and spiky
workloads; they do not automatically favour everything.**
