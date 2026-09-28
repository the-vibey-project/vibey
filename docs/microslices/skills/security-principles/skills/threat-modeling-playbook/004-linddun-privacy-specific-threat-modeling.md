---
id: skill-linddun-privacy-specific-threat-modeling-d3550d7879
purpose: linddun privacy specific threat modeling
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-pasta-risk-centric-threat-modeling-cec8d3db65"]
links: ["skill-attack-trees-modeling-attacker-goals-3d66723488"]
---

## LINDDUN: privacy-specific threat modeling

**LINDDUN** was developed at KU Leuven in 2011. Focuses specifically on privacy threats — use when data privacy is a primary concern.

| Threat | Meaning |
|--------|---------|
| **L**inkability | Can an attacker link two or more items of data about the same person? |
| **I**dentifiability | Can an attacker identify an individual from the data? |
| **N**on-repudiation | Can users be held accountable for their actions? (Here a THREAT — users may want deniability) |
| **D**etectability | Can an attacker detect that a data item exists, even without its content? |
| **D**isclosure | Can an attacker access the content of data? |
| **U**nawareness | Are users unaware of how their data is being collected and used? |
| **N**oncompliance | Does the system violate data protection regulations or privacy policies? |

**Critical insight**: Non-repudiation is inverted from security to privacy. In security, proving who did what is a goal. In privacy, it can be a threat — users sometimes want deniability (think: political dissidents, abuse victims, medical patients). A system that creates undeniable records of sensitive behavior may violate privacy principles even if technically "secure."

**When to use LINDDUN**: GDPR compliance design, health data systems, messaging applications with privacy expectations, any system processing personal data at scale.
