---
id: skill-1-filesystem-and-files-ef1b0786c7
purpose: 1 filesystem and files
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-filesystem-permissions-and-processes/SKILL.md
requires: ["skill-0-routing-b40ef2d208"]
links: ["skill-2-users-permissions-capabilities-4d0880b5e5"]
---

## §1. Filesystem and Files

### 1.1 Layout (FHS)
```
/etc      configuration          ⚠️ this is what you back up
/var      variable data — logs, spool, databases, containers
/usr      read-only program data (/usr/bin, /usr/lib, /usr/share)
/opt      third-party packages
/srv      service data
/home     users
/tmp      ⚠️ often tmpfs (RAM), cleared on boot
/run      ⚠️ tmpfs, runtime state, PIDs, sockets — gone on reboot BY DESIGN
/proc     kernel/process interface (virtual)
/sys      kernel object interface (virtual)
/dev      device nodes
/boot     kernel, initramfs, bootloader
```
**⚠️ `/usr` merge**: `/bin`, `/sbin`, `/lib` are symlinks into `/usr` on modern systems.
Stop treating them as distinct.

### 1.2 File semantics that surprise people
**Inodes hold metadata; directory entries map names to inodes.** Consequences:
- **⚠️ Deleting a file with an open descriptor doesn't free the space** — the inode
  survives until the last FD closes. **This is the classic "disk full but `du` shows
  nothing" incident.** Find it with `lsof +L1` or `lsof | grep deleted`, then restart the
  holder or truncate via `/proc/PID/fd/N`.
- **Hard links** share an inode (⚠️ **same filesystem only**); **symlinks** are separate
  inodes containing a path.
- **⚠️ You can exhaust inodes while free space remains** — `df -i`. Common with mail
  spools and small-file caches.
- **`rename(2)` is atomic within a filesystem** — ⚠️ **which is why "write to temp, fsync,
  rename" is the correct way to update a config file safely.**

**⚠️ Durability**: `write()` returns when data is in the page cache, not on disk.
**`fsync()` is what makes it durable**, and **you must also fsync the parent directory**
for the rename to survive a crash. **This is where people lose data.**

### 1.3 Special filesystems worth knowing
```
/proc/PID/{cmdline,environ,fd/,maps,status,limits,cgroup}   ⚠️ per-process truth
/proc/{meminfo,loadavg,mounts,net/,sys/}
/sys/class/net/*/statistics/                                interface counters
/sys/block/*/queue/{scheduler,rotational,nr_requests}
/proc/sys/...  ← the same tree sysctl writes to
```
**⚠️ `/proc/PID/limits` shows the actual limits of a running process** — not what your
shell has, not what the unit file says. **When a limit seems unapplied, check here.**

---
