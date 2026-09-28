---
id: skill-2-users-permissions-capabilities-4d0880b5e5
purpose: 2 users permissions capabilities
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-filesystem-permissions-and-processes/SKILL.md
requires: ["skill-1-filesystem-and-files-ef1b0786c7"]
links: ["skill-3-processes-and-resources-69096eaf8e"]
---

## §2. Users, Permissions, Capabilities

### 2.1 The basics, precisely
```
rwx rwx rwx    user / group / other
4=r 2=w 1=x
```
**⚠️ On a directory**: `x` = may traverse into it (needed to access anything inside);
`r` = may *list* it; `w` = may create/delete entries. **⚠️ Delete permission on a file
comes from the DIRECTORY's `w`, not the file's** — which is why you can delete a file you
can't write.

**Special bits**: **setuid** (4000 — runs as file owner), **setgid** (2000 — on a
directory, ⚠️ **new files inherit the group; the standard trick for shared directories**),
**sticky** (1000 — ⚠️ **on `/tmp`: only the owner may delete their own files**).

**⚠️ umask subtracts**: default 022 gives 755 for dirs, 644 for files. Services often set
their own.

**ACLs** for finer control: `getfacl` / `setfacl -m u:alice:rw file`.
⚠️ **`ls -l` shows a `+` when ACLs exist — and people miss it.**

### 2.2 Capabilities — the modern answer to setuid root
**⚠️ Root is decomposed into ~40 capabilities.** Grant one instead of everything:
```
getcap /usr/bin/ping                      → cap_net_raw+ep
setcap cap_net_bind_service=+ep /path/to/binary   ⚠️ bind <1024 without root
capsh --print                             what does this shell have
```
**Common ones**: `CAP_NET_BIND_SERVICE`, `CAP_NET_ADMIN`, `CAP_SYS_ADMIN`
(⚠️ **effectively root — "the new root"; granting it is not hardening**), `CAP_DAC_OVERRIDE`,
`CAP_CHOWN`, `CAP_SETUID`.

**⚠️ In systemd, prefer `AmbientCapabilities=` over a setuid binary** (§4.3 → `sysadmin-systemd-storage-and-networking`) — it's
auditable and scoped to the unit.

### 2.3 Accounts
`/etc/passwd` (⚠️ **no passwords — they're in `/etc/shadow`**), `/etc/group`,
`/etc/sudoers` (⚠️ **edit with `visudo` only — a syntax error locks you out of sudo**).
**Service accounts should be `--system --shell /usr/sbin/nologin --no-create-home`.**
**PAM** (`/etc/pam.d/`) governs authentication, session setup, and limits —
⚠️ **`pam_limits` is why `/etc/security/limits.conf` applies to login sessions but NOT to
systemd services** (§4.3 → `sysadmin-systemd-storage-and-networking`).

---
