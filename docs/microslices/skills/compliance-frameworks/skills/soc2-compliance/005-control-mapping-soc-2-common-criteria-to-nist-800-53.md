---
id: skill-control-mapping-soc-2-common-criteria-to-nist-800-53-e6057854b7
purpose: control mapping soc 2 common criteria to nist 800 53
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/soc2-compliance/SKILL.md
requires: ["skill-minimum-policy-set-for-soc-2-type-2-267c32bf38"]
links: ["skill-evidence-collection-for-auditors-71296011ca"]
---

## Control Mapping: SOC 2 Common Criteria to NIST 800-53

SOC 2 auditors increasingly expect organizations to be able to map their controls to established frameworks. The mapping from TSC to NIST 800-53 is published by the AICPA.

| SOC 2 Criteria | NIST 800-53 Control Families |
|----------------|------------------------------|
| CC1 (Control Environment) | PM (Program Management), AT (Awareness & Training) |
| CC2 (Communication) | PL (Planning), PM |
| CC3 (Risk Assessment) | RA (Risk Assessment), PM |
| CC4 (Monitoring) | CA (Assessment), AU (Audit) |
| CC5 (Control Activities) | PL, SA (System Acquisition), PM |
| CC6.1 (Logical Access — Identification) | IA (Identification & Authentication) |
| CC6.2 (Logical Access — Provisioning) | AC (Access Control) |
| CC6.3 (Role-Based Access) | AC |
| CC6.6 (External Threats — Boundary) | SC (System & Comms Protection), SI |
| CC6.7 (Encryption) | SC, MP (Media Protection) |
| CC6.8 (Malware Protection) | SI |
| CC7.1 (Vulnerability Management) | RA, SI, CA |
| CC7.2 (Monitoring) | AU, SI, IR |
| CC7.3–CC7.5 (Incident Response) | IR (Incident Response) |
| CC8 (Change Management) | CM (Configuration Management), SA |
| CC9 (Risk Mitigation / Vendors) | SA-9, PM |
| A1 (Availability) | CP (Contingency Planning), SC |
| PI1 (Processing Integrity) | SI, AU |
| C1 (Confidentiality) | AC, SC, MP |
| P1–P8 (Privacy) | PT (PII Processing) |


---
