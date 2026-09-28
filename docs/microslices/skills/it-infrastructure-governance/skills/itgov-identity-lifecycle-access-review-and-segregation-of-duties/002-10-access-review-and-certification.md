---
id: skill-10-access-review-and-certification-c69c54d683
purpose: 10 access review and certification
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-identity-lifecycle-access-review-and-segregation-of-duties/SKILL.md
requires: ["skill-9-identity-lifecycle-joiner-mover-leaver-c255d736fb"]
links: ["skill-11-segregation-of-duties-1d9ac53f33"]
---

## §10. Access Review and Certification

**⚠️ Periodic recertification: managers or resource owners attest that access is still
needed.** ⚠️ **It is the standard control and it is widely performed badly.**

> **⚠️ GOTCHA — rubber-stamping makes the control worthless while producing perfect
> evidence that it was performed.** ⚠️ **A manager presented with 400 entitlements named
> `APP_PRD_RW_GRP_04` will approve all of them, and the audit artefact will look
> immaculate.**
> **⚠️ What actually improves it**: **review by resource owner rather than line manager
> where the owner understands what the access does**; **plain-language entitlement
> descriptions**; **risk-based scoping — certify high-risk entitlements often and
> low-risk ones rarely, rather than everything annually**; **highlighting anomalies and
> outliers rather than presenting flat lists**; ⚠️ **and micro-certifications triggered by
> events (role change, unusual usage) rather than a calendar.**

**⚠️ Metrics worth tracking**: **orphaned accounts (no owner), dormant accounts (no
sign-in in N days), entitlements never used** (⚠️ **research suggests identities commonly
use a very small fraction of what they're granted, which is the argument for
usage-informed rightsizing**), **exception count and age**, **time-to-deprovision.**

---
