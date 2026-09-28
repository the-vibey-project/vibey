---
id: skill-minimum-policy-set-for-soc-2-type-2-267c32bf38
purpose: minimum policy set for soc 2 type 2
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/soc2-compliance/SKILL.md
requires: ["skill-the-five-trust-service-categories-tsc-8e68da9dbf"]
links: ["skill-control-mapping-soc-2-common-criteria-to-nist-800-53-e6057854b7"]
---

## Minimum Policy Set for SOC 2 Type 2

The following policies are required to satisfy the Common Criteria and any additional TSC categories elected. These come from the SOC2-Type2 Minimum Policy Set documentation.

### 1. Information Security Policy
The overarching policy defining the organization's approach to information security.
- Roles and responsibilities for information security
- Acceptable use rules for systems and data
- Consequences for policy violations
- Annual review and update process
- Executive sign-off and communication to all personnel

### 2. Access Control Policy
Defines who has access to what information and the procedures for granting and revoking access.
- User provisioning and de-provisioning process
- Principle of least privilege requirements
- Access review frequency (quarterly for privileged; semi-annual for standard)
- Segregation of duties requirements
- Privileged access management rules
- Remote access controls

### 3. Data Encryption Policy
Outlines how and when data is encrypted, both at rest and in transit.
- Encryption standards (AES-256 at rest; TLS 1.2+ in transit)
- Key management and rotation schedule
- Encryption requirements for portable devices and storage media
- Certificate management procedures

### 4. Incident Response Policy
Details how to respond to a security incident.
- Incident classification and severity definitions
- Roles and responsibilities (IR team)
- Incident detection and reporting procedures
- Containment, eradication, and recovery steps
- Communication plan (internal; customer notification)
- Post-incident review and lessons learned
- Retention of incident records

### 5. Disaster Recovery and Business Continuity Plan (BCP/DRP)
Outlines how the organization recovers from a disaster or significant event.
- Business impact analysis (BIA) with RTO/RPO for critical systems
- Recovery procedures per system/service
- Backup strategy and verification
- DR testing schedule (annual minimum for Type 2)
- Communication and escalation tree

### 6. Change Management Policy
Controls how changes to the IT environment are requested, approved, tested, and deployed.
- Change request and approval workflow
- Separation of duties: developers cannot deploy to production unilaterally
- Testing requirements before promotion to production
- Emergency change procedures
- Rollback procedures
- Change log maintenance

### 7. Risk Assessment Policy
Outlines how risks are identified, evaluated, and mitigated.
- Risk assessment methodology and frequency (annual minimum)
- Risk scoring criteria (likelihood × impact)
- Risk acceptance criteria
- Risk treatment options (accept, mitigate, transfer, avoid)
- Risk register ownership and maintenance

### 8. Vendor Management Policy
Governs evaluation and monitoring of third-party vendors.
- Vendor risk tiering (critical, significant, standard)
- Security due diligence requirements by tier
- Contract requirements (security obligations, audit rights, breach notification)
- Annual review of critical vendors
- Subservice organization monitoring (for SOC 2 carve-out or inclusive reports)


### 9. Data Backup Policy
Outlines how and when data is backed up, and how it can be restored.
- Backup frequency per data classification/criticality
- Backup storage location (offsite/cloud)
- Encryption of backups
- Restoration testing frequency (quarterly recommended)
- Retention periods

### 10. Network Security Policy
Documents network protection controls.
- Firewall and network segmentation requirements
- Intrusion detection/prevention systems
- Wireless network controls
- Network monitoring and alerting
- Remote access VPN requirements

### 11. Data Retention and Disposal Policy
Governs how long data is kept and how it is securely disposed of.
- Retention periods by data category
- Legal hold procedures
- Secure disposal methods (shredding, NIST 800-88 media sanitization)
- Records of destruction

### 12. Privacy Policy (if Privacy TSC selected)
Covers collection, use, retention, disclosure, and disposal of personal information.
- Data subject rights (access, deletion, correction)
- Cookie and tracking disclosures
- Third-party sharing disclosures
- Data breach notification commitments

---
