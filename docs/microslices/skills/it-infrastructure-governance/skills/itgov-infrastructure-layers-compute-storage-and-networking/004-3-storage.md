---
id: skill-3-storage-6c9137c57a
purpose: 3 storage
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-infrastructure-layers-compute-storage-and-networking/SKILL.md
requires: ["skill-2-compute-and-virtualization-ebf237b364"]
links: ["skill-4-networking-93a6cbf897"]
---

## §3. Storage

```
BLOCK    SAN, iSCSI, FC — ⚠️ raw volumes; databases and VMs
FILE     NAS, SMB/CIFS, NFS — shared filesystems, permissions
OBJECT   S3-compatible — ⚠️ flat namespace, HTTP, massive scale, no POSIX semantics
```
**RAID levels and their real trade-offs** — ⚠️ **RAID is not backup; it protects against
drive failure, not deletion, corruption or ransomware.**
**Tiering, thin provisioning** (⚠️ **and the failure mode: over-provisioning until the
pool fills and everything stops at once**), **snapshots** (⚠️ **which are not backups
either — they usually share the same storage and the same fate**), **replication
(sync vs async)**, **deduplication and compression.**
**⚠️ Storage permissions are where file-level access governance actually lives**, and
**NTFS/share permission interaction, inheritance, and the accumulated mess of nested
groups is a perennial audit finding** (§7 → `itgov-directory-authentication-authorization-and-privileged-access`).

---
