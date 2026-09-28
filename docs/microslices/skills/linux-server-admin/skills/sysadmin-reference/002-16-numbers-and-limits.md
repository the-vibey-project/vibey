---
id: skill-16-numbers-and-limits-1898cb6bf7
purpose: 16 numbers and limits
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-reference/SKILL.md
requires: ["skill-15-anti-patterns-b9b816ab4e"]
links: ["skill-17-lifecycle-dates-verified-august-2026-0f96ff4415"]
---

## §16. Numbers and Limits

```
SIGNALS      TERM 15 · KILL 9 · HUP 1 · INT 2 · QUIT 3 · USR1 10 · USR2 12
PERMISSIONS  r4 w2 x1 · setuid 4000 · setgid 2000 · sticky 1000 · umask 022
EXIT CODES   0 ok · 1 general · 2 misuse · 126 not executable · 127 not found
             ⚠️ 128+N = killed by signal N (137 = SIGKILL, 143 = SIGTERM)
PORTS        <1024 privileged (⚠️ or CAP_NET_BIND_SERVICE)
             22 SSH · 25 SMTP · 53 DNS · 80/443 HTTP(S) · 123 NTP · 3306 MySQL
             5432 Postgres · 6379 Redis · 9090 Prometheus
LIMITS       Default nofile often 1024 ⚠️ (far too low for servers — set 65535)
             PID max default 4194304 on 64-bit
             Ephemeral ports default 32768–60999
LOAD         Divide by core count; ⚠️ includes D-state (I/O), not just CPU
FS           ext4 max file 16 TiB · XFS ⚠️ cannot shrink · inode exhaustion is separate
TIME         ⚠️ Always UTC on servers. `timedatectl set-timezone UTC`
```

---
