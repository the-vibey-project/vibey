---
id: skill-input-schema-1a86c2a14f
purpose: input schema
source: src/vibey_tools/skills/plugins/christian-courtship/skills/risk-calculus-and-quarantine/SKILL.md
requires: ["skill-invocation-triggers-d2c9f86ca1"]
links: ["skill-mathematical-formulations-1e6fa017b2"]
---

## Input Schema
```yaml
risk_evaluation_input:
  exposure_level_E: float (1.0 to 10.0) # sensitivity of shared assets and private disclosures
  hazard_severity_H: float (1.0 to 10.0) # catastrophic potential of defection
  adversarial_capacity_C: float (1.0 to 10.0) # potential for harm or manipulation
  demonstrated_integrity_I: float (1.0 to 10.0) # track record of truthfulness under adversity
  incentive_alignment_A: float (1.0 to 10.0) # correlation of counterpart flourishing with agent
  structural_accountability_S: float (1.0 to 10.0) # church elders, family oversight, formal checks
```
