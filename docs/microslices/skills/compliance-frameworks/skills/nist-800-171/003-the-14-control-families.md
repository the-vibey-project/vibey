---
id: skill-the-14-control-families-ad18b18d3c
purpose: the 14 control families
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/nist-800-171/SKILL.md
requires: ["skill-framework-overview-c4b60e976d"]
links: ["skill-sprs-score-system-2a42f8675e"]
---

## The 14 Control Families

### 1. Access Control (AC) — 3.1.x — 22 controls
Limit system access to authorized users, devices, and processes. Enforce least privilege, separate duties, control remote access sessions, and manage mobile/wireless/external connections.

**Critical controls:**
- 3.1.1 — Limit access to authorized users and devices
- 3.1.2 — Limit access to permitted transactions and functions
- 3.1.5 — Employ least privilege including privileged accounts
- 3.1.12 — Monitor and control remote access sessions
- 3.1.13 — Encrypt remote access sessions cryptographically
- 3.1.17 — Protect wireless access with authentication and encryption


### 2. Awareness and Training (AT) — 3.2.x — 3 controls
Ensure managers, admins, and users understand security risks. Provide role-based training. Train on insider threat indicators.

- 3.2.1 — Security awareness for all system users
- 3.2.2 — Role-based training for security responsibilities
- 3.2.3 — Insider threat recognition and reporting

### 3. Audit and Accountability (AU) — 3.3.x — 9 controls
Create, retain, and protect audit logs. Ensure user actions are traceable. Alert on logging failures. Correlate events across systems.

**Critical controls:**
- 3.3.1 — Create and retain audit logs
- 3.3.2 — Ensure actions are uniquely traceable to users
- 3.3.5 — Correlate audit records for investigation
- 3.3.8 — Protect audit information from unauthorized access/modification

### 4. Configuration Management (CM) — 3.4.x — 9 controls
Establish baselines, enforce secure configurations, track changes, apply least functionality. Control user-installed software.

- 3.4.1 — Establish and maintain baseline configurations
- 3.4.2 — Enforce security configuration settings
- 3.4.6 — Least functionality (only essential capabilities)
- 3.4.8 — Application allowlisting/denylisting

### 5. Identification and Authentication (IA) — 3.5.x — 11 controls
Identify and authenticate users, processes, and devices before granting access. Enforce MFA. Manage passwords and credentials securely.

**Critical controls:**
- 3.5.1 — Identify all system users and devices
- 3.5.2 — Authenticate identities before granting access
- 3.5.3 — MFA for privileged accounts (local and network) and all non-privileged network accounts
- 3.5.10 — Store and transmit only cryptographically protected passwords


### 6. Incident Response (IR) — 3.6.x — 3 controls
Establish operational incident handling: preparation, detection, containment, recovery. Track and report incidents. Test the capability.

- 3.6.1 — Establish incident handling capability
- 3.6.2 — Track, document, and report incidents
- 3.6.3 — Test incident response capability

### 7. Maintenance (MA) — 3.7.x — 6 controls
Control maintenance activities, tools, and personnel. Require MFA for remote maintenance sessions. Sanitize equipment before off-site maintenance.

- 3.7.3 — Sanitize CUI from equipment before off-site maintenance
- 3.7.5 — MFA for nonlocal (remote) maintenance sessions

### 8. Media Protection (MP) — 3.8.x — 9 controls
Protect, limit access to, mark, and sanitize system media containing CUI. Control transport of media. Encrypt CUI on portable storage.

- 3.8.1 — Physically protect and securely store CUI media
- 3.8.3 — Sanitize or destroy media before disposal/reuse
- 3.8.6 — Encrypt CUI on digital media during transport

### 9. Personnel Security (PS) — 3.9.x — 2 controls
Screen individuals before granting system access. Protect systems during and after terminations and transfers.

- 3.9.1 — Screen individuals prior to access authorization
- 3.9.2 — Protect systems during terminations and transfers (revoke access promptly)

### 10. Physical Protection (PE) — 3.10.x — 6 controls
Limit physical access to authorized individuals. Monitor facilities. Escort visitors. Maintain physical access audit logs. Enforce CUI safeguards at alternate work sites.

- 3.10.1 — Limit physical access to authorized individuals
- 3.10.2 — Monitor physical facility and infrastructure
- 3.10.6 — Enforce CUI safeguards at alternate work sites (remote workers)

### 11. Risk Assessment (RA) — 3.11.x — 3 controls
Periodically assess risk. Scan for vulnerabilities. Remediate in accordance with risk assessments.

- 3.11.1 — Periodic organizational risk assessment
- 3.11.2 — Vulnerability scanning (periodic and when new vulns identified)
- 3.11.3 — Remediate vulnerabilities per risk assessment prioritization


### 12. Security Assessment (CA) — 3.12.x — 4 controls
Periodically assess security controls. Develop and implement POA&Ms. Monitor controls on an ongoing basis. Maintain system security plans.

- 3.12.1 — Periodically assess security control effectiveness
- 3.12.2 — Develop and implement plans of action (POA&Ms)
- 3.12.3 — Ongoing monitoring of security control effectiveness
- 3.12.4 — Develop and maintain system security plan (SSP)

### 13. System and Communications Protection (SC) — 3.13.x — 16 controls
Monitor and protect communications at boundaries. Architect for security. Encrypt CUI in transit and at rest. Prevent split tunneling. Use FIPS-validated cryptography.

**Critical controls:**
- 3.13.1 — Boundary protection: monitor/control at external and key internal boundaries
- 3.13.5 — DMZ/subnetworks for publicly accessible components
- 3.13.6 — Deny-by-default network communications
- 3.13.8 — Encrypt CUI in transit (TLS, VPN)
- 3.13.11 — FIPS-validated cryptography for CUI confidentiality
- 3.13.16 — Protect CUI at rest

### 14. System and Information Integrity (SI) — 3.14.x — 7 controls
Identify and correct flaws. Protect against malicious code. Monitor for attacks and unauthorized use. Update malicious code protections.

- 3.14.1 — Identify, report, and correct system flaws timely
- 3.14.2 — Malicious code protection at designated locations
- 3.14.6 — Monitor inbound and outbound traffic for attacks
- 3.14.7 — Identify unauthorized use of systems

---
