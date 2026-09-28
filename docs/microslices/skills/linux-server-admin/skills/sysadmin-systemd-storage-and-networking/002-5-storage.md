---
id: skill-5-storage-94c4fefc3f
purpose: 5 storage
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-systemd-storage-and-networking/SKILL.md
requires: ["skill-4-systemd-d8c2c67378"]
links: ["skill-6-networking-bda8ff045c"]
---

## §5. Storage

### 5.1 The stack
```
Physical device → partition → [LUKS] → [LVM PV → VG → LV] → [RAID] → filesystem → mount
```
```
lsblk -f                     ⚠️ the best single overview: tree + FS + UUID + mountpoint
blkid                        UUIDs and types
df -h · df -i                ⚠️ run BOTH — inodes exhaust independently
du -xh --max-depth=1 /path   ⚠️ -x stops it crossing filesystems
ncdu -x /                    interactive
```

### 5.2 LVM
```
pvcreate /dev/sdb1 · vgcreate vg0 /dev/sdb1 · lvcreate -L 50G -n data vg0
lvextend -L +20G -r /dev/vg0/data      ⚠️ -r resizes the filesystem too
vgs · lvs · pvs                        status
lvcreate -s -L 5G -n snap /dev/vg0/data   snapshot
```
**⚠️ LVM snapshots are copy-on-write and will fill up and break** if the origin churns
past the snapshot size. **They are a backup *staging* mechanism, not a backup.**

### 5.3 Filesystems
| FS | Use | ⚠️ Notes |
|---|---|---|
| **ext4** | Default, boring, reliable | ⚠️ **Cannot shrink while mounted** |
| **XFS** | RHEL default, large files, parallel I/O | ⚠️ **CANNOT SHRINK AT ALL. Ever.** |
| **btrfs** | Snapshots, checksums, subvolumes | ⚠️ **Avoid RAID5/6 — long-standing write hole** |
| **ZFS** | Checksums, snapshots, send/recv, ARC | ⚠️ **Out-of-tree licensing; wants RAM and ECC** |

**⚠️ `/etc/fstab` mistakes strand a box at boot.** Use **UUID= or LABEL=**, never
`/dev/sdX` (⚠️ **device names are not stable across reboots**). **Add `nofail` to
non-critical mounts.** ⚠️ **Always `mount -a` after editing fstab and before rebooting —
this one habit prevents a genuine class of console-access-required incidents.**

**Useful mount options**: `noatime` (⚠️ **reduces write amplification; `relatime` is the
modern default and usually fine**), `nodev,nosuid,noexec` on data mounts, `discard` vs
periodic `fstrim.timer` (⚠️ **prefer the timer; inline discard can hurt latency**).

### 5.4 I/O
`iostat -xz 1` — ⚠️ **`%util` near 100% means the device is busy, but for SSDs and arrays
that does NOT mean saturated** (they handle parallel requests). **Look at `await`,
`aqu-sz` and throughput instead.** `iotop`, `biolatency`/`biosnoop` (§10.4 → `sysadmin-observability-troubleshooting-and-operations`).
**Schedulers**: `cat /sys/block/sda/queue/scheduler` — ⚠️ **`none`/`mq-deadline` for NVMe,
`bfq` for desktop-ish latency, `mq-deadline` for spinning rust.**

---
