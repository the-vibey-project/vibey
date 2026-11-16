---
id: skill-input-schema-ef4b6f042e
purpose: input schema
source: src/vibey_tools/skills/plugins/christian-courtship/skills/operational-courtship-playbook/SKILL.md
requires: ["skill-invocation-triggers-5a98a48389"]
links: ["skill-situational-action-protocols-d2200979b0"]
---

## Input Schema
```yaml
courtship_transition_request:
  current_stage: string (friendship | courtship | betrothal | marriage)
  candidate_names:
    suitor: string
    candidate: string
  prior_marital_history:
    suitor_divorced: boolean
    candidate_divorced: boolean
    biblical_grounds_verified: boolean # 1 Cor 7:15 abandonment or Matt 19:9
    dependent_children_involved: boolean
  pastoral_oversight_active: boolean
```
