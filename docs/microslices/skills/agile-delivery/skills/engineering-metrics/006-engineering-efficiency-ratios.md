---
id: skill-engineering-efficiency-ratios-ab5b13fc72
purpose: engineering efficiency ratios
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-okr-structure-for-engineering-acd02f29ea"]
links: ["skill-dora-assessment-running-a-team-assessment-ccca5b2a40"]
---

## Engineering Efficiency Ratios

Track the ratio of **value-creating work** to **toil** as a sprint-level metric.

### Feature Work vs. Toil

```
Feature Work % = (Sprint capacity on new features) / (Total sprint capacity) × 100
Toil %         = (Sprint capacity on unplanned work, incidents, support) / (Total) × 100
```

**Targets:**
- Feature work: > 70% of sprint capacity
- Planned improvements: 10–20% (tech debt, security, tooling)
- Toil (unplanned): < 15% of sprint capacity

If toil consistently exceeds 20%, the system has a stability or process problem that must be addressed before velocity can improve. Toil above 30% indicates a systemic issue.

### Tracking Toil
Tag all work items as Feature, Improvement, Toil, or Security in your project management tool. Report the ratio at each Sprint Review. Trend lines over quarters reveal whether system investment is paying off.

---
