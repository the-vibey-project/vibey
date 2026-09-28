---
id: skill-space-framework-a9c5d7b5a3
purpose: space framework
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-dora-four-key-metrics-ec7ec99d23"]
links: ["skill-cycle-time-breakdown-62f0c013db"]
---

## SPACE Framework

The SPACE framework (Forsgren, Storey et al., 2021, *ACM Queue*) provides the holistic complement to DORA — measuring developer productivity across five dimensions to prevent gaming any single metric.

**Rule: Never use a single SPACE dimension alone. Combine at least three.**

### Five Dimensions

**S — Satisfaction and Well-being**
How developers feel about their work, tools, and team. Well-being directly predicts long-term productivity and retention.

What to measure:
- Developer satisfaction survey scores (quarterly pulse surveys)
- Employee Net Promoter Score (eNPS)
- Retention and voluntary turnover rate
- Reported burnout indicators (overtime hours, unplanned leave patterns)

Tools: Athenian, LinearB, Faros AI developer surveys; custom survey in Microsoft Forms or Culture Amp.

**P — Performance**
Whether the work is producing the intended outcomes. Distinct from activity — a developer can be highly active while producing no valuable outcomes.

What to measure:
- DORA metrics (the primary performance indicators)
- Reliability targets met (SLA/SLO adherence)
- Defect escape rate to production
- Customer-reported bugs per release

**A — Activity**
Counts of specific actions in the development process. Use cautiously — activity metrics alone mislead and are trivially gamed.

What to measure (with extreme caution):
- Commits per developer per week (directional only; never as a target)
- Pull requests opened and merged
- Code review participation rate (reviews given per developer)
- Build and test run frequency

**Never use activity metrics as individual performance targets.** The moment you set a commit count target, developers start making tiny commits. Use only as directional signals in aggregate.

**C — Communication and Collaboration**
How effectively developers work together and share information.

What to measure:
- PR review turnaround time (PR opened to first review; PR opened to merge)
- Onboarding effectiveness (time for new team members to ship their first production change)
- Documentation quality (tracked via usage, not just existence)
- Cross-team dependency resolution time
- Code review comment quality (directional — hard to measure mechanically)

**E — Efficiency and Flow**
How smoothly work moves through the system with minimal interruptions.

What to measure:
- Cycle time (active work start to completion)
- WIP (work in progress at any point in time)
- Context switches per developer per day (interrupt events)
- Time in meetings vs. deep work time (calendar analysis)
- Unplanned work percentage per sprint

### SPACE Dashboard Template

| Dimension | Metric | Current | Target | Trend |
|---|---|---|---|---|
| Satisfaction | Developer satisfaction score | 3.8/5 | 4.2/5 | ↑ |
| Satisfaction | Voluntary turnover (annualized) | 18% | <12% | → |
| Performance | Deployment frequency | 2/week | Daily | ↑ |
| Performance | Change failure rate | 12% | <5% | ↑ |
| Performance | Defect escape rate | 8% | <5% | → |
| Activity | PR review participation rate | 68% | >80% | ↑ |
| Communication | Avg PR review turnaround | 18 hrs | <8 hrs | ↑ |
| Communication | Onboarding time to first production deploy | 12 days | <5 days | → |
| Efficiency | Average cycle time | 6.2 days | <3 days | ↑ |
| Efficiency | WIP per developer | 3.1 | <2 | → |

---
