---
id: skill-input-schema-ed5c57a36a
purpose: input schema
source: src/vibey_tools/skills/plugins/loving-people-well/skills/memory-and-tracking/SKILL.md
requires: ["skill-invocation-triggers-e74fa1fbd9"]
links: ["skill-governing-principles-b883af49bb"]
---

## Input Schema
```yaml
memory_tracking_entry:
  person_name: string
  interaction_date: string
  confided_vulnerability: string
  actionable_milestone_date: string
  capture_method: string (voice_memo | digital_note | journal)
  retrieval_reminder_scheduled: boolean
  follow_up_inquiry_text: string
```
