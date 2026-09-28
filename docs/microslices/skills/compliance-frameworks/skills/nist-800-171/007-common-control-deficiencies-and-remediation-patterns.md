---
id: skill-common-control-deficiencies-and-remediation-patterns-062bdb33e0
purpose: common control deficiencies and remediation patterns
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/nist-800-171/SKILL.md
requires: ["skill-poa-m-structure-33060b98cc"]
links: ["skill-relationship-to-cmmc-level-2-4241d6dc39"]
---

## Common Control Deficiencies and Remediation Patterns

### MFA Not Deployed (3.5.3) — High Impact
**Problem:** Password-only authentication for admin accounts.
**Remediation:** Deploy Microsoft Entra ID MFA, Duo Security, or Okta. Enforce Conditional Access policies requiring MFA for all privileged account access. Enforce for all network access to non-privileged accounts as well.
**Evidence:** MFA enrollment reports, Conditional Access policy screenshots, login audit logs.

### No Formal SSP (3.12.4) — High Impact
**Problem:** No documented System Security Plan.
**Remediation:** Use the NIST SP 800-171 SSP template. Document every control with implementation details, not just "yes/no." Include system boundary diagram.
**Evidence:** Completed SSP document with revision history.

### Vulnerability Scanning Not Occurring (3.11.2) — Medium Impact
**Problem:** No scheduled vulnerability scans.
**Remediation:** Deploy Tenable Nessus, Rapid7, or Qualys. Schedule authenticated scans weekly/monthly. Track findings in POA&M.
**Evidence:** Scan reports with timestamps, remediation tracking records.

### Audit Logging Gaps (3.3.1, 3.3.2) — High Impact
**Problem:** Logs not retained; user actions not traceable.
**Remediation:** Configure SIEM (Splunk, Microsoft Sentinel, Elastic). Ensure logs include user ID, timestamp, action, and outcome. Retain logs per policy (typically 1-3 years).
**Evidence:** SIEM configuration, log retention policy, sample log queries.

### Encryption at Rest Missing (3.13.16) — High Impact
**Problem:** CUI stored on unencrypted drives or in unencrypted databases.
**Remediation:** Enable BitLocker (Windows), FileVault (macOS), or cloud provider encryption (AWS KMS, Azure Disk Encryption). Encrypt database columns or tablespaces containing CUI.
**Evidence:** Encryption configuration screenshots, key management documentation.

### No Incident Response Plan (3.6.1) — High Impact
**Problem:** No documented IR procedures.
**Remediation:** Write an IRP covering: preparation, detection, containment, eradication, recovery, and lessons learned. Assign IR roles. Test annually with tabletop exercise.
**Evidence:** IRP document, tabletop exercise records, incident log.

### Least Privilege Not Enforced (3.1.5) — Medium Impact
**Problem:** Users have excessive permissions; no privileged account separation.
**Remediation:** Conduct access review. Remove unnecessary admin rights. Require separate admin accounts for privileged tasks. Implement PAM tools (CyberArk, BeyondTrust) for enterprise environments.
**Evidence:** Access review records, account inventory, PAM configuration.

---
