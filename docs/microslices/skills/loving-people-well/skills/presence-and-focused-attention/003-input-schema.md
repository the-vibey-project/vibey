---
id: skill-input-schema-7ee99519a1
purpose: input schema
source: src/vibey_tools/skills/plugins/loving-people-well/skills/presence-and-focused-attention/SKILL.md
requires: ["skill-invocation-triggers-b60cb45b16"]
links: ["skill-governing-principles-f351e977d5"]
---

## Input Schema
```yaml
presence_protocol_parameters:
  environment_type: string (dining_table | living_room | car | walking)
  device_isolation_method: string (out_of_room | face_down_on_shelf | airplane_mode)
  conversational_counterpart: string
  listening_focus_areas: list[string]
  silence_tolerance_seconds: integer
```
