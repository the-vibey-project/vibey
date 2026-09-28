---
id: skill-17-lifecycle-dates-verified-august-2026-0f96ff4415
purpose: 17 lifecycle dates verified august 2026
source: src/vibey_tools/skills/plugins/linux-server-admin/skills/sysadmin-reference/SKILL.md
requires: ["skill-16-numbers-and-limits-1898cb6bf7"]
links: ["skill-18-books-59ff0a57ae"]
---

## §17. Lifecycle Dates — verified August 2026

**⚠️ Lifecycle dates are the one genuinely perishable thing in this document. Verify
against the vendor before planning a migration.**

| Distribution | Status as of August 2026 |
|---|---|
| **RHEL 10** | Released **20 May 2025**. Full support to ~**May 2030**, maintenance to ~**May 2035**. Latest minor **10.2** (May 2026) |
| **RHEL 9** | Full support to **31 May 2027**, maintenance to **31 May 2032** |
| **RHEL 8** | ⚠️ **Full support ended 31 May 2024**; 8.10 is the final minor, maintenance to **31 May 2029** |
| **RHEL 7** | ⚠️ **Maintenance ended 30 June 2024**; ELS extended to **31 May 2029** |
| **Ubuntu 26.04 LTS** | Current LTS, released **April 2026**, standard support to **30 April 2031** |
| **Ubuntu 24.04 LTS** | Supported to **31 May 2029** |
| **Ubuntu 25.10** | ⚠️ **EOL 1 July 2026** — interim releases get 9 months |

**⚠️ RHEL's lifecycle is unusually complex** — overlapping **Full Support → Maintenance
Support → Extended Life → ELS** phases, each meaning something different about which
patches you actually receive. **"Is it EOL?" is the wrong question; "which phase, and does
that phase still ship security errata?" is the right one.** **Ubuntu LTS is 5 years
standard, extendable via Pro/ESM.**

**⚠️ Kernel LTS windows have been volatile**: historically six years, **cut to a 2-year
default in 2023** as maintainers cited burnout, then **partially extended again in early
2026 after industry pushback.** ⚠️ **But upstream kernel.org lifecycle usually isn't what
governs you — your distribution's backporting is.** **A RHEL 9 kernel gets security fixes
long after the upstream branch is dead.**

⚠️ **One claim I encountered and am flagging rather than repeating as fact**: a source
asserts a **Linux 7.0** release in 2026 following the 6.x series. **I could not corroborate
this against kernel.org and have not built anything in this document on it.** Version
numbering in Linux is arbitrary by policy, so it's plausible — **verify before quoting.**

**eBPF tooling** (§10.4 → `sysadmin-observability-troubleshooting-and-operations`) is mature and stable in interface: **BCC** ships **80+ ready-made
tools**, **bpftrace** is the one-liner language, and **libbpf + CO-RE** is the production
path for custom programs. ⚠️ **This is now baseline knowledge rather than specialist
tooling.**

---
