---
id: skill-input-schema-6952f9cd32
purpose: input schema
source: src/vibey_tools/skills/plugins/christian-courtship/skills/commitment-and-differentiation/SKILL.md
requires: ["skill-invocation-triggers-e7ca008a97"]
links: ["skill-key-empirical-models-b38a8b3b33"]
---

## Input Schema
```yaml
empirical_assessment:
  dedication_score: float (0.0 to 10.0) # partner priority, we-identity, long-term intent
  constraint_score: float (0.0 to 10.0) # external exit costs, financial ties, social pressure
  cohabitation_status: boolean
  differentiation_level: string (low_fusion | low_cutoff | moderate | high_differentiation)
  triangulation_risk: boolean
```
