---
id: skill-architecture-decision-records-adrs-e3a998da3f
purpose: architecture decision records adrs
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-team-health-checks-3c85ebd381"]
links: ["skill-sprint-planning-checklist-with-security-gates-8a5ff01814"]
---

## Architecture Decision Records (ADRs)

ADRs (Michael Nygard, 2011; Thoughtworks Radar "Adopt" 2018) capture the reasoning behind architectural decisions for future team members and for system evolution.

### ADR Template
```
# ADR-NNN: [Short title]

**Status:** Proposed | Accepted | Deprecated | Superseded by ADR-NNN

**Context:** [What is the situation forcing this decision? What constraints apply?]

**Decision:** [What was decided?]

**Consequences:** [What becomes easier or harder as a result?]
```

**Store in `docs/adr/` in the repository** — co-located with code, version-controlled, always current. Create ADRs during spikes and refinement. Reference them in Sprint Planning when related work appears. Present significant decisions in Sprint Review.

---
