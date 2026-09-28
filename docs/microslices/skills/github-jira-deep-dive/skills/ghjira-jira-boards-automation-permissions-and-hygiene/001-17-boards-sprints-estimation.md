---
id: skill-17-boards-sprints-estimation-95a81ad3bc
purpose: 17 boards sprints estimation
source: src/vibey_tools/skills/plugins/github-jira-deep-dive/skills/ghjira-jira-boards-automation-permissions-and-hygiene/SKILL.md
requires: []
links: ["skill-18-reports-a698f7b73c"]
---

## §17. Boards, Sprints, Estimation

```
SCRUM BOARD   ⚠️ sprints, backlog, sprint commitment, burndown
KANBAN BOARD  ⚠️ continuous flow, WIP limits, cumulative flow diagram
⚠️ WIP LIMITS  the single highest-value Kanban feature and the most ignored.
   ⚠️ Limiting WIP reduces cycle time — Little's Law: WIP = throughput × cycle time
SWIMLANES · QUICK FILTERS · CARD COLOURS
```
**⚠️ Estimation, honestly:**
- ⚠️ **Story points are RELATIVE SIZE, not time**, **and they work by letting a team's
  historical throughput convert points to duration empirically.**
- **⚠️ Velocity is a planning aid for ONE team and is not comparable across teams** —
  ⚠️ **and using it as a performance metric reliably causes point inflation, which is
  Goodhart's law arriving on schedule** (§24 → `ghjira-integration-metrics-and-anti-patterns`).
- **⚠️ Counting ISSUES often forecasts about as well as summing points**, **provided
  issues are broken down to roughly similar size** — **which is a genuinely useful and
  under-known finding.**
- ⚠️ **Probabilistic forecasting from historical cycle time (Monte Carlo) beats
  commitment-based estimation for delivery dates**, **and it doesn't require estimates
  at all.**

---
