---
id: skill-20-method-a71adc6e9a
purpose: 20 method
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-reference/SKILL.md
requires: ["skill-19-command-reference-2bc6732222"]
links: []
---

## §20. Method

**§1–§16 → `sysadmin-filesystem-permissions-and-processes`, `sysadmin-systemd-storage-and-networking`, `sysadmin-packages-boot-and-hardening`, `sysadmin-observability-troubleshooting-and-operations` and §19 rest on stable material** — POSIX file semantics, kernel subsystems,
systemd, TCP/IP, and standard tooling — plus the reference works in §18, chiefly
**Nemeth**, **Gregg's *Systems Performance*** for the observability method, and
**Kerrisk** for syscall behaviour. ⚠️ **None of that needed web verification; the man
pages and those books are the authority and they change slowly.**

**Two searches were run in August 2026**, confined to what genuinely perishes:
**distribution lifecycle dates** and the **eBPF tooling landscape**.

**Confidence.** **High** in §1–§16 → `sysadmin-filesystem-permissions-and-processes`, `sysadmin-systemd-storage-and-networking`, `sysadmin-packages-boot-and-hardening`, `sysadmin-observability-troubleshooting-and-operations` and §19 — these are mechanisms and commands I've stated
with their failure modes, and the failure modes are the valuable part. **High** in §10.4 → `sysadmin-observability-troubleshooting-and-operations`'s
eBPF characterization, which is consistent across sources and matches the primary tooling
documentation.

⚠️ **Lower confidence on §17's dates specifically, and I want to be direct about why.**
**Most sources returned for lifecycle questions are EOL-tracking aggregator sites**, several
of which are commercial services with an interest in urgency, and they occasionally
disagree at the margins. **The RHEL dates are consistent across several of them and align
with Red Hat's published phase structure; the Ubuntu dates follow the documented
5-year LTS policy.** **But before you plan a migration on these, check Red Hat's own
lifecycle page or Canonical's release-cycle page** — ⚠️ **vendors extend ELS windows, and
RHEL 7's ELS extension to 2029 is exactly that kind of change.**

⚠️ **And I have explicitly declined to assert one claim**: a source stated Linux 7.0
shipped in 2026. **I could not corroborate it and nothing here depends on it.** Version
numbers in Linux are chosen arbitrarily rather than by semantic rule, so it is plausible —
but **an uncorroborated version claim is not something to put in a reference document
unflagged.**
