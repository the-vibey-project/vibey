---
id: skill-9-storage-1db28501f2
purpose: 9 storage
source: src/vibey_tools/skills/plugins/aws-gcp-azure-deep-dive/skills/hyperscaler-storage-databases-analytics-and-observability/SKILL.md
requires: []
links: ["skill-10-databases-1e4a91b933"]
---

## §9. Storage

```
Object     S3               Blob Storage       Cloud Storage
Block      EBS              Managed Disks      Persistent Disk / Hyperdisk
File       EFS / FSx        Azure Files        Filestore
Archive    Glacier tiers    Archive tier       Archive / Coldline
```
**⚠️ Storage classes are the main cost lever**, **and the trap is retrieval**: ⚠️ **archive
tiers are cheap to store and expensive and SLOW to retrieve, with minimum storage
durations that charge you if you delete early.** **Lifecycle policies that move data down
tiers automatically are the right pattern; moving data you actually read is not.**
**⚠️ S3 is strongly consistent** (**since 2020 — older material saying otherwise is
wrong**); **all three now offer strong read-after-write consistency for objects.**
**⚠️ Object storage is not a filesystem.** **No atomic rename, no partial update, and
list operations are expensive at scale** — **which is why "S3 as a database" patterns fall
over.**

---
