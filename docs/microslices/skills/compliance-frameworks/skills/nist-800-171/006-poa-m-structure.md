---
id: skill-poa-m-structure-33060b98cc
purpose: poa m structure
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/nist-800-171/SKILL.md
requires: ["skill-self-assessment-methodology-8c70848f7c"]
links: ["skill-common-control-deficiencies-and-remediation-patterns-062bdb33e0"]
---

## POA&M Structure

A Plan of Actions and Milestones documents unmet controls and the roadmap to address them.

**Required fields per POA&M item:**
```
Control ID:        3.5.3
Requirement:       Use multifactor authentication for local and network access to privileged accounts
Weakness:          MFA is not enforced for local privileged access on 12 workstations
Severity:          High (3-point deduction)
Scheduled Completion: 2024-03-31
Milestones:
  - 2024-01-15: Evaluate MFA solutions (Duo, Entra ID MFA, Okta)
  - 2024-02-15: Pilot deployment to 3 admin workstations
  - 2024-03-15: Full rollout to all privileged accounts
  - 2024-03-31: Evidence collected and SSP updated
Responsible Party: IT Manager
Resources:         $X licensing cost, 40 hours implementation
```


---
