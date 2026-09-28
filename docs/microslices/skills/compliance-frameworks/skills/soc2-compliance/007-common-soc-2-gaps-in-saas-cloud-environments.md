---
id: skill-common-soc-2-gaps-in-saas-cloud-environments-2bf47ffc73
purpose: common soc 2 gaps in saas cloud environments
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/soc2-compliance/SKILL.md
requires: ["skill-evidence-collection-for-auditors-71296011ca"]
links: ["skill-readiness-assessment-checklist-360365b260"]
---

## Common SOC 2 Gaps in SaaS/Cloud Environments

### No Formal Access Review Process (CC6.2, CC6.3)
**Gap:** User access is provisioned but never reviewed; departed employees may retain access.
**Fix:** Implement quarterly access reviews in Jira, Vanta, Drata, or a spreadsheet. Document who reviewed, when, what changes were made. Automate deprovisioning via HRIS-SSO integration.

### Developers Can Deploy to Production (CC8)
**Gap:** Engineers have direct production deployment access; no separation of duties.
**Fix:** Require pull request approval from a second engineer. Restrict production deployments to CI/CD pipeline with approvals. Even for small teams, document the control: "Engineer A writes code; Engineer B reviews and approves before merge; CI/CD deploys."

### No Documented Incident Response Testing (CC7.3–CC7.5)
**Gap:** IRP exists on paper but has never been tested.
**Fix:** Conduct a tabletop exercise (even 1 hour with 3 people). Document scenario, participants, walk-through, and action items. Auditors want evidence of testing, not just the plan.

### Monitoring Without Investigation Records (CC7.2)
**Gap:** SIEM generates alerts but no records of alert investigation.
**Fix:** Create a simple alert log: date, alert type, who investigated, finding, action taken. Even "investigated, false positive, no action required" counts.

### Vendor SOC Reports Not Collected (CC9.2)
**Gap:** Critical cloud providers (AWS, Stripe, Salesforce) not included in vendor management program.
**Fix:** Download SOC 2 reports for critical subservice organizations annually (most are available via their trust portals). Document where you reviewed them and what you found.

### Backup Restoration Not Tested (A1, if Availability in scope)
**Gap:** Backups run but restoration is never verified.
**Fix:** Perform a documented restoration test at least annually. Restore to a non-production environment and confirm data integrity. Record date, what was restored, results.

---
