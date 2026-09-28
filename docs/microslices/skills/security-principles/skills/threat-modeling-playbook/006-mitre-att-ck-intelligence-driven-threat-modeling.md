---
id: skill-mitre-att-ck-intelligence-driven-threat-modeling-b495d5d542
purpose: mitre att ck intelligence driven threat modeling
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-attack-trees-modeling-attacker-goals-3d66723488"]
links: ["skill-practical-stride-in-agile-sprints-a8bb621a6a"]
---

## MITRE ATT&CK: intelligence-driven threat modeling

**MITRE ATT&CK** (Adversarial Tactics, Techniques, and Common Knowledge) was developed in 2013 and made public in 2015. A continuously updated knowledge base of real-world attack patterns observed against enterprise environments.

**Structure**:
- **Tactics** (14): the "why" — the attacker's objectives at each stage (Initial Access, Execution, Persistence, Privilege Escalation, Defense Evasion, Credential Access, Discovery, Lateral Movement, Collection, Command and Control, Exfiltration, Impact)
- **Techniques** (188+): the "how" — specific methods used to achieve each tactic
- **Sub-techniques** (379+): more specific implementations of techniques
- **Threat actors**: groups associated with specific technique combinations

**Example**: Tactic = Credential Access → Technique = OS Credential Dumping → Sub-technique = LSASS Memory (T1003.001) → used by APT28, Lazarus Group, others

**ATT&CK vs Lockheed Martin Kill Chain**: The Kill Chain (2011) has seven linear stages (Reconnaissance, Weaponization, Delivery, Exploitation, Installation, C2, Actions on Objectives) — useful for describing the attack lifecycle to non-technical leadership and for the insight that breaking any link disrupts the entire attack. But the Kill Chain is linear and perimeter-focused, poorly covering insider threats, cloud attacks, or post-exploitation lateral movement.

**Best practice**: use Kill Chain to identify the attack **stage**; use ATT&CK to identify specific **techniques** within that stage.

### Using ATT&CK for threat modeling

For each system component, ask: which ATT&CK techniques apply to this component's attack surface?

For a Kubernetes cluster, relevant techniques include:
- T1609 (Container Administration Command): exec into containers
- T1610 (Deploy Container): deploy malicious container as persistence
- T1613 (Container and Resource Discovery): enumerate pods, services
- T1552.007 (Container API credentials): steal service account tokens
- T1078.001 (Default Accounts): use default service accounts

Map each technique to relevant mitigations from ATT&CK's mitigation library, then to specific controls in your environment.
