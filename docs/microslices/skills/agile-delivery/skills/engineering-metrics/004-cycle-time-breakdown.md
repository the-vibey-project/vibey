---
id: skill-cycle-time-breakdown-62f0c013db
purpose: cycle time breakdown
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-space-framework-a9c5d7b5a3"]
links: ["skill-okr-structure-for-engineering-acd02f29ea"]
---

## Cycle Time Breakdown

Cycle time (active work start to completion) is the most actionable flow metric. Break it into phases to identify bottlenecks.

### Cycle Time Phases

```
[Story pulled into In Progress]
       ↓
  CODING TIME (developer working)
       ↓
  PR OPEN (code complete, PR created)
       ↓
  REVIEW WAIT (waiting for first reviewer to engage)
       ↓
  REVIEW TIME (active review, back-and-forth)
       ↓
  MERGE WAIT (approved, waiting to merge / merge queue)
       ↓
  CI PIPELINE (build, test, scan — automated)
       ↓
  DEPLOY WAIT (waiting for deployment window or approval)
       ↓
  PRODUCTION (deployed)
```

### Typical Bottleneck Locations

| Bottleneck | Symptom | Fix |
|---|---|---|
| Review wait too long | PRs sit open > 4 hours before first review | Set team review SLA; use PR review rotation |
| PR size too large | Review time > 1 day; high change failure rate | Cap PRs at 400 lines; break stories into smaller items |
| Merge queue backup | Many approved PRs waiting to merge | Enable merge queue; move to trunk-based development |
| CI pipeline slow | Pipeline > 30 minutes; developers context-switch while waiting | Parallelize tests; cache dependencies; run fast tests first |
| Deploy wait | Code merged but not deployed for days | Remove manual deployment gates; automate deployment |
| Coding time too variable | Some stories take 1 day, others 2 weeks | Stories not broken down to 1–3 day items |

### Lead Time vs. Cycle Time

- **Cycle time** = active work start → completion (measures team efficiency)
- **Lead time** = request/commit → completion (measures customer experience)

A team with fast cycle time but slow lead time has a **queue problem** — work waits too long before anyone starts it. Track both; use cycle time for team improvement and lead time for stakeholder communication.

---
