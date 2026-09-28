---
id: skill-security-debt-management-80d4512cfa
purpose: security debt management
source: src/vibey_tools/skills/plugins/agile-delivery/skills/security-first-agile/SKILL.md
requires: ["skill-owasp-samm-integration-b368047388"]
links: []
---

## Security Debt Management

**60% of organizations carry critical security debt** (Veracode 2026 State of Software Security). Security debt is technical debt with higher blast radius.

### Visibility Mechanisms
- Unified dashboard: open vulnerabilities by age, security debt trend per sprint, MTTR by severity
- CISA Known Exploited Vulnerabilities list checked weekly
- Vulnerability age tracked as a sprint metric (average days open by severity tier)

### Prioritization SLAs
| Severity | SLA |
|---|---|
| CISA KEV or CVSS ≥9.0 (internet-facing) | Current sprint |
| CVSS 7.0–8.9 | Within 2 sprints |
| CVSS 4.0–6.9 | Within current quarter |
| CVSS <4.0 | Scheduled as capacity allows |

Dedicate **10–20% of sprint capacity** to security debt. Make this a standing capacity allocation visible in Sprint Planning — not something negotiated away under feature pressure.
