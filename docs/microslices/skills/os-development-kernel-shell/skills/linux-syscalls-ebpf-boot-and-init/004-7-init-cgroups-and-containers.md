---
id: skill-7-init-cgroups-and-containers-c7a3caf2e8
purpose: 7 init cgroups and containers
source: src/vibey_tools/skills/plugins/os-development-kernel-shell/skills/linux-syscalls-ebpf-boot-and-init/SKILL.md
requires: ["skill-6-boot-8ee5a95db5"]
links: []
---

## §7. Init, cgroups, and Containers

### 7.1 systemd — like it or not, the reference userland

**[VERSIONED — v258/v259/v260 removed a lot, so check your target.]**

Core model: **units** (`.service`, `.socket`, `.timer`, `.mount`, `.target`, `.slice`,
`.path`, `.device`) with declarative dependencies, socket activation, cgroup-based
resource control, and a journal. PID 1 supervises; `systemd --user` does the same
per-session.

```ini
# /etc/systemd/system/myapp.service — a hardened service, which is the point
[Unit]
Description=My App
After=network-online.target
Wants=network-online.target

[Service]
Type=notify                       # exec | simple | forking | oneshot | notify | idle
ExecStart=/usr/bin/myapp
Restart=on-failure
RestartSec=5s
User=myapp
DynamicUser=yes                   # transient UID, no /etc/passwd entry needed

# Sandboxing — systemd's most underused feature. Check with `systemd-analyze security`
NoNewPrivileges=yes
ProtectSystem=strict              # /usr, /boot, /etc read-only
ProtectHome=yes
PrivateTmp=yes
PrivateDevices=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
RestrictNamespaces=yes
SystemCallFilter=@system-service
SystemCallArchitectures=native
MemoryDenyWriteExecute=yes
StateDirectory=myapp              # → /var/lib/myapp, created with right ownership

[Install]
WantedBy=multi-user.target
```
`systemd-analyze security myapp.service` scores this and tells you what's missing. It is
the cheapest hardening win available on a modern Linux system.

**Recent removals that will break things** [VERSIONED]:
- **v258 removed cgroup v1 entirely** (legacy and hybrid hierarchies). cgroup v2 only.
  Monitoring tools with hardcoded v1 paths break.
- **v258 removed System V runlevel compatibility** (`initctl`, `runlevel`, `telinit`) and
  made OpenSSL the only crypto backend for resolved/importd.
- **v259 deprecated SysV service script support**; **v260 (2026) removed
  `systemd-sysv-generator`, `systemd-rc-local-generator`, and `systemd-sysv-install`.**
  A package still shipping only an LSB init script now silently does nothing.
- **v259 made journald persistent by default** (previously it only wrote to disk if
  `/var/log/journal` existed) and **dropped iptables/libiptc NAT in networkd and nspawn —
  nftables only.**
- v260 raises minimums to kernel 5.10, glibc 2.34, OpenSSL 3.0, Python 3.9.

**[CONTESTED] systemd.** *For:* declarative dependencies, socket activation, correct
process supervision (no more PID files and double-forking), cgroup integration, unified
logging, and the security sandboxing above — all things shell-script init genuinely could
not do reliably. *Against:* scope creep into DNS, NTP, boot, containers, home
directories, and login; a binary log format; tight coupling that makes non-systemd
distros progressively harder to maintain; and a design philosophy that trades Unix
composability for integration. Both sides have shipped working systems for a decade;
this argument will not be resolved by anyone reading this document.

### 7.2 cgroup v2

**[DURABLE] Unified hierarchy** (v1's per-controller hierarchies are gone). Controllers:
`cpu`, `memory`, `io`, `pids`, `cpuset`, `hugetlb`, `rdma`, `misc`.

Key files: `cpu.max` (quota/period), `cpu.weight`, `memory.max` (hard limit → OOM),
**`memory.high`** (throttle + reclaim pressure, no kill — usually what you actually
want), `memory.low` (protection), `io.max`, `pids.max`, and **`*.pressure`** (PSI per
cgroup — the best signal for "this workload is starved").

**The "no internal processes" rule**: a cgroup with children can't have processes of its
own (except the root). This trips up hand-rolled cgroup management constantly.

### 7.3 Namespaces — what a container actually is

| Namespace | Isolates |
|---|---|
| `mnt` | Mount table |
| `pid` | Process IDs (your PID 1 is the container's init) |
| `net` | Network stack: interfaces, routes, netfilter, ports |
| `ipc` | SysV IPC, POSIX message queues |
| `uts` | Hostname, domainname |
| `user` | **UID/GID mapping — the basis of rootless containers** |
| `cgroup` | cgroup root view |
| `time` | Boot/monotonic clock offsets |

**[DURABLE] "Container" is not a kernel object.** It is a process created with
namespace flags, confined by cgroups, restricted by seccomp and an LSM, using
**overlayfs** for the layered image, and usually **pivot_root**ed into it. Docker, Podman,
LXC, and systemd-nspawn are all different userspace assemblies of the same primitives.
Knowing this is the difference between debugging a container and being confused by one.

**User namespaces** are how rootless containers work: root inside maps to an unprivileged
UID outside. They are also historically a **major source of privilege-escalation CVEs**,
because they let unprivileged users reach kernel code paths that previously required root.
Several distros restrict them (`kernel.unprivileged_userns_clone`,
`user.max_user_namespaces`) — a live security-vs-usability tradeoff.
