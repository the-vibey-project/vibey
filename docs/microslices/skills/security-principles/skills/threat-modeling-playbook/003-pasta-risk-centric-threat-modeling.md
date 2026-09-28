---
id: skill-pasta-risk-centric-threat-modeling-cec8d3db65
purpose: pasta risk centric threat modeling
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-stride-systematic-threat-enumeration-3d1ffad6be"]
links: ["skill-linddun-privacy-specific-threat-modeling-d3550d7879"]
---

## PASTA: risk-centric threat modeling

**PASTA** (Process for Attack Simulation and Threat Analysis) was developed in 2012 by Tony UcedaVélez. Seven stages organized as risk-centric and attacker-centric analysis. Carnegie Mellon SEI recommends PASTA as the basis for comprehensive threat modeling.

| Stage | Name | Key Activity |
|-------|------|-------------|
| 1 | Define Business Objectives | Identify the business impact of a breach: regulatory, reputational, financial |
| 2 | Define Technical Scope | Enumerate components, dependencies, data classification |
| 3 | Decompose Application | Create DFDs, identify trust boundaries, data flows |
| 4 | Threat Analysis | Enumerate threats using intelligence (CVEs, threat feeds, MITRE ATT&CK) |
| 5 | Vulnerability Analysis | Map threats to known weaknesses in the specific tech stack |
| 6 | Attack Modeling | Build attack trees; model attacker scenarios end-to-end |
| 7 | Risk/Impact Analysis | Connect technical threats to business impact; prioritize mitigations |

**PASTA's key advantage over STRIDE**: by starting with business objectives (Stage 1) and ending with risk analysis (Stage 7), PASTA connects technical threats to business impact. Stage 7 filters STRIDE's threat explosion through a risk and impact lens, producing a prioritized, business-justified mitigation backlog.

**PASTA's key advantage over pure STRIDE**: PASTA elevates threat modeling to a strategic organizational activity. It produces output that resonates with executives and boards — not just a list of technical vulnerabilities, but a prioritized risk register with business-impact framing.

**When to use PASTA**: new system architecture review, compliance audit preparation, board-level security reporting, any context requiring explicit business impact analysis.
