---
id: skill-12-endpoint-management-and-patching-07c8f23464
purpose: 12 endpoint management and patching
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-endpoints-continuity-itsm-and-vendor-risk/SKILL.md
requires: []
links: ["skill-13-backup-dr-and-continuity-1f63342bae"]
---

## §12. Endpoint Management and Patching

**Imaging and provisioning**, **MDM/UEM**, **configuration baselines** (⚠️ **CIS
Benchmarks, DISA STIGs — and applying a benchmark wholesale without testing breaks
things, so baseline then exception with justification**), **application allowlisting**,
**disk encryption with escrowed recovery keys**, **EDR.**
**⚠️ Patching is where most exploited vulnerabilities actually live** — **not zero-days,
but known vulnerabilities with available patches.** ⚠️ **The constraint is rarely knowing
about them; it's testing, change windows, and legacy dependencies.**
```
Inventory → risk-rank (⚠️ exploitability and exposure, not CVSS alone)
→ test ring → phased deployment → verify → report exceptions
```
**⚠️ Emergency patching needs a pre-agreed process**, because deciding how to bypass change
control during an active exploit is too late.

---
