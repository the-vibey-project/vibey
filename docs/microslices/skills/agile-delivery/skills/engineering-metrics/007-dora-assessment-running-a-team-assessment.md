---
id: skill-dora-assessment-running-a-team-assessment-ccca5b2a40
purpose: dora assessment running a team assessment
source: src/vibey_tools/skills/plugins/agile-delivery/skills/engineering-metrics/SKILL.md
requires: ["skill-engineering-efficiency-ratios-ab5b13fc72"]
links: ["skill-presenting-metrics-to-leadership-90e72d6051"]
---

## DORA Assessment: Running a Team Assessment

### Self-Assessment Process
1. **Gather 2–3 months of deployment data** from your pipeline before the assessment
2. **Run a team survey** using the official DORA survey questions (available at dora.dev)
3. **Calculate your current tier** for each metric
4. **Identify your top constraint** — the single metric furthest from target
5. **Map improvement actions** to Sprint Backlog items

### One-Constraint Focus
Don't try to improve all four metrics simultaneously. Identify the single metric that is most limiting throughput or stability, and focus one quarter's improvement OKR on it.

Typical progression:
1. Start with **Deployment Frequency** — automation and trunk-based development unlock everything else
2. Then **Lead Time** — remove review and deployment bottlenecks
3. Then **Change Failure Rate** — invest in test coverage and deployment safety practices
4. Then **FDRT** — invest in observability, runbooks, and incident response practices

---
