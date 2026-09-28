---
id: skill-11-segregation-of-duties-1d9ac53f33
purpose: 11 segregation of duties
source: src/vibey_tools/skills/plugins/it-infrastructure-governance/skills/itgov-identity-lifecycle-access-review-and-segregation-of-duties/SKILL.md
requires: ["skill-10-access-review-and-certification-c69c54d683"]
links: []
---

## §11. Segregation of Duties

**⚠️ No single person should control an entire sensitive transaction end to end.**
**Classic pairs: create a vendor and approve payment to it; write code and deploy it to
production unreviewed; request access and approve it; administer a system and audit its
logs.**
**⚠️ SoD is a combinatorial problem, not a per-permission one** — **each permission is
fine; the combination is the violation**, ⚠️ **which is why it must be evaluated as a rule
set across effective access, and why it interacts badly with nested groups** (§7 → `itgov-directory-authentication-authorization-and-privileged-access`).
**⚠️ Compensating controls** where SoD is impossible — **and in small teams it frequently
is.** **Detective controls, mandatory review, and logging with independent oversight are
the honest answer for a five-person IT department, rather than pretending the separation
exists.**
