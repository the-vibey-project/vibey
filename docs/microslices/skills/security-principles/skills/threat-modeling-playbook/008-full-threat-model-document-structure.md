---
id: skill-full-threat-model-document-structure-ce10b37165
purpose: full threat model document structure
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-practical-stride-in-agile-sprints-a8bb621a6a"]
links: ["skill-risk-rating-using-cvss-and-epss-together-c875d533c2"]
---

## Full threat model document structure

For architecture-level reviews (new systems, major changes, compliance requirements):

1. **Scope**: what is in scope, what is explicitly out of scope, which threat actors are in scope
2. **Architecture diagram**: components, data flows, external integrations, deployment topology
3. **Trust boundaries**: explicit enumeration with rationale for each boundary
4. **Asset inventory**: what data is stored/processed, classification, regulatory scope
5. **Threat enumeration**: STRIDE per element, organized by risk level
6. **Risk rating**: likelihood × impact for each threat (CVSS base score where applicable; EPSS for exploitation probability)
7. **Mitigations**: specific controls mapped to each threat
8. **Residual risk**: threats that cannot be fully mitigated, accepted risk documented with owner and review date
9. **Security backlog**: prioritized list of mitigations not yet implemented
