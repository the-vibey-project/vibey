---
id: skill-readiness-assessment-checklist-360365b260
purpose: readiness assessment checklist
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/soc2-compliance/SKILL.md
requires: ["skill-common-soc-2-gaps-in-saas-cloud-environments-2bf47ffc73"]
links: []
---

## Readiness Assessment Checklist

Before engaging a SOC 2 auditor, verify:

**Governance**
- [ ] Information Security Policy approved and distributed
- [ ] All minimum policies exist (12 policies above)
- [ ] Risk assessment completed in last 12 months
- [ ] Security awareness training completed by all personnel

**Access Controls**
- [ ] MFA enabled for all systems in scope
- [ ] Privileged access documented and reviewed
- [ ] Terminated employees removed from all systems (documented process)
- [ ] Access provisioning follows documented approval process

**Change Management**
- [ ] Code review/PR approval process enforced in version control
- [ ] CI/CD pipeline has approval gates before production
- [ ] Change log maintained for infrastructure changes

**Monitoring**
- [ ] Security alerts configured and investigated
- [ ] Vulnerability scans running and documented
- [ ] Log retention meets audit period (12 months)

**Availability (if in scope)**
- [ ] Backup policy defined and implemented
- [ ] Restoration test completed and documented
- [ ] DR/BCP plan tested in last 12 months

**Vendors**
- [ ] Critical vendor list maintained
- [ ] SOC 2 reports collected for critical SaaS/cloud vendors
