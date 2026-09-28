---
id: skill-the-cia-triad-what-security-protects-2f84706f8a
purpose: the cia triad what security protects
source: src/vibey_tools/skills/plugins/security-principles/skills/cybersecurity-principles/SKILL.md
requires: ["skill-the-saltzer-schroeder-eight-principles-d6169a079e"]
links: ["skill-aaa-authentication-authorization-and-accounting-7fe93cb775"]
---

## The CIA Triad: what security protects

**Confidentiality, Integrity, Availability** — the three pillars emerged separately. Confidentiality from a 1976 U.S. Air Force study. Integrity from Clark and Wilson's 1987 commercial security paper. Availability as a named concept around 1988. They unified into a triad by the late 1990s.

NIST CSF 2.0 extended this to include data *in use* — the driver behind confidential computing adoption (see Modern Framework Updates section).

### The critical insight: the pillars are in tension

Every security architecture is an act of balancing these tensions, not maximizing any single pillar.

| Tension | Example |
|---------|---------|
| Confidentiality vs. Availability | HIPAA authentication requirements slow access to patient records in emergencies. A doctor trying to access a patient record in a code situation faces this tension daily. |
| Integrity vs. Performance | Running integrity checks on every transaction adds latency that real-time financial systems cannot afford. |
| Confidentiality vs. Availability | Encrypting data at rest protects confidentiality, but if encryption keys are lost, availability is permanently destroyed. |

There is no universally correct balance point. The right trade-off depends on the specific context and which failure mode is more catastrophic.
