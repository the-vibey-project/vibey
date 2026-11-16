---
id: skill-input-schema-5aea5f5f2f
purpose: input schema
source: src/vibey_tools/skills/plugins/loving-people-well/skills/mercy-and-trust-edges/SKILL.md
requires: ["skill-invocation-triggers-3bd5dfa888"]
links: ["skill-governing-principles-167e721ef5"]
---

## Input Schema
```yaml
offense_and_boundary_evaluation:
  offense_description: string
  grievance_ledger_severity: integer (1-10)
  unilateral_forgiveness_status: boolean
  trust_rebuilding_requirements: list[string]
  truth_speaking_needed: string
  boundary_edges: list[string]
```
