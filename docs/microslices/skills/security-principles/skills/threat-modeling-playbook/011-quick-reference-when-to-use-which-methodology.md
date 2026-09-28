---
id: skill-quick-reference-when-to-use-which-methodology-cc081e5a01
purpose: quick reference when to use which methodology
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-common-threat-modeling-mistakes-293309546c"]
links: []
---

## Quick-reference: when to use which methodology

| Situation | Recommended approach |
|-----------|---------------------|
| New feature in a sprint, need fast analysis | Lightweight STRIDE per user story |
| New system architecture design | STRIDE + attack trees for high-risk components |
| Comprehensive architecture review for compliance | PASTA |
| System processes personal data (GDPR, HIPAA) | Add LINDDUN to STRIDE |
| Evaluating detection/monitoring coverage | MITRE ATT&CK mapping |
| Executive/board security briefing | PASTA Stage 7 output |
| Red team planning | Attack trees + MITRE ATT&CK |
| Post-incident review to update threat model | MITRE ATT&CK technique identification + threat model update |
