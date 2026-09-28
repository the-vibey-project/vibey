---
id: skill-15-anti-patterns-b9b816ab4e
purpose: 15 anti patterns
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-reference/SKILL.md
requires: []
links: ["skill-16-numbers-and-limits-1898cb6bf7"]
---

## §15. Anti-Patterns

| Anti-pattern | Why |
|---|---|
| **Disabling SELinux** | ⚠️ **Fix the label. Two commands** (§9.2 → `sysadmin-packages-boot-and-hardening`) |
| Editing vendor unit files in `/usr/lib` | ⚠️ **Overwritten on update. Use `systemctl edit`** (§4.1 → `sysadmin-systemd-storage-and-networking`) |
| Forgetting `daemon-reload` | Your edit isn't loaded (§4.1 → `sysadmin-systemd-storage-and-networking`) |
| `Requires=` without `After=` | ⚠️ **Starts in parallel; fails** (§4.2 → `sysadmin-systemd-storage-and-networking`) |
| `/dev/sdX` in fstab | ⚠️ **Names aren't stable. Use UUID** (§5.3 → `sysadmin-systemd-storage-and-networking`) |
| Rebooting without `mount -a` | ⚠️ **Stranded at emergency shell** (§5.3 → `sysadmin-systemd-storage-and-networking`) |
| `kill -9` first | Skips flush and cleanup (§3 → `sysadmin-filesystem-permissions-and-processes`) |
| Panicking about low "free" memory | ⚠️ **Read `available`. Cache is doing its job** (§10.2 → `sysadmin-observability-troubleshooting-and-operations`) |
| Enabling a firewall before allowing SSH | ⚠️ **Lockout** (§6.3 → `sysadmin-systemd-storage-and-networking`) |
| Changing firewall rules with no rollback timer | Same (§6.3 → `sysadmin-systemd-storage-and-networking`) |
| Password SSH auth | ⚠️ **Keys only is the biggest single win** (§9.4 → `sysadmin-packages-boot-and-hardening`) |
| Reloading sshd without `sshd -t` | Console trip (§9.4 → `sysadmin-packages-boot-and-hardening`) |
| `net.ipv4.tcp_tw_recycle` | ⚠️ **Removed from the kernel; broke NAT clients** (§6.4 → `sysadmin-systemd-storage-and-networking`) |
| Ignoring `.rpmnew`/`.dpkg-dist` | ⚠️ **Running old config plus a file you never read** (§7 → `sysadmin-packages-boot-and-hardening`) |
| Using `strace` on a hot production process | ⚠️ **ptrace stops it on every syscall** (§10.4 → `sysadmin-observability-troubleshooting-and-operations`) |
| Treating LVM snapshots as backups | They fill and break (§5.2 → `sysadmin-systemd-storage-and-networking`) |
| Untested backups | ⚠️ **Not backups** (§14 → `sysadmin-observability-troubleshooting-and-operations`) |
| File-copying a running database | ⚠️ **Corrupt restore** (§14 → `sysadmin-observability-troubleshooting-and-operations`) |
| `--privileged` containers | Kernel is shared (§12 → `sysadmin-observability-troubleshooting-and-operations`) |
| Alerting on CPU% instead of symptoms | Noise, then ignored alerts (§10.5 → `sysadmin-observability-troubleshooting-and-operations`) |
| Manual fixes with config management running | ⚠️ **Reverted in 30 minutes** (§11.2 → `sysadmin-observability-troubleshooting-and-operations`) |
| Theorizing before asking "what changed?" | ⚠️ **The highest-yield question** (§11.1 → `sysadmin-observability-troubleshooting-and-operations`) |
| Volatile journal on a production box | ⚠️ **No logs from the crash** (§4.4 → `sysadmin-systemd-storage-and-networking`) |
| Running as root because it's easier | Capabilities and systemd sandboxing exist (§2.2 → `sysadmin-filesystem-permissions-and-processes`, §4.3 → `sysadmin-systemd-storage-and-networking`) |
| `ifconfig`/`netstat` muscle memory | Deprecated; `ip`/`ss` show more (§6.1 → `sysadmin-systemd-storage-and-networking`) |

---
