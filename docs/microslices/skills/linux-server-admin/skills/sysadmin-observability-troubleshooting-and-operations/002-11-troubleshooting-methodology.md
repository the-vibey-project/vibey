---
id: skill-11-troubleshooting-methodology-97d77938b6
purpose: 11 troubleshooting methodology
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-observability-troubleshooting-and-operations/SKILL.md
requires: ["skill-10-observability-and-performance-603b4f80c2"]
links: ["skill-12-containers-and-namespaces-f5fa36b2a7"]
---

## §11. Troubleshooting Methodology

### 11.1 The sequence
```
1. ⚠️ What CHANGED?  deploys, package updates, config management runs, certs, DNS,
                      upstream, traffic pattern. Check this BEFORE theorizing.
2. Define the symptom precisely — who, what, since when, how often, all or some?
3. Bisect the stack:  client → DNS → network → LB → host → service → dependency → storage
4. Read the errors:   journalctl -p err -b · dmesg -T · the app's own log
5. Form ONE hypothesis, test it cheaply, record the result
6. Fix, verify, and write down what it was
```
**⚠️ The single highest-yield question is "what changed?" and it is the one people skip
while forming theories.**

### 11.2 The four-places-state problem
**⚠️ When behaviour makes no sense, check whether these agree:**
```
On disk           cat the actual file — ⚠️ and check for .rpmnew (§7)
Kernel/live       sysctl -a · ip a · nft list ruleset · systemctl show
Process memory    ⚠️ the process loaded config at START — it may be running old config
                  ls -l /proc/PID/exe · /proc/PID/environ · restart to be sure
Config management ⚠️ is Ansible/Puppet about to revert your manual fix?
```
**⚠️ "I fixed it and it broke again 30 minutes later" is config management reverting you.**

### 11.3 Specific scenarios
**Disk full but `du` disagrees** → ⚠️ **deleted-but-open files: `lsof +L1`** (§1.2 → `sysadmin-filesystem-permissions-and-processes`).
Also check for a filesystem mounted *over* a populated directory hiding its contents.
**Out of inodes** → `df -i` (§1.2 → `sysadmin-filesystem-permissions-and-processes`).
**Service won't start** → `systemctl status -l`, `journalctl -xeu NAME`,
`systemd-analyze verify unit`, ⚠️ **and check SELinux with `ausearch -m avc -ts recent`.**
**Port already in use** → `ss -tulpn | grep :PORT`.
**Slow but idle CPU** → ⚠️ **`runqlat`, PSI, `%steal`, I/O `await`** — saturation without
utilization.
**Intermittent DNS** → ⚠️ **`resolvectl status`, check search domains and `ndots`, compare
`dig @server` against `dig`.**
**Clock drift** → `timedatectl`, `chronyc tracking` — ⚠️ **breaks TLS, Kerberos, and
log correlation in ways that look like other problems.**
**Certificate expiry** → `openssl s_client -connect host:443 </dev/null 2>/dev/null |
openssl x509 -noout -dates`. ⚠️ **Monitor this; it is a fully preventable, recurring
outage cause.**

---
