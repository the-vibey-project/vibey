---
id: skill-security-champions-model-6f05dcaa73
purpose: security champions model
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-threat-modeling-in-sprint-planning-4832aabe55"]
links: ["skill-security-sprint-cadence-7190370048"]
---

## Security Champions Model

**One Security Champion per team** (one per 10–20 developers). Select based on curiosity and peer influence — not seniority.

### Champion Responsibilities
- **In refinement** — flag stories with security implications; propose misuse stories; initiate STRIDE quick-scans
- **In code review** — review security-tagged PRs; verify DoD security criteria
- **In Sprint Review** — present security scan dashboard; trend open vulnerabilities vs. resolved
- **Ongoing** — maintain team's security knowledge; escalate to central AppSec when needed

### Security Guild
Champions from all teams form a **Security Guild** meeting bi-weekly:
- Share findings across teams (vulnerability patterns, new attack techniques)
- Maintain shared Semgrep rulesets, Gitleaks config, and scan baselines
- Coordinate on cross-cutting security architecture decisions
- Manage the Champions rotation schedule

### Rotation Schedule
Rotate champions every 6–12 months. Overlap periods of 4 weeks for knowledge transfer. Track champion assignments on a dedicated **Champions board** in the project management tool. Never leave a team without a champion — overlap before rotating.

### Champion Training Path
1. OWASP Top 10 (foundational)
2. Threat modeling facilitation (STRIDE workshop)
3. SAST tool operation and triage
4. Penetration testing basics and scope definition
5. Incident response and blameless postmortem facilitation

---
