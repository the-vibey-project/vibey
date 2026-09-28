---
id: skill-common-pci-dss-gaps-and-remediation-675dfd7df5
purpose: common pci dss gaps and remediation
source: src/vibey_tools/skills/plugins/compliance-frameworks/skills/pci-dss-v4/SKILL.md
requires: ["skill-compensating-controls-31e133e42d"]
links: ["skill-conversation-starters-for-pci-assessments-36f48359f8"]
---

## Common PCI DSS Gaps and Remediation

### Default Credentials Not Changed (Req 2.1)
**Problem:** Network devices, databases, or applications using vendor default passwords.
**Remediation:** Inventory all systems; change all defaults before deployment; use a configuration standard (CIS Benchmarks).

### PAN Stored Unnecessarily (Req 3.2)
**Problem:** Full PAN found in log files, error messages, databases beyond authorization.
**Remediation:** Data discovery scan (Spirion, Ground Labs); implement tokenization; add logging filters to mask PAN; delete unnecessary stored data.

### No Key Management Procedures (Req 3.7)
**Problem:** Encryption keys not formally managed; no rotation schedule; no split knowledge.
**Remediation:** Document key management procedures; implement key rotation (at least annually); use hardware security modules (HSMs) for key storage; enforce split knowledge and dual control.

### Missing Security Awareness Training (Req 12.6)
**Problem:** No annual security training for personnel with CDE access.
**Remediation:** Deploy KnowBe4, Proofpoint Security Awareness, or equivalent; track completion; test with phishing simulations.

### No Vendor Management Program (Req 12.8)
**Problem:** No list of service providers; no confirmation of their PCI compliance.
**Remediation:** Maintain vendor inventory; obtain AOC (Attestation of Compliance) from each service provider annually; include PCI obligations in contracts.

### Payment Page Scripts Not Inventoried (Req 6.4.3) — v4.0 NEW
**Problem:** Unknown third-party scripts load on payment pages (analytics, chat, A/B testing tools).
**Remediation:** Audit all scripts on payment pages; implement CSP headers; add SRI hashes to known scripts; remove unnecessary scripts.

---
