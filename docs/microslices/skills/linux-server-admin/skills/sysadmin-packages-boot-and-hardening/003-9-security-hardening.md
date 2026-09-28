---
id: skill-9-security-hardening-28d7f03aba
purpose: 9 security hardening
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-packages-boot-and-hardening/SKILL.md
requires: ["skill-8-boot-2b413c594f"]
links: []
---

## §9. Security Hardening

### 9.1 The order that actually reduces risk
1. **⚠️ Patch.** Unpatched known CVEs beat every exotic control. Automate it.
2. **Minimize attack surface** — ⚠️ **`ss -tulpn` and turn off what's listening that
   shouldn't be.**
3. **SSH hardening** (§9.4).
4. **Least privilege** — service accounts, capabilities (§2.2 → `sysadmin-filesystem-permissions-and-processes`), systemd sandboxing (§4.3 → `sysadmin-systemd-storage-and-networking`).
5. **Firewall** default-deny inbound (§6.3 → `sysadmin-systemd-storage-and-networking`).
6. **MAC** — SELinux or AppArmor (§9.2).
7. **Audit and monitor** (§9.3).
8. **Backups you have actually restored from** (§14 → `sysadmin-observability-troubleshooting-and-operations`).

### 9.2 SELinux and AppArmor
**⚠️ Do not disable SELinux. Fix the label.** It is the single most-disabled security
control and the fix is usually two commands.
```
getenforce · setenforce 0|1        ⚠️ 0 = permissive, TEMPORARY diagnosis only
ausearch -m avc -ts recent         what was denied
sealert -a /var/log/audit/audit.log   human-readable explanation + suggested fix
semanage fcontext -a -t httpd_sys_content_t "/srv/web(/.*)?"
restorecon -Rv /srv/web            ⚠️ apply the labels
semanage port -a -t http_port_t -p tcp 8080   ⚠️ non-standard port needs this
getsebool -a · setsebool -P httpd_can_network_connect on
```
**⚠️ The diagnostic pattern**: set permissive, reproduce, read the AVC denials, fix labels
or booleans, set enforcing, verify. **Permissive still logs — that's the point.**

**AppArmor** (Debian/Ubuntu, path-based): `aa-status`, `aa-complain`, `aa-enforce`,
profiles in `/etc/apparmor.d/`.

### 9.3 Audit and detection
`auditd` with rules in `/etc/audit/rules.d/`; `aureport`, `ausearch`.
**File integrity**: AIDE, Tripwire. **Rootkit checks**: rkhunter, chkrootkit.
**Runtime**: **Falco** (eBPF-based, §10.4 → `sysadmin-observability-troubleshooting-and-operations`). **`fail2ban`** for brute-force.
**⚠️ Detection you never look at is theatre.** Ship to a central place, alert on
something, and test that the alert fires.

### 9.4 SSH — the config that matters
```
PermitRootLogin no                    ⚠️ or prohibit-password at minimum
PasswordAuthentication no             ⚠️ keys only — this is the single biggest win
KbdInteractiveAuthentication no        (⚠️ or password auth sneaks back in via PAM)
PubkeyAuthentication yes
AllowUsers alice bob   /  AllowGroups ssh-users
MaxAuthTries 3 · LoginGraceTime 30 · MaxSessions 10
ClientAliveInterval 300 · ClientAliveCountMax 2
X11Forwarding no · AllowAgentForwarding no · PermitTunnel no
```
**⚠️ Always `sshd -t` before reloading, and keep your existing session open while you test
a new one from another terminal.** A bad sshd config plus a closed session equals a
console trip.

**Keys**: `ed25519` (⚠️ **the default choice — small, fast, no parameter footguns**) or
RSA ≥3072. **`ssh-keygen -t ed25519 -C "comment"`.** ⚠️ **Use an agent and
`AddKeysToAgent`; consider certificates (`ssh-keygen -s`) over `authorized_keys` sprawl at
fleet scale — a CA with short-lived certs removes the key-revocation problem entirely.**
