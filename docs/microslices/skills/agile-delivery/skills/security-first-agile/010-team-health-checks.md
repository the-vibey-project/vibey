---
id: skill-team-health-checks-3c85ebd381
purpose: team health checks
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-retrospective-formats-d1a539f2de"]
links: ["skill-architecture-decision-records-adrs-e3a998da3f"]
---

## Team Health Checks

### Spotify Squad Health Check (Kniberg & Lindwall, 2014)
Rate eleven dimensions on green/yellow/red with trend arrows:
Easy to Release, Suitable Process, Tech Quality, Value, Speed, Mission, Fun, Learning, Support, Pawns or Players, Teamwork.

**Run quarterly as a workshop with simultaneous card reveals** — the conversation is the value, not the score. Track trends across quarters; scan across teams to spot systemic patterns.

### Bus Factor Mitigation
Bus factor = minimum team members whose sudden absence would stall the project. Research of 25 popular GitHub projects found 10 had a bus factor of 1.

**Strategies:**
- **Pair programming** — NC State research: ~15% development-time cost; 86–94% test pass rate vs. 73–78% solo
- **Mob programming** — whole team on one problem; best for complex architectural decisions
- **Code review limits** — SmartBear/Cisco: optimal review size 200–400 lines; defect detection drops sharply above 400 LOC
- **Architecture Decision Records** — capture reasoning, not just decisions

---
