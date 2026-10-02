---
id: skill-blameless-postmortems-92ac08863a
purpose: blameless postmortems
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-psychological-safety-project-aristotle-8a70bceba3"]
links: ["skill-retrospective-formats-d1a539f2de"]
---

## Blameless Postmortems

Adapted from Google SRE. A blameless postmortem assumes everyone involved had good intentions and made the best decision they could with the information they had at the time.

### Postmortem Template
1. **Incident summary** — one paragraph, factual
2. **Impact assessment** — affected users, revenue impact, duration
3. **Timeline** — chronological, using roles not names
4. **Root causes and triggers** — systemic factors, not individual failures
5. **What went well** — detection speed, response effectiveness, communication
6. **What went wrong** — gaps in monitoring, process failures, tooling gaps
7. **Where luck intervened** — reveals future risks that could materialize without the lucky condition
8. **Action items** — SMART, single owner, due date, linked to Sprint Backlog ticket
9. **Lessons learned** — generalizable insights for future incidents

**Store postmortems in a searchable team wiki.** Review action item status at the next Sprint Retrospective. Use past incidents for "Wheel of Misfortune" training with new team members. Focus on systems, not individuals — the goal is to prevent recurrence, not assign blame.

---
