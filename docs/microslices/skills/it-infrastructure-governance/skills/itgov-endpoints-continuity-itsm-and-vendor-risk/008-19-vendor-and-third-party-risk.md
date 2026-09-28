---
id: skill-19-vendor-and-third-party-risk-920c443b19
purpose: 19 vendor and third party risk
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-endpoints-continuity-itsm-and-vendor-risk/SKILL.md
requires: ["skill-18-capacity-and-lifecycle-8074d2ddd7"]
links: []
---

## §19. Vendor and Third-Party Risk

**⚠️ Your security posture includes your vendors', and supply-chain compromise is now a
primary attack path.**
**Due diligence, security questionnaires** (⚠️ **low signal, but the absence of answers is
itself signal**), **SOC 2 reports** (⚠️ **read the exceptions section and the scope, which
is where the information is**), **contractual security requirements, right to audit,
breach notification obligations** (see a business reference §16).
**⚠️ Fourth-party risk** — your vendor's vendors.
**⚠️ Integration access is the concrete exposure**: **every SaaS integration holds a
credential into your environment**, and ⚠️ **OAuth grants and API tokens issued to
third-party applications are frequently over-scoped, never reviewed, and outlive the
business relationship** (§21.2 → `itgov-reference`).
