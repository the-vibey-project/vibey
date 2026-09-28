---
id: skill-common-cmmc-cui-implementation-gaps-ea235e56b8
purpose: common cmmc cui implementation gaps
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/cmmc-cui/SKILL.md
requires: ["skill-assessment-types-in-detail-fa308c70e4"]
links: []
---

## Common CMMC/CUI Implementation Gaps

### No CUI Identification Process
**Problem:** Organization does not know what it has that qualifies as CUI.
**Fix:** Conduct CUI data discovery. Review contracts and deliverables. Work with customers to identify CUI categories. Document CUI types and locations in SSP.

### CUI Stored in Non-Compliant Systems
**Problem:** CUI in personal email, personal cloud drives (Dropbox, Google Drive consumer), or unencrypted local drives.
**Fix:** Migrate CUI to compliant systems. Deploy Microsoft 365 GCC or equivalent. Encrypt local drives. Remove CUI from personal services.

### No Flow-Down to Subcontractors
**Problem:** Prime has DFARS clauses but has not flowed them to subs that handle CUI.
**Fix:** Audit all subcontracts. Add DFARS 252.204-7012, 7019, 7020, 7021 clauses to subcontracts. Obtain SPRS scores from subs. Confirm subs understand their reporting obligations.

### SPRS Score Inflated
**Problem:** SPRS score does not reflect actual compliance; score was calculated optimistically.
**Fix:** Conduct a rigorous self-assessment using 800-171A assessment procedures. Score each control honestly. Submit a lower score with a strong POA&M showing active remediation — this is legally safer than a falsely high score.

### No Incident Response Plan for DoD Reporting
**Problem:** IRP does not include DFARS 252.204-7012 reporting procedures; team does not know the 72-hour rule.
**Fix:** Add a DoD incident reporting section to the IRP. Define the trigger criteria. Identify who submits the report to DIBNet. Practice the scenario in tabletop exercises.
