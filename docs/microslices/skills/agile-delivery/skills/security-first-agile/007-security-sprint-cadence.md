---
id: skill-security-sprint-cadence-d23f5cd8fe
purpose: security sprint cadence
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-security-champions-model-c81407b013"]
links: ["skill-psychological-safety-project-aristotle-047809b565"]
---

## Security Sprint Cadence

### Recurring Security Stories (add to backlog each sprint)
- Dependency updates — triage Dependabot/Snyk alerts; fix Critical CVEs this sprint
- SAST triage — review new CodeQL/Semgrep findings; close false positives; create stories for true positives
- Security debt burndown — dedicate 10–20% of sprint capacity to security debt
- Security metric review — update vulnerability age dashboard; MTTR trends

### Security Backlog Grooming
Hold a dedicated **Security Backlog Grooming** session monthly (separate from standard refinement):
- Review OWASP SAMM maturity scores against targets
- Review all open vulnerabilities from the unified dashboard
- Prioritize using CISA Known Exploited Vulnerabilities list first
- Severity-based SLAs: Critical/CISA KEV → current sprint; CVSS ≥9.0 internet-facing → current sprint; CVSS 7.0–8.9 → within 2 sprints; lower → scheduled as capacity allows

### Penetration Testing Cadence
| Tier | Frequency | Scope |
|---|---|---|
| Automated DAST (OWASP ZAP baseline) | Every PR/build | Changed endpoints |
| Security Champion review | Each sprint | Security-critical features |
| Internal manual pentest | Quarterly | Full application scope |
| External firm engagement | Annually | Full scope including social engineering |

With 2-week sprints, annual external testing leaves 25 of 26 releases untested. Layer all four tiers.

---
