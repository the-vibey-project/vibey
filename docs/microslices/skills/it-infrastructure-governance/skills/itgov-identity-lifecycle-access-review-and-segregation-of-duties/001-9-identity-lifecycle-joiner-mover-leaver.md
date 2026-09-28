---
id: skill-9-identity-lifecycle-joiner-mover-leaver-c255d736fb
purpose: 9 identity lifecycle joiner mover leaver
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-identity-lifecycle-access-review-and-segregation-of-duties/SKILL.md
requires: []
links: ["skill-10-access-review-and-certification-c69c54d683"]
---

## §9. Identity Lifecycle (Joiner-Mover-Leaver)

```
JOINER  ⚠️ provisioning driven from an authoritative source (HR system), not tickets
MOVER   ⚠️ THE HARD ONE — see below
LEAVER  ⚠️ deprovision everything, promptly, including non-SSO apps
```
> **⚠️ GOTCHA — the "mover" case is where privilege creep comes from, and almost every
> organization handles it badly.** ⚠️ **When someone changes role, new access is granted
> promptly because they need it to work — and old access is rarely removed, because
> removing it has no urgency and some risk of breaking something.** **Over a career, a
> long-tenured employee accumulates the union of every role they've held.**
> **⚠️ The fix is that role change must trigger revocation review, not just grant** — and
> ⚠️ **defaulting to revoke-and-re-request is more effective than review-and-remove, because
> the default is what determines the outcome.**

**⚠️ Leaver risk is concentrated in what SSO doesn't cover**: **the account disabled in the
directory is the easy part.** ⚠️ **Locally-provisioned SaaS, shared credentials, personal
API keys, VPN certificates, physical access, and anything the person set up themselves are
what actually persist.** **Immediate disable beats delete** (preserves data and audit
trail), **transfer ownership of data and service accounts**, and **rotate any shared
secret they knew.**
**⚠️ Contractors and third parties need an expiry date at creation** — ⚠️ **time-bounded by
default, because nobody will remember to remove them.**

---
