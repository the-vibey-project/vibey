---
id: skill-input-schema-01071265a6
purpose: input schema
source: src/vibey_tools/skills/plugins/christian-courtship/skills/concentric-boundaries-and-chastity/SKILL.md
requires: ["skill-invocation-triggers-2999bc1d8d"]
links: ["skill-the-five-concentric-spheres-1151c566de"]
---

## Input Schema
```yaml
boundary_configuration:
  current_sphere: integer (0 | 1 | 2 | 3 | 4)
  target_sphere: integer (0 | 1 | 2 | 3 | 4)
  physical_boundaries_declared: boolean
  third_party_accountability_active: boolean
  private_seclusion_status: string (public_only | group_settings | family_environment)
```
