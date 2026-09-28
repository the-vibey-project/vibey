---
id: skill-sprint-planning-checklist-with-security-gates-74aca8b11f
purpose: sprint planning checklist with security gates
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-architecture-decision-records-adrs-20540c61df"]
links: ["skill-ai-coding-governance-in-agile-672fa992dc"]
---

## Sprint Planning Checklist with Security Gates

### Before Sprint Planning
- [ ] Security backlog groomed; Critical/High vulnerabilities assigned severity SLA
- [ ] Previous sprint security scan results reviewed; open findings triaged
- [ ] OWASP SAMM targets for this quarter reviewed
- [ ] Champion available for the sprint (not on PTO)

### During Sprint Planning
- [ ] Sprint Goal drafted before selecting backlog items
- [ ] Capacity calculated realistically (subtract ceremony time, PTO, support rotation, interrupt buffer)
- [ ] Each story with new data flows or integrations: STRIDE quick-scan assigned (5–10 min during planning or refinement)
- [ ] Security stories included (dependency updates, SAST triage, debt reduction)
- [ ] Misuse stories written for security-sensitive features
- [ ] AI-assisted work tagged; augmented DoD requirements confirmed
- [ ] Security DoD checklist reviewed with team

### Security Work Allocation Target
- 50–60% feature development
- 10–20% infrastructure
- 10–20% data engineering / analytics
- **10–20% security hardening and debt reduction**

---
