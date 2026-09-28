---
id: skill-4-systemd-d8c2c67378
purpose: 4 systemd
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-systemd-storage-and-networking/SKILL.md
requires: []
links: ["skill-5-storage-94c4fefc3f"]
---

## §4. systemd

### 4.1 The model
**Units**: `.service`, `.socket`, `.timer`, `.mount`, `.target`, `.path`, `.slice`,
`.device`. **Targets replace runlevels.**
```
systemctl status|start|stop|restart|reload|enable|disable|mask NAME
systemctl daemon-reload            ⚠️ ALWAYS after editing a unit file
systemctl list-units --failed      ⚠️ the first thing to run on a sick box
systemctl cat NAME                 effective unit, including drop-ins
systemctl show NAME                every resolved property
systemctl edit NAME                ⚠️ creates a drop-in — the RIGHT way to override
systemd-analyze blame              boot time by unit
systemd-analyze critical-chain     ⚠️ the actual boot critical path
```
> **⚠️ GOTCHA — never edit vendor unit files in `/usr/lib/systemd/system/`.**
> A package update overwrites them. **Use `systemctl edit NAME` (drop-in in
> `/etc/systemd/system/NAME.d/`) or copy the whole unit to `/etc/systemd/system/`.**
> `/etc` beats `/usr`. **`systemctl cat` shows you what's actually in effect.**

### 4.2 Dependency and ordering — the distinction people get wrong
**⚠️ `Wants=`/`Requires=` express *dependency*. `After=`/`Before=` express *ordering*.
They are independent.** `Requires=foo.service` without `After=foo.service` starts both in
parallel and your service probably fails.
- **`Requires=`** — if the dep fails, this unit fails. **`Wants=`** — weaker; proceed
  regardless. **`BindsTo=`** — stronger; stop if the dep stops.
- ⚠️ **`Requires=` + `After=` is the combination you almost always want.**

### 4.3 The hardening and resource directives
**⚠️ This is systemd's best feature and it's underused.** Per-service sandboxing:
```
[Service]
User=svc                       Group=svc
NoNewPrivileges=true           ⚠️ blocks setuid escalation
ProtectSystem=strict           /usr, /boot, /etc read-only
ProtectHome=true               /home, /root, /run/user inaccessible
PrivateTmp=true                ⚠️ private /tmp — kills a whole class of symlink attacks
PrivateDevices=true            minimal /dev
ProtectKernelTunables=true     ProtectKernelModules=true
ProtectControlGroups=true      RestrictSUIDSGID=true
RestrictAddressFamilies=AF_INET AF_INET6 AF_UNIX
SystemCallFilter=@system-service
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
AmbientCapabilities=CAP_NET_BIND_SERVICE
ReadWritePaths=/var/lib/svc
MemoryMax=2G                   CPUQuota=50%     TasksMax=512
LimitNOFILE=65535              ⚠️ limits.conf does NOT apply here
Restart=on-failure             RestartSec=5s
```
**⚠️ `systemd-analyze security NAME` scores a unit's exposure** and tells you what's
missing. Run it on everything you write.

**⚠️ `Type=` matters**: `simple` (default, ⚠️ **considered started immediately — no
readiness signal**), `exec`, `forking` (⚠️ **needs `PIDFile=`**), `oneshot`
(+ `RemainAfterExit=`), **`notify`** (⚠️ **the process signals readiness via sd_notify —
the correct choice if the software supports it**).

### 4.4 journald
```
journalctl -u NAME -f                  follow one unit
journalctl -u NAME --since "1 hour ago" --until "10 min ago"
journalctl -p err -b                   ⚠️ errors this boot
journalctl -b -1                       previous boot ⚠️ (crash forensics)
journalctl -k                          kernel messages
journalctl -o json-pretty              structured fields
journalctl --disk-usage · --vacuum-time=30d · --vacuum-size=1G
journalctl -f _SYSTEMD_UNIT=x.service _PID=1234    field matching
```
**⚠️ By default the journal may be volatile** (`/run/log/journal`) and lost on reboot.
**For persistence: `Storage=persistent` in `journald.conf` and `mkdir -p
/var/log/journal`.** ⚠️ **A surprising number of "we have no logs from the crash"
incidents are this.**

### 4.5 Timers over cron
```
[Timer]
OnCalendar=*-*-* 02:00:00
Persistent=true          ⚠️ run on boot if the last run was missed
RandomizedDelaySec=300   ⚠️ avoid thundering herd across a fleet
```
**⚠️ Timers beat cron because**: you get journald logging, dependency ordering, resource
limits, and `systemctl list-timers`. **`systemd-analyze calendar "EXPR"` validates the
schedule before you deploy it.**

---
