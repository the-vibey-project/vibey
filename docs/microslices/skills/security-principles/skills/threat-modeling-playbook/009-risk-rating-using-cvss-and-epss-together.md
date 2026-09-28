---
id: skill-risk-rating-using-cvss-and-epss-together-c875d533c2
purpose: risk rating using cvss and epss together
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-full-threat-model-document-structure-ce10b37165"]
links: ["skill-common-threat-modeling-mistakes-293309546c"]
---

## Risk rating: using CVSS and EPSS together

**CVSS** (Common Vulnerability Scoring System) measures severity 0.0-10.0. Limitations: base scores are often treated as final severity when temporal and environmental metrics are rarely applied; does not capture vulnerability chaining; measures severity, not risk.

**EPSS** (Exploit Prediction Scoring System): predicts exploitation probability within 30 days based on real-world exploit activity. Critical complement to CVSS.

**The key insight**: a CVSS 6.8 vulnerability with 94% EPSS probability may be more urgent than a CVSS 9.8 with 2% EPSS probability that has never been exploited in the wild.

**Combined formula for threat modeling**: Risk = CVSS severity × EPSS exploitation probability × Asset value × (1 - Control effectiveness)
