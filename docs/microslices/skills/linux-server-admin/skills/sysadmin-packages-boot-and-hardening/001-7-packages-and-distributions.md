---
id: skill-7-packages-and-distributions-9f08e3fe53
purpose: 7 packages and distributions
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-packages-boot-and-hardening/SKILL.md
requires: []
links: ["skill-8-boot-2b413c594f"]
---

## §7. Packages and Distributions

| Family | Tools |
|---|---|
| **Debian/Ubuntu** | `apt`, `dpkg`, `apt-mark hold`, `/etc/apt/sources.list.d/`, `unattended-upgrades` |
| **RHEL family** | `dnf`, `rpm`, `dnf versionlock`, `dnf history undo N` ⚠️ **(genuinely useful)**, `dnf needs-restarting -r` |
| **SUSE** | `zypper` |
| **Arch** | `pacman` |
| **Universal** | `snap`, `flatpak`, `nix` |

```
dnf history · dnf history undo 42       ⚠️ transactional rollback of a package op
apt list --upgradable · apt-mark hold pkg
rpm -qf /path/to/file · dpkg -S /path   ⚠️ which package owns this file?
rpm -V pkg · debsums -c                 ⚠️ verify installed files against the package
needrestart / dnf needs-restarting -r   ⚠️ what needs restarting after an update
```
**⚠️ The `.rpmnew` / `.dpkg-dist` trap**: when you've modified a config that a package
update also changed, the package manager writes the new version alongside and **your
edited file stays**. **You get the old behaviour plus a file you never look at.** Search
for them after every batch of updates:
`find /etc -name '*.rpmnew' -o -name '*.rpmsave' -o -name '*.dpkg-*'`.

**⚠️ Distribution choice is mostly a lifecycle and ecosystem decision, not a technical
one.** RHEL family for long support and vendor certification; Debian for stability without
a subscription; Ubuntu LTS for a middle path with commercial options. **§17 → `sysadmin-reference` for dates.**

---
