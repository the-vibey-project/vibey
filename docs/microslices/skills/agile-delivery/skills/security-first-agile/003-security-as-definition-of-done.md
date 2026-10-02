---
id: skill-security-as-definition-of-done-7e172ba8c3
purpose: security as definition of done
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-scrum-fundamentals-f233a9bb68"]
links: ["skill-threat-modeling-in-sprint-planning-4832aabe55"]
---

## Security as Definition of Done

The DoD applies universally to every Increment. Security gates are mandatory — an item that does not pass is returned to the backlog, not presented at Sprint Review.

```
## Security Definition of Done Checklist
- [ ] SAST scan (Semgrep + CodeQL) — 0 Critical/High findings
- [ ] SCA scan (Snyk/Dependabot) — 0 Critical CVEs in dependencies
- [ ] Secrets scan (Gitleaks) — 0 leaked secrets in commits or diffs
- [ ] IaC scan (Checkov) — 0 High misconfigs (when infra changed)
- [ ] All DB queries use parameterized patterns (no string concatenation)
- [ ] All API endpoints carry [Authorize] with appropriate policy
- [ ] CORS policy explicitly whitelists allowed origins only
- [ ] Content Security Policy headers configured (no unsafe-inline)
- [ ] Security logging verified (structured logs; no PII in logs)
- [ ] Threat model updated if new data flows or trust boundaries introduced
- [ ] AI-assisted code: PR labeled ai-assisted; reviewer confirms understanding (not just diff)
```

**Pipeline enforcement:** SAST and secrets scanning run as PR gates — the PR cannot merge on failure. SCA runs nightly and on PRs. IaC scanning triggers on infrastructure file changes only. Every gate should produce zero manual willpower.

---
