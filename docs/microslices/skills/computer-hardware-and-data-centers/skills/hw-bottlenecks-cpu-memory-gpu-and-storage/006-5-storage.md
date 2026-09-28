---
id: skill-5-storage-eb804f9ff8
purpose: 5 storage
source: src/vibey_tools/skills/plugins/computer-hardware-and-data-centers/skills/hw-bottlenecks-cpu-memory-gpu-and-storage/SKILL.md
requires: ["skill-4-gpus-and-accelerators-74f38901dd"]
links: []
---

## §5. Storage

```
⚠️ NAND SSD  (see a semiconductor reference §8) ⚠️ wear-out is
   intrinsic, hence TBW ratings and wear levelling
   ⚠️ SLC/TLC/QLC trade density against endurance and sustained
   write speed — ⚠️ note that consumer drives use an SLC CACHE
   and slow dramatically once it's exhausted, which is why
   short benchmarks flatter them
   ⚠️ DRAM cache vs DRAM-less · ⚠️ TRIM · write amplification
⚠️ INTERFACES  SATA → NVMe over PCIe. ⚠️ NVMe's real advantage is
   the queue model and latency, not just bandwidth
⚠️ HDD  ⚠️ still unbeaten on cost per terabyte at capacity, hence
   its persistence in bulk and archival tiers
⚠️ ⚠️ RAID IS NOT BACKUP. It protects against DRIVE failure, not
   against deletion, corruption, ransomware, fire or theft
   ⚠️ RAID 5 rebuild on large modern drives carries real risk of a
   second failure or unrecoverable read error during the rebuild
⚠️ THE 3-2-1 RULE  three copies, two media, one offsite
⚠️ FILESYSTEMS  ⚠️ ZFS and Btrfs checksum data and can detect and
   repair silent corruption; conventional filesystems cannot
```
