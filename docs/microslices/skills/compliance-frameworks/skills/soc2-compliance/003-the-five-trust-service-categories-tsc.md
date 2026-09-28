---
id: skill-the-five-trust-service-categories-tsc-8e68da9dbf
purpose: the five trust service categories tsc
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/soc2-compliance/SKILL.md
requires: ["skill-framework-overview-779e8826ea"]
links: ["skill-minimum-policy-set-for-soc-2-type-2-267c32bf38"]
---

## The Five Trust Service Categories (TSC)

### Security (CC — Common Criteria) — ALWAYS REQUIRED
The foundational category. Every SOC 2 report must include Security. The Common Criteria (CC) covers logical and physical access controls, change management, risk management, and monitoring.

Security is organized into CC1–CC9 subcriteria:

**CC1: Control Environment**
- Commitment to integrity and ethical values (tone at the top)
- Board/management oversight of security program
- Organizational structure and reporting lines

**CC2: Communication and Information**
- Internal communication of security responsibilities
- External communication to relevant parties about security obligations

**CC3: Risk Assessment**
- Identify and analyze risks to achieving security objectives
- Fraud risk assessment
- Changes to systems/processes that create new risks

**CC4: Monitoring Activities**
- Ongoing and separate evaluations of controls
- Deficiency identification and remediation

**CC5: Control Activities (Policies)**
- Selection and development of controls
- Technology controls (general IT controls)
- Policy deployment and enforcement


**CC6: Logical and Physical Access Controls**
- User access provisioning, de-provisioning, and reviews
- Principle of least privilege
- Multi-factor authentication
- Physical facility access controls
- Encryption of data at rest and in transit
- Network security and segmentation

**CC7: System Operations**
- Detection and monitoring of new vulnerabilities
- System monitoring and anomaly detection
- Incident identification and response
- Change management and infrastructure reliability

**CC8: Change Management**
- Controlled change process (development → testing → production)
- Software development lifecycle controls
- Infrastructure change controls
- Emergency change procedures

**CC9: Risk Mitigation**
- Risk treatment and mitigation strategies
- Vendor/third-party risk management (subservice organizations)
- Business disruption risk

### Availability (A) — Optional
The system is available for operation and use as committed or agreed.

Covers: uptime SLA commitments, redundancy and failover, backup and recovery, capacity management, incident response for availability events, DR testing.

**Include if:** You have SLA commitments to customers; customers depend on uptime for their operations; you are a SaaS platform where downtime = customer revenue loss.

### Processing Integrity (PI) — Optional
System processing is complete, accurate, timely, and authorized.

Covers: Input validation, processing controls, error handling, output accuracy, transactional completeness, anomaly detection in processing.

**Include if:** You process financial transactions, payroll, healthcare data processing, or any workflow where processing errors have material consequences.

### Confidentiality (C) — Optional
Information designated as confidential is protected as committed or agreed.

Covers: Data classification, confidentiality agreements (NDAs), encryption of confidential data, access restrictions to confidential information, secure disposal.

**Include if:** You handle customer-designated confidential data, IP, trade secrets, or regulated data categories where confidentiality is a contractual or regulatory obligation.

### Privacy (P) — Optional
Personal information is collected, used, retained, disclosed, and disposed of in conformity with the entity's privacy notice and GAPP.

Covers: Notice and consent, data collection limitation, use/retention/disposal, access to personal data, disclosure to third parties, security of personal data.

**Include if:** You collect or process personal information and have made privacy commitments (GDPR alignment, CCPA compliance, etc.).


---
