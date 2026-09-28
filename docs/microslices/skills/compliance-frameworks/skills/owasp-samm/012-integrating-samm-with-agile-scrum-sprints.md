---
id: skill-integrating-samm-with-agile-scrum-sprints-078af6bdff
purpose: integrating samm with agile scrum sprints
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/owasp-samm/SKILL.md
requires: ["skill-security-champions-program-g3-level-2-4bfd7b902f"]
links: ["skill-relationship-to-other-frameworks-08fccdc22b"]
---

## Integrating SAMM with Agile/Scrum Sprints

Security practices can be embedded into existing Agile ceremonies without creating separate security overhead.

### Sprint Planning
- Security requirements appear as acceptance criteria on user stories
- "Threat model reviewed" as a Definition of Ready criterion for security-sensitive stories
- Security champion reviews backlog for high-risk items

### Sprint Execution
- SAST, SCA, secrets scanning run on every commit (automated, fast feedback)
- Developers fix security findings in the same sprint they introduce them
- Security champion available for pairing on security-sensitive code

### Sprint Review / Demo
- Security-sensitive features demonstrate how security controls work (show the auth, show the audit log)
- Security defects shown alongside functional bugs in velocity metrics

### Sprint Retrospective
- "Did any security issues come up this sprint? How did we handle them?"
- Security improvement tasks added to team backlog

### Definition of Done (Security Additions)
- [ ] SAST scan passed (no new high/critical findings unreviewed)
- [ ] Dependencies checked (no new high/critical CVEs unreviewed)
- [ ] Security requirements from story met
- [ ] Sensitive data handling reviewed
- [ ] Security champion notified for security-sensitive changes

---
