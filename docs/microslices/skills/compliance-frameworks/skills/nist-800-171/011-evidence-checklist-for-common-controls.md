---
id: skill-evidence-checklist-for-common-controls-4c327531e1
purpose: evidence checklist for common controls
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/nist-800-171/SKILL.md
requires: ["skill-assessment-conversation-starters-c4bb40fb83"]
links: []
---

## Evidence Checklist for Common Controls

**For MFA (3.5.3):**
- [ ] MFA enrollment report (100% of privileged accounts)
- [ ] MFA enrollment report (100% of non-privileged accounts for network access)
- [ ] Conditional Access or equivalent policy screenshot
- [ ] Exception process if any accounts are excluded

**For Encryption in Transit (3.13.8):**
- [ ] Network diagram showing where TLS is enforced
- [ ] TLS configuration (minimum TLS 1.2, cipher suites)
- [ ] VPN configuration for remote access
- [ ] Certificate inventory

**For Audit Logging (3.3.1):**
- [ ] Log retention policy (minimum period defined)
- [ ] SIEM/log aggregation configuration
- [ ] Evidence logs include: user ID, timestamp, event, outcome
- [ ] Alert configuration for anomalous events

**For Vulnerability Management (3.11.2, 3.14.1):**
- [ ] Vulnerability scan schedule and tool configuration
- [ ] Most recent scan report
- [ ] Remediation SLAs (critical within X days)
- [ ] Patch management policy and records
