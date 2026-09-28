---
id: skill-evidence-collection-for-auditors-71296011ca
purpose: evidence collection for auditors
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/soc2-compliance/SKILL.md
requires: ["skill-control-mapping-soc-2-common-criteria-to-nist-800-53-e6057854b7"]
links: ["skill-common-soc-2-gaps-in-saas-cloud-environments-2bf47ffc73"]
---

## Evidence Collection for Auditors

SOC 2 auditors (for Type 2) will request evidence of control operation over the entire audit period. Evidence must be dated to show it occurred during the period under review.

### Access Control Evidence
- [ ] User access list with roles — point in time + evidence of periodic review
- [ ] Terminated employee access revocation records (show prompt deprovisioning)
- [ ] MFA enrollment confirmation for all users
- [ ] Privileged access request and approval tickets
- [ ] Access review documentation (reviewer sign-off, date, actions taken)
- [ ] New employee access provisioning records

### Change Management Evidence
- [ ] Git commit history and pull request approvals showing peer review
- [ ] Deployment records (who deployed what, when, from which environment)
- [ ] Change tickets with approvals and test results
- [ ] Separation of duties evidence: developers cannot merge their own PRs
- [ ] Production deployment approvals (separate from development team)

### Security Monitoring Evidence
- [ ] Vulnerability scan reports with dates (quarterly minimum)
- [ ] Penetration test report (annual)
- [ ] SIEM/log monitoring screenshots showing active alerting
- [ ] Alert investigation records
- [ ] Patch deployment records aligned to vulnerability reports

### Vendor Management Evidence
- [ ] Vendor inventory with tier classifications
- [ ] SOC 2 reports or security questionnaire responses from critical vendors
- [ ] Vendor contracts with security clauses
- [ ] Annual review documentation

### Incident Response Evidence
- [ ] Incident log (even if no major incidents — log minor events)
- [ ] Tabletop exercise record (scenario, attendees, findings, actions)
- [ ] IRP document with version history
- [ ] For any incidents during period: incident ticket, timeline, resolution, notifications

### Business Continuity / DR Evidence
- [ ] BCP/DRP document with RTO/RPO definitions
- [ ] DR test results (restore from backup, failover test)
- [ ] Backup job success logs
- [ ] Restoration test records (did the backup actually restore?)

---
