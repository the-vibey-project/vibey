---
id: skill-attack-trees-modeling-attacker-goals-3d66723488
purpose: attack trees modeling attacker goals
source: src/vibey_tools/skills/plugins/security-principles/skills/threat-modeling-playbook/SKILL.md
requires: ["skill-linddun-privacy-specific-threat-modeling-d3550d7879"]
links: ["skill-mitre-att-ck-intelligence-driven-threat-modeling-b495d5d542"]
---

## Attack trees: modeling attacker goals

**Attack trees** were popularized by Bruce Schneier in his December 1999 *Dr. Dobb's Journal* article. Root node = attacker's goal. Children = ways to achieve the goal.

**Node types**:
- **OR nodes**: children are alternatives — any one can achieve the parent goal
- **AND nodes**: all children are required co-conditions — the attacker must accomplish all of them

**Attribute propagation**: assign values to leaf nodes (cost, likelihood, difficulty, legality) and compute the cheapest or most likely path to the root. This makes attack trees analytically powerful.

**Example attack tree**: "Gain admin access to payment database"

```
[ROOT - OR] Gain admin access to payment database
├── [OR] Compromise a DBA account
│   ├── Phish DBA (cost: $200, likelihood: medium)
│   ├── Brute-force SSH (cost: $50, likelihood: low - rate limited)
│   └── Exploit password reuse from data breach (cost: $10, likelihood: high)
├── [AND] Exploit SQL injection + Escalate privileges
│   ├── Find SQL injection vulnerability (requires: pen test time)
│   └── Use DB function for OS privilege escalation (requires: specific DB version)
└── [OR] Insider threat
    ├── Bribe current DBA
    └── Compromise former DBA credentials (not yet deprovisioned)
```

Attribute propagation reveals the cheapest path: exploit password reuse from a breach costs $10 and has high likelihood — almost certainly cheaper than all other paths. This drives mitigation priorities: mandatory MFA for DBAs, breach monitoring, deprovisioning processes.

Schneier envisions AI enabling continuous automated attack tree generation — a realistic near-term application for LLMs in security tooling.
