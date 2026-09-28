---
id: skill-okr-structure-for-engineering-acd02f29ea
purpose: okr structure for engineering
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-cycle-time-breakdown-62f0c013db"]
links: ["skill-engineering-efficiency-ratios-ab5b13fc72"]
---

## OKR Structure for Engineering

OKRs drive transformation and align engineering work to business outcomes. KPIs monitor ongoing operational health. Use both — OKRs for improvement initiatives, KPIs for steady-state monitoring.

### OKR Template for Engineering

**Objective:** [Inspiring, qualitative statement of direction]
- **KR1:** [Measurable outcome, not activity] — from X to Y by [date]
- **KR2:** [Measurable outcome] — from X to Y by [date]
- **KR3:** [Measurable outcome] — from X to Y by [date]

Sprint Goals should derive from current-quarter OKRs. If a Sprint Goal cannot be traced to an OKR, question why the work is being done.

### Example Engineering OKRs

**Objective 1:** Make our delivery pipeline a competitive advantage
- KR1: Deployment frequency from 2/week to multiple times per day
- KR2: Lead time for changes from 3 days to under 4 hours
- KR3: Change failure rate from 15% to under 5%

**Objective 2:** Build the most reliable internal developer platform in the organization
- KR1: Achieve 99.9% uptime for CI/CD infrastructure (up from 99.2%)
- KR2: Reduce mean time to resolve tool incidents from 4 hours to under 30 minutes
- KR3: Zero P1 incidents caused by tool configuration errors

**Objective 3:** Make engineers love their developer experience
- KR1: Developer satisfaction score from 3.1 to 4.2/5
- KR2: Onboarding time to first production deploy from 12 days to under 5 days
- KR3: Reduce time spent on unplanned work from 35% to under 15% of sprint capacity

### Initiative Mapping
For each KR, define 1–3 initiatives (the "how"):

```
KR: Lead time < 4 hours
  Initiative 1: Parallelize test execution (pytest-xdist + matrix strategy)
  Initiative 2: Eliminate manual deployment approval gate to staging
  Initiative 3: Move to trunk-based development; eliminate feature branch delay
```

---
