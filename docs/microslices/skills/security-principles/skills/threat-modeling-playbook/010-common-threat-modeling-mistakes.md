---
id: skill-common-threat-modeling-mistakes-293309546c
purpose: common threat modeling mistakes
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-risk-rating-using-cvss-and-epss-together-c875d533c2"]
links: ["skill-quick-reference-when-to-use-which-methodology-cc081e5a01"]
---

## Common threat modeling mistakes

**Threat explosion without prioritization**: STRIDE generates many threats; without risk filtering, the output is an unusable list. Always apply likelihood × impact before presenting results.

**Forgetting the Return threat**: threat models often focus on external attacks and miss insider threats, supply chain threats, and operational failures.

**Static threat models**: threat models have a shelf life. Architectural changes, new integrations, and new threat intelligence all require revisits. Schedule quarterly reviews for production systems.

**Confusing assets with components**: the asset is the data, not the database. The database is the component that protects (or exposes) the asset. Threats are ultimately to assets, not to components.

**Skipping the Trust Boundary step**: trust boundaries are where most interesting threats live — they are the seams where different levels of trust meet. A DFD without explicit trust boundaries is a drawing, not a threat model.

**Not translating to business impact**: technical threat models that cannot be translated to business terms (revenue at risk, regulatory exposure, reputation damage) fail to drive organizational prioritization. PASTA Stage 7 solves this; even lightweight STRIDE should include a one-sentence business impact for each High-risk threat.
