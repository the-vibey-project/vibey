---
id: skill-presenting-metrics-to-leadership-90e72d6051
purpose: presenting metrics to leadership
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-dora-assessment-running-a-team-assessment-ccca5b2a40"]
links: ["skill-common-metrics-anti-patterns-181b0db09f"]
---

## Presenting Metrics to Leadership

### Executive Dashboard Principles

1. **Show trends, not snapshots** — a single data point is noise; 6–12 months of trend lines tell a story
2. **Benchmark against DORA tiers** — "we're Medium, targeting High by Q3" is more meaningful than raw numbers
3. **Connect to business outcomes** — deployment frequency → faster time to market; CFR → customer trust; FDRT → revenue protection
4. **Use three colors consistently** — Red (below Medium), Yellow (Medium/High), Green (Elite)
5. **Never show individual-level activity metrics** to leadership — this destroys psychological safety and causes gaming

### Executive Dashboard Template

```
Engineering Performance Dashboard — [Quarter]

THROUGHPUT
  Deployment Frequency:  2.3/day    ↑  [Elite ✓]
  Lead Time for Changes: 6.2 hours  ↑  [Elite ✓]

STABILITY
  Change Failure Rate:   8.2%       ↑  [High — target <5%]
  Recovery Time (FDRT):  47 mins    →  [Elite ✓]

DEVELOPER EXPERIENCE
  Satisfaction Score:    3.8/5      ↑  [Yellow — target 4.2]
  Cycle Time (avg):      3.1 days   ↑  [Improving]

THIS QUARTER'S FOCUS
  OKR: Reduce Change Failure Rate from 8.2% to < 5%
  Initiative: Expand integration test coverage to 80% of API endpoints
  Status: On track (currently at 67%, up from 52%)
```

### Handling the "Are People Working Hard Enough?" Question

When leadership asks about individual productivity, redirect to system performance:
- "We measure team output, not individual activity. Individual activity metrics cause gaming and harm collaboration."
- "The SPACE framework (Google/Microsoft Research, 2021) establishes that productivity is a multidimensional system property — it cannot be reduced to individual commits or story points."
- "What I can show you is how fast our system delivers value: deployment frequency, lead time, and change failure rate."

---
